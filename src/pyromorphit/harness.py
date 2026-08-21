"""Execution truth, evidence persistence, and recovery constraints."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .models import CapabilityResult, EvidenceRef, RunState, RunStatus, StepRecord, to_jsonable, utc_now
from .protocols import Capability


class ExecutionHarness:
    """Persist authoritative run state while keeping semantic choices outside the harness."""

    def __init__(self, *, root: str | Path = ".pyromorphit/runs") -> None:
        self.root = Path(root)

    def start_run(self, *, goal: str) -> RunState:
        run_id = str(uuid.uuid4())
        state = RunState(run_id=run_id, goal=goal)
        self._run_dir(run_id).mkdir(parents=True, exist_ok=False)
        self._evidence_dir(run_id).mkdir(parents=True, exist_ok=True)
        self.save_state(state)
        self._append_event(run_id, {"event": "run_started", "goal": goal})
        return state

    def load_state(self, run_id: str) -> RunState:
        path = self._state_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown Pyromorphit run: {run_id}")
        return RunState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_state(self, state: RunState) -> None:
        state.updated_at = utc_now()
        target = self._state_path(state.run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def add_human_input(self, *, state: RunState, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("human input must not be empty")
        state.human_inputs.append(cleaned)
        state.pending_question = None
        state.status = RunStatus.RUNNING
        self._append_event(state.run_id, {"event": "human_input", "text": cleaned})
        self.save_state(state)

    async def execute_capability(
        self,
        *,
        state: RunState,
        capability: Capability,
        instruction: str,
        decision_summary: str = "",
    ) -> CapabilityResult:
        """Execute locally, persist raw evidence first, then append a compact step record."""
        index = len(state.steps) + 1
        try:
            result = await capability.execute(instruction=instruction)
        except Exception as exc:  # local failure must not erase earlier work; cancellation still propagates
            result = CapabilityResult(
                success=False,
                summary=f"Capability raised {type(exc).__name__}: {exc}",
                raw={"exception_type": type(exc).__name__, "message": str(exc)},
            )

        evidence = self._write_evidence(
            run_id=state.run_id,
            index=index,
            capability=capability.descriptor.name,
            instruction=instruction,
            result=result,
        )
        state.steps.append(
            StepRecord(
                index=index,
                capability=capability.descriptor.name,
                instruction=instruction,
                decision_summary=decision_summary,
                success=result.success,
                result_summary=result.summary,
                evidence=evidence,
            )
        )
        self._append_event(
            state.run_id,
            {
                "event": "capability_completed",
                "step": index,
                "capability": capability.descriptor.name,
                "success": result.success,
                "summary": result.summary,
                "evidence": to_jsonable(evidence),
            },
        )
        self.save_state(state)
        return result

    def _write_evidence(
        self,
        *,
        run_id: str,
        index: int,
        capability: str,
        instruction: str,
        result: CapabilityResult,
    ) -> EvidenceRef:
        payload = {
            "step": index,
            "capability": capability,
            "instruction": instruction,
            "success": result.success,
            "summary": result.summary,
            "raw": to_jsonable(result.raw),
            "captured_at": utc_now(),
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in capability)[:80]
        path = self._evidence_dir(run_id) / f"{index:04d}-{safe_name}-{digest[:10]}.json"
        path.write_bytes(content)
        return EvidenceRef(path=str(path), sha256=digest)

    def _append_event(self, run_id: str, event: dict[str, object]) -> None:
        event = {"at": utc_now(), **event}
        path = self._run_dir(run_id) / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def _evidence_dir(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "evidence"

    def _state_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "state.json"
