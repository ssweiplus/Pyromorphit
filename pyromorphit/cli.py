from __future__ import annotations

import argparse

from .llm import provider_from_env
from .models import HumanFeedback, Objective, OperatorAction, SessionState
from .orchestrator import Orchestrator
from .recorder import SessionRecorder
from .skills import SkillLoader


def _multiline(label: str) -> str:
    print(f"{label} (finish with a single line containing .done)")
    lines: list[str] = []
    while True:
        line = input()
        if line == ".done":
            return "\n".join(lines)
        lines.append(line)


def _csv(label: str) -> list[str]:
    raw = input(label).strip()
    return [x.strip() for x in raw.split(";") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Pyromorphit human-in-the-loop red-team assistant")
    parser.add_argument("--skill", default="prompt_injection")
    args = parser.parse_args()

    skill = SkillLoader().load(args.skill)
    orchestrator = Orchestrator(skill, provider_from_env(), SessionRecorder())

    print("=== Pyromorphit ===")
    description = input("Test objective: ").strip()
    success = _csv("Success criteria (semicolon separated): ")
    boundaries = _csv("Failure boundaries (semicolon separated, optional): ")
    session = orchestrator.new_session(Objective(description, success, boundaries))
    print(f"Session: {session.id}")

    parent_turn_id: int | None = None
    while True:
        turn = orchestrator.generate_turn(session, parent_turn_id=parent_turn_id)
        print("\n" + "=" * 72)
        print(f"TURN {turn.id}")
        print(f"Objective: {turn.objective_snapshot}")
        print(f"Strategy: {turn.strategy.family} / {turn.strategy.tactic}")
        print(f"Why: {turn.strategy.rationale}")
        print("\nPrompt to execute:\n")
        print(turn.prompt)
        print("\n" + turn.operator_instruction)
        print("=" * 72)

        response = _multiline("Paste target response")
        notes = _multiline("Operator notes; leave empty if none")
        actions: list[OperatorAction] = []
        print("Record operator actions. Examples: new_conversation, manual_edit, retry, environment_change.")
        while True:
            action_type = input("Action type (blank to finish): ").strip()
            if not action_type:
                break
            actions.append(OperatorAction(action_type, input("Action description: ").strip()))

        evaluation = orchestrator.submit_feedback(
            session,
            HumanFeedback(target_response=response, operator_notes=notes, operator_actions=actions),
        )
        print("\nEvaluation")
        print(f"Result: {evaluation.result}")
        print(f"Score: {evaluation.score:.2f}  Confidence: {evaluation.confidence:.2f}")
        print(f"Reason: {evaluation.rationale}")
        print(f"Analysis: {session.turns[-1].analysis}")

        if evaluation.result.value == "SUCCESS":
            print("Objective reached. Session completed.")
            break

        command = input("\nNext action [continue/branch/stop]: ").strip().lower() or "continue"
        if command == "stop":
            session.state = SessionState.STOPPED
            orchestrator.recorder.save_session(session)
            break
        if command == "branch":
            raw = input(f"Branch from turn id [default {turn.id}]: ").strip()
            parent_turn_id = int(raw) if raw else turn.id
        else:
            parent_turn_id = turn.id

    print(f"Archive: test-report-{session.id}/")


if __name__ == "__main__":
    main()
