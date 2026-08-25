"""Declarative Target capability built on PyRIT's TargetRegistry."""

from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Coroutine, TypeVar

from pyromorphit.capabilities.catalog import CatalogCapability, to_jsonable
from pyromorphit.model import ActionRecord, ActionRequest, ExecutionResult

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run a PyRIT coroutine from normal agent/tool code, even if a loop already exists."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@dataclass(frozen=True)
class TargetHandle:
    name: str
    type_name: str
    action_id: str | None = None


class TargetCapability:
    """Create, persist, restore, inspect, and invoke PyRIT targets without adapter code."""

    def __init__(self, harness: Any) -> None:
        self.harness = harness
        self.catalog = CatalogCapability()
        self._definition_dir = harness.run_dir / "definitions" / "targets"
        self._definition_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _registry() -> Any:
        return CatalogCapability._registry("target")

    def list_types(self) -> list[dict[str, Any]]:
        return self.catalog.list_types("target")

    def describe_type(self, name: str) -> dict[str, Any]:
        return self.catalog.describe("target", name)

    def _definition_path(self, name: str) -> Path:
        safe = name.replace("/", "_").replace("\\", "_")
        if safe in {"", ".", ".."}:
            raise ValueError("target name must not be empty")
        return self._definition_dir / f"{safe}.json"

    @staticmethod
    def _write_private_json(path: Path, data: dict[str, Any]) -> None:
        raw = (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)

    def create(
        self,
        *,
        name: str,
        type_name: str,
        parameters: dict[str, Any],
        persist_definition: bool = True,
        human_authorized: bool = False,
    ) -> TargetHandle:
        """Instantiate a PyRIT target from data, not user-authored Python."""
        request = ActionRequest(
            capability="pyrit_target",
            operation="target.create",
            args=(name, type_name),
            human_authorized=human_authorized,
            metadata={"target_name": name, "target_type": type_name, "parameter_names": sorted(parameters)},
        )

        def runner() -> ExecutionResult:
            registry = self._registry()
            instance = registry.create_instance(type_name, **parameters)
            registry.instances.register(instance, name=name, metadata={"created_by": "pyromorphit"})
            if persist_definition:
                self._write_private_json(
                    self._definition_path(name),
                    {"name": name, "type_name": type_name, "parameters": parameters},
                )
            body = json.dumps(
                {"name": name, "type_name": type_name, "identifier": to_jsonable(instance.get_identifier())},
                ensure_ascii=False,
            ).encode("utf-8")
            return ExecutionResult(command=("pyrit_target", "create", name), returncode=0, stdout=body, stderr=b"")

        record = self.harness.execute(request=request, runner=runner)
        if not record.succeeded:
            raise RuntimeError(f"Target creation failed; inspect action {record.action_id}")
        return TargetHandle(name=name, type_name=type_name, action_id=record.action_id)

    def get(self, name: str) -> Any:
        """Return an in-memory target or recreate it from the private declarative definition."""
        registry = self._registry()
        existing = registry.instances.get(name)
        if existing is not None:
            return existing
        path = self._definition_path(name)
        if not path.exists():
            raise KeyError(f"Target {name!r} has not been defined in this run")
        with path.open("r", encoding="utf-8") as fh:
            definition = json.load(fh)
        instance = registry.create_instance(definition["type_name"], **definition["parameters"])
        registry.instances.register(instance, name=name, metadata={"restored_by": "pyromorphit"})
        return instance

    def send(self, *, name: str, prompt: str, human_authorized: bool = False) -> ActionRecord:
        """Send one prompt through a named target; callers do not construct PyRIT Message objects."""
        if not prompt:
            raise ValueError("prompt must not be empty")
        request = ActionRequest(
            capability="pyrit_target",
            operation="target.send",
            args=(name,),
            human_authorized=human_authorized,
            metadata={"target_name": name},
        )

        def runner() -> ExecutionResult:
            try:
                from pyrit.models import Message, MessagePiece
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("PyRIT is not installed") from exc
            target = self.get(name)
            message = Message(
                message_pieces=[
                    MessagePiece(role="user", original_value=prompt, original_value_data_type="text")
                ]
            )
            response = run_async(target.send_prompt_async(message=message))
            body = json.dumps(to_jsonable(response), ensure_ascii=False).encode("utf-8")
            return ExecutionResult(command=("pyrit_target", "send", name), returncode=0, stdout=body, stderr=b"")

        return self.harness.execute(request=request, runner=runner)
