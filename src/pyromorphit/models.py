"""Small, serializable models shared by the agent and harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class RunStatus(str, Enum):
    """Authoritative run lifecycle states."""

    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    PARTIALLY_COMPLETE = "partially_complete"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionKind(str, Enum):
    """Semantic actions the planner can ask the harness to perform."""

    RUN_CAPABILITY = "run"
    ASK_HUMAN = "ask_human"
    FINISH = "finish"
    PAUSE = "pause"


@dataclass(slots=True)
class AgentDecision:
    """One planner decision. ``summary`` is an observable reason, not chain-of-thought."""

    kind: DecisionKind
    capability: str | None = None
    instruction: str | None = None
    summary: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentDecision":
        action = str(value.get("action", "")).strip().lower()
        aliases = {
            "run": DecisionKind.RUN_CAPABILITY,
            "run_capability": DecisionKind.RUN_CAPABILITY,
            "ask_human": DecisionKind.ASK_HUMAN,
            "finish": DecisionKind.FINISH,
            "pause": DecisionKind.PAUSE,
        }
        if action not in aliases:
            raise ValueError(f"Unsupported planner action: {action!r}")
        decision = cls(
            kind=aliases[action],
            capability=_optional_text(value.get("capability")),
            instruction=_optional_text(value.get("instruction")),
            summary=str(value.get("summary", "")).strip(),
        )
        if decision.kind is DecisionKind.RUN_CAPABILITY and not decision.capability:
            raise ValueError("A run decision requires 'capability'.")
        if decision.kind in {DecisionKind.RUN_CAPABILITY, DecisionKind.ASK_HUMAN} and not decision.instruction:
            raise ValueError(f"A {decision.kind.value!r} decision requires 'instruction'.")
        return decision


@dataclass(slots=True)
class CapabilityDescriptor:
    """Planner-facing description of an independently meaningful capability."""

    name: str
    description: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CapabilityResult:
    """Normalized capability result; raw evidence is retained separately by the harness."""

    success: bool
    summary: str
    raw: Any = None


@dataclass(slots=True)
class EvidenceRef:
    """Pointer to immutable-ish raw evidence for one executed step."""

    path: str
    sha256: str


@dataclass(slots=True)
class StepRecord:
    """Compact, planner-visible record of a completed capability invocation."""

    index: int
    capability: str
    instruction: str
    decision_summary: str
    success: bool
    result_summary: str
    evidence: EvidenceRef
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class RunState:
    """Durable run whiteboard. It remembers the run; it does not decide the run."""

    run_id: str
    goal: str
    status: RunStatus = RunStatus.RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    human_inputs: list[str] = field(default_factory=list)
    pending_question: str | None = None
    final_summary: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @property
    def failed_steps(self) -> int:
        return sum(1 for step in self.steps if not step.success)

    def compact_view(self, *, max_steps: int = 12) -> dict[str, Any]:
        """Return a bounded semantic view for a planner prompt."""
        recent = self.steps[-max_steps:]
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "status": self.status.value,
            "recent_steps": [
                {
                    "index": s.index,
                    "capability": s.capability,
                    "instruction": s.instruction,
                    "success": s.success,
                    "result_summary": s.result_summary,
                }
                for s in recent
            ],
            "human_inputs": self.human_inputs[-6:],
            "pending_question": self.pending_question,
        }

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RunState":
        steps = [
            StepRecord(
                index=int(s["index"]),
                capability=str(s["capability"]),
                instruction=str(s["instruction"]),
                decision_summary=str(s.get("decision_summary", "")),
                success=bool(s["success"]),
                result_summary=str(s.get("result_summary", "")),
                evidence=EvidenceRef(**s["evidence"]),
                created_at=str(s.get("created_at", utc_now())),
            )
            for s in value.get("steps", [])
        ]
        return cls(
            run_id=str(value["run_id"]),
            goal=str(value["goal"]),
            status=RunStatus(value.get("status", RunStatus.RUNNING.value)),
            steps=steps,
            human_inputs=[str(x) for x in value.get("human_inputs", [])],
            pending_question=_optional_text(value.get("pending_question")),
            final_summary=_optional_text(value.get("final_summary")),
            created_at=str(value.get("created_at", utc_now())),
            updated_at=str(value.get("updated_at", utc_now())),
        )


def to_jsonable(value: Any) -> Any:
    """Best-effort conversion that never discards raw evidence just because it is custom typed."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return to_jsonable(model_dump(mode="json"))
        except TypeError:
            return to_jsonable(model_dump())
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "__dict__"):
        return to_jsonable(vars(value))
    return repr(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
