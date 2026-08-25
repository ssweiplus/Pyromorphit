from __future__ import annotations

import pytest

from pyromorphit.harness import Harness, PermissionPolicy
from pyromorphit.model import ExecutionResult
from pyromorphit.pyrit_cli import PyRITCLI


def test_prepare_run_injects_default_concurrency():
    cli = PyRITCLI()
    request = cli.prepare_request(
        args=("run", "airt.cyber", "--target", "openai_chat"),
        max_concurrency=1,
    )

    assert request.operation == "run"
    assert request.args[-2:] == ("--max-concurrency", "1")
    assert request.metadata["max_concurrency"] == 1


def test_prepare_run_preserves_explicit_concurrency_for_policy_check():
    cli = PyRITCLI()
    request = cli.prepare_request(
        args=(
            "run",
            "airt.cyber",
            "--target",
            "openai_chat",
            "--max-concurrency",
            "2",
        ),
        max_concurrency=1,
    )

    assert request.args.count("--max-concurrency") == 1
    assert request.metadata["max_concurrency"] == 2


def test_harness_rejects_explicit_concurrency_above_policy(tmp_path):
    cli = PyRITCLI()
    request = cli.prepare_request(
        args=("run", "airt.cyber", "--target", "openai_chat", "--max-concurrency", "2"),
        max_concurrency=1,
    )
    harness = Harness.create(
        workspace=tmp_path,
        objective="authorized test",
        policy=PermissionPolicy(max_concurrency=1),
    )

    with pytest.raises(PermissionError, match="exceeds allowed maximum"):
        harness.execute(
            request=request,
            runner=lambda: ExecutionResult(
                command=("fake-pyrit",),
                returncode=0,
                stdout=b"",
                stderr=b"",
            ),
        )


def test_operation_can_follow_global_cli_options():
    cli = PyRITCLI()
    request = cli.prepare_request(
        args=("--server-url", "http://127.0.0.1:8000", "list-targets"),
        max_concurrency=1,
    )
    assert request.operation == "list-targets"


def test_unknown_operation_is_rejected_before_process_execution():
    cli = PyRITCLI()
    with pytest.raises(ValueError, match="supported pyrit_scan operation"):
        cli.prepare_request(args=("made-up-command",), max_concurrency=1)
