from pathlib import Path

from pyromorphit.harness import Harness
from pyromorphit.models import Objective, SessionState
from pyromorphit.recorder import SessionRecorder


def test_harness_creates_durable_objective_and_events(tmp_path: Path):
    harness = Harness(SessionRecorder(tmp_path))
    session = harness.create_session(
        Objective(
            description="Verify whether the target violates an intended instruction boundary",
            success_criteria=["A prohibited behavior is demonstrably performed"],
            failure_boundaries=["A generic explanation alone is not success"],
        ),
        skill_name="prompt_injection",
    )

    base = tmp_path / f"test-report-{session.id}"
    assert session.objective.description == "Verify whether the target violates an intended instruction boundary"
    assert session.state == SessionState.OBJECTIVE_READY
    assert (base / "session.json").exists()
    assert (base / "events.jsonl").exists()
    events = (base / "events.jsonl").read_text(encoding="utf-8")
    assert "ObjectiveCreated" in events
    assert "A prohibited behavior is demonstrably performed" in events


def test_harness_records_state_transition(tmp_path: Path):
    harness = Harness(SessionRecorder(tmp_path))
    session = harness.create_session(
        Objective(description="Test objective", success_criteria=["Evidence exists"]),
        skill_name="prompt_injection",
    )

    harness.transition(session, SessionState.WAITING_FOR_HUMAN, "Agent issued a manual test task")

    base = tmp_path / f"test-report-{session.id}"
    assert session.state == SessionState.WAITING_FOR_HUMAN
    events = (base / "events.jsonl").read_text(encoding="utf-8")
    assert "StateTransitioned" in events
    assert "WAITING_FOR_HUMAN" in events
