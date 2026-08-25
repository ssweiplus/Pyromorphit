"""Maintainer/agent CLI for the Pyromorphit Harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pyromorphit.model import RunStatus
from pyromorphit.session import PyromorphitSession


def _workspace(value: str) -> Path:
    return Path(value).expanduser()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyromorphit",
        description=(
            "Durable control/evidence harness for a host Agent using PyRIT. "
            "This CLI is an execution surface, not the end-user workflow."
        ),
    )
    parser.add_argument("--workspace", type=_workspace, default=Path(".pyromorphit"))
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="create a durable run")
    start.add_argument("--objective", required=True)
    start.add_argument("--max-concurrency", type=int, default=1)

    execute = sub.add_parser("exec", help="invoke pyrit_scan inside an existing run")
    execute.add_argument("--run-id", required=True)
    execute.add_argument("--authorized", action="store_true")
    execute.add_argument("--timeout", type=float, default=None)
    execute.add_argument("pyrit_args", nargs=argparse.REMAINDER)

    status = sub.add_parser("status", help="inspect authoritative run status")
    status.add_argument("--run-id", required=True)

    note = sub.add_parser("note", help="record composable human input")
    note.add_argument("--run-id", required=True)
    note.add_argument("--action-taken")
    note.add_argument("--context")
    note.add_argument("--correction")
    note.add_argument("--instruction")
    note.add_argument("--authorization")

    finish = sub.add_parser("finish", help="mark the run completed")
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--reason")

    return parser


def _clean_remainder(args: Sequence[str]) -> list[str]:
    values = list(args)
    if values and values[0] == "--":
        values = values[1:]
    if not values:
        raise ValueError("exec requires pyrit_scan arguments after '--'")
    return values


def _session(workspace: Path, run_id: str) -> PyromorphitSession:
    return PyromorphitSession.open(workspace=workspace, run_id=run_id)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)

    if ns.command == "start":
        session = PyromorphitSession.create(
            workspace=ns.workspace,
            objective=ns.objective,
            max_concurrency=ns.max_concurrency,
        )
        print(
            json.dumps(
                {
                    "run_id": session.run_id,
                    "objective": session.harness.objective,
                    "status": session.harness.latest_status().value,
                },
                ensure_ascii=False,
            )
        )
        return 0

    session = _session(ns.workspace, ns.run_id)

    if ns.command == "exec":
        record = session.execute_pyrit(
            _clean_remainder(ns.pyrit_args),
            human_authorized=ns.authorized,
            timeout_s=ns.timeout,
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False))
        return 0 if record.succeeded else 1

    if ns.command == "status":
        actions = session.harness.completed_actions()
        print(
            json.dumps(
                {
                    "run_id": session.run_id,
                    "objective": session.harness.objective,
                    "constraints": session.harness.constraints,
                    "status": session.harness.latest_status().value,
                    "actions": [record.to_dict() for record in actions],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if ns.command == "note":
        session.add_human_note(
            action_taken=ns.action_taken,
            context=ns.context,
            correction=ns.correction,
            instruction=ns.instruction,
            authorization=ns.authorization,
        )
        print(json.dumps({"recorded": True, "run_id": session.run_id}))
        return 0

    if ns.command == "finish":
        session.set_status(RunStatus.COMPLETED, reason=ns.reason)
        print(json.dumps({"run_id": session.run_id, "status": "COMPLETED"}))
        return 0

    parser.error(f"unsupported command: {ns.command}")
    return 2
