"""Small, dependency-free models used by the Pyromorphit harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    """Authoritative run status.

    These names are internal facts. User-facing agents should translate them into
    domain language instead of exposing the enum as workflow ceremony.
    """

    RUNNING = "RUNNING"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    BLOCKED = "BLOCKED"
    FAILED_ACTION = "FAILED_ACTION"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class ActionRequest:
    """A deterministic capability invocation proposed by the host Agent."""

    capability: str
    operation: str
    args: tuple[str, ...]
    human_authorized: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["args"] = list(self.args)
        return data


@dataclass(frozen=True)
class ExecutionResult:
    """Raw deterministic execution result returned by a capability runner."""

    command: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class EvidenceRef:
    """Reference to raw evidence stored by the Harness."""

    kind: str
    path: str
    sha256: str
    size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionRecord:
    """Authoritative summary of one completed or failed action."""

    action_id: str
    capability: str
    operation: str
    args: tuple[str, ...]
    command: tuple[str, ...]
    returncode: int
    started_at: str
    finished_at: str
    stdout: EvidenceRef
    stderr: EvidenceRef
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and self.error is None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["args"] = list(self.args)
        data["command"] = list(self.command)
        return data
