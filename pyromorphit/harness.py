from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import Objective, SessionState, TestSession
from .recorder import SessionRecorder


@dataclass(frozen=True)
class HarnessEvent:
    type: str
    session_id: str
    payload: dict[str, Any]
    timestamp: str

    @classmethod
    def create(cls, type: str, session_id: str, payload: dict[str, Any] | None = None) -> "HarnessEvent":
        return cls(
            type=type,
            session_id=session_id,
            payload=payload or {},
            timestamp=datetime.now(UTC).isoformat(),
        )


class Harness:
    """Thin deterministic runtime used by an external agentic orchestrator.

    This class deliberately contains no LLM calls and no red-team strategy loop.
    It protects durable state and records lifecycle events. Semantic decisions belong
    to the Agent and Skills.
    """

    def __init__(self, recorder: SessionRecorder | None = None) -> None:
        self.recorder = recorder or SessionRecorder()

    def create_session(self, objective: Objective, skill_name: str) -> TestSession:
        session = TestSession(
            id=uuid.uuid4().hex[:12],
            skill_name=skill_name,
            objective=objective,
            state=SessionState.OBJECTIVE_READY,
        )
        self.recorder.save_session(session)
        self.record_event(
            session,
            "ObjectiveCreated",
            {
                "skill_name": skill_name,
                "objective": objective.description,
                "success_criteria": objective.success_criteria,
                "failure_boundaries": objective.failure_boundaries,
            },
        )
        return session

    def transition(self, session: TestSession, state: SessionState, reason: str = "") -> None:
        previous = session.state
        session.state = state
        self.recorder.save_session(session)
        self.record_event(
            session,
            "StateTransitioned",
            {"from": str(previous), "to": str(state), "reason": reason},
        )

    def record_event(self, session: TestSession, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self.recorder.append_event(HarnessEvent.create(event_type, session.id, payload).__dict__, session)
