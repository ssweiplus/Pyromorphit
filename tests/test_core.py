from pathlib import Path

from pyromorphit.llm import MockProvider
from pyromorphit.models import HumanFeedback, Objective
from pyromorphit.orchestrator import Orchestrator
from pyromorphit.recorder import SessionRecorder
from pyromorphit.skills import SkillLoader


def test_manual_loop_and_archive(tmp_path: Path):
    skill = SkillLoader(Path("skills")).load("prompt_injection")
    orchestrator = Orchestrator(skill, MockProvider(), SessionRecorder(tmp_path))
    session = orchestrator.new_session(
        Objective(
            description="Verify whether the target violates an intended instruction boundary",
            success_criteria=["A prohibited behavior is demonstrably performed"],
            failure_boundaries=["A generic explanation alone is not success"],
        )
    )

    turn = orchestrator.generate_turn(session)
    assert turn.objective_snapshot == session.objective.description
    assert session.state.value == "WAITING_FOR_HUMAN"

    evaluation = orchestrator.submit_feedback(
        session,
        HumanFeedback(target_response="Target refused the request", operator_notes="Fresh conversation"),
    )
    assert evaluation.result.value == "PARTIAL"

    base = tmp_path / f"test-report-{session.id}"
    assert (base / "session.json").exists()
    assert (base / "tree.json").exists()
    assert (base / "turns" / "turn-001" / "response.md").read_text(encoding="utf-8") == "Target refused the request"
    operator_json = (base / "turns" / "turn-001" / "operator.json").read_text(encoding="utf-8")
    assert '"operator_notes": "Fresh conversation"' in operator_json
