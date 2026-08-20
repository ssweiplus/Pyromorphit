from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class SessionState(StrEnum):
    NEW = "NEW"
    OBJECTIVE_READY = "OBJECTIVE_READY"
    STRATEGY_READY = "STRATEGY_READY"
    PROMPT_READY = "PROMPT_READY"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    EVALUATED = "EVALUATED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"


class EvaluationResult(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"
    NEEDS_HUMAN_JUDGMENT = "NEEDS_HUMAN_JUDGMENT"


@dataclass(frozen=True)
class Objective:
    description: str
    success_criteria: list[str]
    failure_boundaries: list[str] = field(default_factory=list)


@dataclass
class OperatorAction:
    type: str
    description: str = ""


@dataclass
class HumanFeedback:
    target_response: str
    operator_notes: str = ""
    operator_actions: list[OperatorAction] = field(default_factory=list)


@dataclass
class StrategyDecision:
    family: str
    tactic: str
    rationale: str
    preserve: list[str] = field(default_factory=list)
    change: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


@dataclass
class Evaluation:
    result: EvaluationResult
    score: float
    confidence: float
    achieved: list[str] = field(default_factory=list)
    not_achieved: list[str] = field(default_factory=list)
    defenses_observed: list[str] = field(default_factory=list)
    weaknesses_observed: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class Turn:
    id: int
    objective_snapshot: str
    strategy: StrategyDecision
    prompt: str
    operator_instruction: str
    parent_turn_id: int | None = None
    feedback: HumanFeedback | None = None
    evaluation: Evaluation | None = None
    analysis: str = ""


@dataclass
class TestSession:
    id: str
    skill_name: str
    objective: Objective
    state: SessionState = SessionState.NEW
    turns: list[Turn] = field(default_factory=list)
    discovered_behaviors: list[str] = field(default_factory=list)
    observed_defenses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
