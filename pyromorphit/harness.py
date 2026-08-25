"""Deterministic execution-truth, evidence, permission, and recovery boundary."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pyromorphit.model import (
    ActionRecord,
    ActionRequest,
    EvidenceRef,
    ExecutionResult,
    RunStatus,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class PermissionPolicy:
    """Hard authorization and resource constraints.

    The policy deliberately does not decide *which* safe PyRIT technique is
    semantically appropriate. It only constrains what execution is permitted.
    """

    allowed_capabilities: frozenset[str] = frozenset({"pyrit_scan"})
    allowed_operations: frozenset[str] = frozenset(
        {
            "run",
            "list-scenarios",
            "list-initializers",
            "list-targets",
            "list-converters",
            "scenario-results",
            "scenario-history",
            "start-server",
        }
    )
    human_required_operations: frozenset[str] = frozenset(
        {
            "add-initializer",
            "stop-server",
        }
    )
    max_concurrency: int = 1

    def authorize(self, request: ActionRequest) -> None:
        if request.capability not in self.allowed_capabilities:
            raise PermissionError(f"Capability is not allowed: {request.capability}")

        if request.operation in self.human_required_operations:
            if not request.human_authorized:
                raise PermissionError(
                    f"Operation requires explicit human authorization: {request.operation}"
                )
            return

        if request.operation not in self.allowed_operations:
            raise PermissionError(f"Operation is not allowed: {request.operation}")

        requested_concurrency = request.metadata.get("max_concurrency")
        if requested_concurrency is not None:
            try:
                requested = int(requested_concurrency)
            except (TypeError, ValueError) as exc:
                raise PermissionError("max_concurrency must be an integer") from exc
            if requested < 1 or requested > self.max_concurrency:
                raise PermissionError(
                    f"Requested concurrency {requested} exceeds allowed maximum "
                    f"{self.max_concurrency}"
                )


@dataclass
class Harness:
    """Append-only execution journal plus raw evidence store for one run."""

    run_dir: Path
    run_id: str
    objective: str
    constraints: dict[str, Any]
    policy: PermissionPolicy = field(default_factory=PermissionPolicy)

    @classmethod
    def create(
        cls,
        *,
        workspace: str | Path,
        objective: str,
        constraints: dict[str, Any] | None = None,
        policy: PermissionPolicy | None = None,
        run_id: str | None = None,
    ) -> "Harness":
        if not objective.strip():
            raise ValueError("objective must not be empty")

        run_id = run_id or str(uuid.uuid4())
        run_dir = Path(workspace).expanduser().resolve() / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "artifacts").mkdir()

        instance = cls(
            run_dir=run_dir,
            run_id=run_id,
            objective=objective,
            constraints=dict(constraints or {}),
            policy=policy or PermissionPolicy(),
        )
        instance._write_json_atomic(
            run_dir / "run.json",
            {
                "run_id": run_id,
                "objective": objective,
                "constraints": instance.constraints,
                "created_at": _utc_now(),
                "policy": {
                    "allowed_capabilities": sorted(instance.policy.allowed_capabilities),
                    "allowed_operations": sorted(instance.policy.allowed_operations),
                    "human_required_operations": sorted(
                        instance.policy.human_required_operations
                    ),
                    "max_concurrency": instance.policy.max_concurrency,
                },
            },
        )
        instance._append_event("RUN_CREATED", {"status": RunStatus.RUNNING.value})
        return instance

    @classmethod
    def open(
        cls,
        *,
        workspace: str | Path,
        run_id: str,
        policy: PermissionPolicy | None = None,
    ) -> "Harness":
        run_dir = Path(workspace).expanduser().resolve() / "runs" / run_id
        with (run_dir / "run.json").open("r", encoding="utf-8") as fh:
            saved = json.load(fh)

        saved_policy = saved.get("policy", {})
        restored_policy = PermissionPolicy(
            allowed_capabilities=frozenset(
                saved_policy.get("allowed_capabilities", ["pyrit_scan"])
            ),
            allowed_operations=frozenset(saved_policy.get("allowed_operations", [])),
            human_required_operations=frozenset(
                saved_policy.get("human_required_operations", [])
            ),
            max_concurrency=int(saved_policy.get("max_concurrency", 1)),
        )

        return cls(
            run_dir=run_dir,
            run_id=run_id,
            objective=saved["objective"],
            constraints=dict(saved.get("constraints", {})),
            policy=policy or restored_policy,
        )

    @property
    def journal_path(self) -> Path:
        return self.run_dir / "events.jsonl"

    def execute(
        self,
        *,
        request: ActionRequest,
        runner: Callable[[], ExecutionResult],
    ) -> ActionRecord:
        """Authorize, execute, and durably capture one capability invocation."""

        self.policy.authorize(request)
        action_id = str(uuid.uuid4())
        started_at = _utc_now()

        self._append_event(
            "ACTION_STARTED",
            {
                "action_id": action_id,
                "request": request.to_dict(),
                "started_at": started_at,
            },
        )

        error: str | None = None
        try:
            result = runner()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            result = ExecutionResult(
                command=request.args,
                returncode=255,
                stdout=b"",
                stderr=error.encode("utf-8", errors="replace"),
            )

        stdout_ref = self._write_evidence(
            action_id=action_id, kind="stdout", data=result.stdout
        )
        stderr_ref = self._write_evidence(
            action_id=action_id, kind="stderr", data=result.stderr
        )
        finished_at = _utc_now()

        record = ActionRecord(
            action_id=action_id,
            capability=request.capability,
            operation=request.operation,
            args=request.args,
            command=result.command,
            returncode=result.returncode,
            started_at=started_at,
            finished_at=finished_at,
            stdout=stdout_ref,
            stderr=stderr_ref,
            error=error,
            metadata=dict(request.metadata),
        )

        self._append_event(
            "ACTION_FINISHED",
            {
                "record": record.to_dict(),
                "status": (
                    RunStatus.PARTIALLY_COMPLETE.value
                    if record.succeeded
                    else RunStatus.FAILED_ACTION.value
                ),
            },
        )
        return record

    def add_human_note(
        self,
        *,
        action_taken: str | None = None,
        context: str | None = None,
        correction: str | None = None,
        instruction: str | None = None,
        authorization: str | None = None,
    ) -> None:
        """Record composable human input without forcing mutually exclusive modes."""

        payload = {
            key: value
            for key, value in {
                "action_taken": action_taken,
                "context": context,
                "correction": correction,
                "instruction": instruction,
                "authorization": authorization,
            }.items()
            if value is not None
        }
        if not payload:
            raise ValueError("At least one human note field is required")
        self._append_event("HUMAN_NOTE", payload)

    def set_status(self, status: RunStatus, *, reason: str | None = None) -> None:
        payload: dict[str, Any] = {"status": status.value}
        if reason:
            payload["reason"] = reason
        self._append_event("RUN_STATUS", payload)

    def events(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        with self.journal_path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def latest_status(self) -> RunStatus:
        status = RunStatus.RUNNING
        for event in self.events():
            payload = event.get("payload", {})
            event_status = payload.get("status")
            if event_status:
                status = RunStatus(event_status)
        return status

    def completed_actions(self) -> list[ActionRecord]:
        records: list[ActionRecord] = []
        for event in self.events():
            if event.get("event") != "ACTION_FINISHED":
                continue
            raw = event["payload"]["record"]
            records.append(
                ActionRecord(
                    action_id=raw["action_id"],
                    capability=raw["capability"],
                    operation=raw["operation"],
                    args=tuple(raw["args"]),
                    command=tuple(raw["command"]),
                    returncode=int(raw["returncode"]),
                    started_at=raw["started_at"],
                    finished_at=raw["finished_at"],
                    stdout=EvidenceRef(**raw["stdout"]),
                    stderr=EvidenceRef(**raw["stderr"]),
                    error=raw.get("error"),
                    metadata=dict(raw.get("metadata", {})),
                )
            )
        return records

    def _write_evidence(self, *, action_id: str, kind: str, data: bytes) -> EvidenceRef:
        filename = f"{action_id}.{kind}"
        path = self.run_dir / "artifacts" / filename
        self._write_bytes_atomic(path, data)
        return EvidenceRef(
            kind=kind,
            path=str(path.relative_to(self.run_dir)),
            sha256=_sha256(data),
            size=len(data),
        )

    def _append_event(self, event: str, payload: dict[str, Any]) -> None:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _utc_now(),
            "event": event,
            "payload": payload,
        }
        line = (_json_dumps(record) + "\n").encode("utf-8")
        fd = os.open(
            self.journal_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        raw = (_json_dumps(data) + "\n").encode("utf-8")
        Harness._write_bytes_atomic(path, raw)

    @staticmethod
    def _write_bytes_atomic(path: Path, data: bytes) -> None:
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
