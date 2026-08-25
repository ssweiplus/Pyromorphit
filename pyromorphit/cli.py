"""Maintainer/agent CLI for the Pyromorphit capability and Harness surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from pyromorphit.model import RunStatus
from pyromorphit.session import PyromorphitSession


def _workspace(value: str) -> Path:
    return Path(value).expanduser()


def _json_object(value: str | None) -> dict[str, Any]:
    if value is None:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("expected a JSON object")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyromorphit",
        description=(
            "Agent-facing PyRIT capabilities with durable truth/evidence. "
            "Humans may stay in one conversation instead of writing access code."
        ),
    )
    parser.add_argument("--workspace", type=_workspace, default=Path(".pyromorphit"))
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="create a durable run")
    start.add_argument("--objective", required=True)
    start.add_argument("--max-concurrency", type=int, default=1)

    catalog = sub.add_parser("catalog", help="discover a PyRIT Target/Scenario/Converter/Scorer contract")
    catalog.add_argument("--kind", required=True, choices=["target", "scenario", "converter", "scorer"])
    catalog.add_argument("--name")

    define_http = sub.add_parser("define-http", help="define a PyRIT HTTPTarget from a raw request; no adapter code")
    define_http.add_argument("--run-id", required=True)
    define_http.add_argument("--name", required=True)
    define_http.add_argument("--request-file", type=Path, required=True)
    define_http.add_argument("--prompt-marker", default="{PROMPT}")
    define_http.add_argument("--no-tls", action="store_true")
    define_http.add_argument("--no-follow-redirects", action="store_true")
    define_http.add_argument("--max-requests-per-minute", type=int)

    send = sub.add_parser("send", help="send a prompt through a named Target")
    send.add_argument("--run-id", required=True)
    send.add_argument("--target", required=True)
    prompt_group = send.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file", type=Path)

    scenario = sub.add_parser("run-scenario", help="run a named Scenario against a named Target")
    scenario.add_argument("--run-id", required=True)
    scenario.add_argument("--scenario", required=True)
    scenario.add_argument("--target", required=True)
    scenario.add_argument("--technique", action="append", dest="techniques")
    scenario.add_argument("--scenario-params-json")
    scenario.add_argument("--run-params-json")
    scenario.add_argument("--resume-id")

    execute = sub.add_parser("exec", help="escape hatch: invoke pyrit_scan directly")
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
        print(json.dumps({"run_id": session.run_id, "objective": session.harness.objective,
                          "status": session.harness.latest_status().value}, ensure_ascii=False))
        return 0

    if ns.command == "catalog":
        # Catalog discovery does not need a run because it is read-only PyRIT metadata.
        from pyromorphit.capabilities import CatalogCapability
        catalog = CatalogCapability()
        result = catalog.describe(ns.kind, ns.name) if ns.name else catalog.list_types(ns.kind)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    session = _session(ns.workspace, ns.run_id)

    if ns.command == "define-http":
        raw_request = ns.request_file.read_text(encoding="utf-8")
        handle = session.http.define(
            name=ns.name,
            raw_request=raw_request,
            prompt_marker=ns.prompt_marker,
            use_tls=not ns.no_tls,
            follow_redirects=not ns.no_follow_redirects,
            max_requests_per_minute=ns.max_requests_per_minute,
        )
        print(json.dumps({"target": handle.name, "type": handle.type_name, "action_id": handle.action_id}))
        return 0

    if ns.command == "send":
        prompt = ns.prompt if ns.prompt is not None else ns.prompt_file.read_text(encoding="utf-8")
        record = session.targets.send(name=ns.target, prompt=prompt)
        print(json.dumps(record.to_dict(), ensure_ascii=False))
        return 0 if record.succeeded else 1

    if ns.command == "run-scenario":
        record = session.scenarios.run(
            name=ns.scenario,
            target=ns.target,
            techniques=ns.techniques,
            scenario_params=_json_object(ns.scenario_params_json),
            run_params=_json_object(ns.run_params_json),
            scenario_result_id=ns.resume_id,
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False))
        return 0 if record.succeeded else 1

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
        print(json.dumps({"run_id": session.run_id, "objective": session.harness.objective,
                          "constraints": session.harness.constraints,
                          "status": session.harness.latest_status().value,
                          "actions": [record.to_dict() for record in actions]}, ensure_ascii=False))
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
