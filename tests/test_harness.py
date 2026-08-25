from __future__ import annotations

import hashlib

import pytest

from pyromorphit.harness import Harness, PermissionPolicy
from pyromorphit.model import ActionRequest, ExecutionResult, RunStatus


def _request(
    operation: str = "list-targets",
    *,
    human_authorized: bool = False,
    metadata: dict[str, object] | None = None,
) -> ActionRequest:
    return ActionRequest(
        capability="pyrit_scan",
        operation=operation,
        args=(operation,),
        human_authorized=human_authorized,
        metadata=dict(metadata or {}),
    )


def test_raw_evidence_survives_reopen(tmp_path):
    harness = Harness.create(workspace=tmp_path, objective="authorized test")
    raw_stdout = b"raw\x00stdout\n"
    raw_stderr = b"warning\n"

    record = harness.execute(
        request=_request(),
        runner=lambda: ExecutionResult(
            command=("fake-pyrit", "list-targets"),
            returncode=0,
            stdout=raw_stdout,
            stderr=raw_stderr,
        ),
    )

    assert record.succeeded
    assert (harness.run_dir / record.stdout.path).read_bytes() == raw_stdout
    assert (harness.run_dir / record.stderr.path).read_bytes() == raw_stderr
    assert record.stdout.sha256 == hashlib.sha256(raw_stdout).hexdigest()
    assert record.stderr.sha256 == hashlib.sha256(raw_stderr).hexdigest()

    reopened = Harness.open(workspace=tmp_path, run_id=harness.run_id)
    actions = reopened.completed_actions()
    assert len(actions) == 1
    assert actions[0].action_id == record.action_id
    assert actions[0].stdout.sha256 == record.stdout.sha256
    assert reopened.latest_status() is RunStatus.PARTIALLY_COMPLETE


def test_failed_action_does_not_erase_prior_success(tmp_path):
    harness = Harness.create(workspace=tmp_path, objective="authorized test")

    first = harness.execute(
        request=_request("list-targets"),
        runner=lambda: ExecutionResult(
            command=("fake-pyrit", "list-targets"),
            returncode=0,
            stdout=b"target-a\n",
            stderr=b"",
        ),
    )

    def fail() -> ExecutionResult:
        raise RuntimeError("backend unavailable")

    second = harness.execute(request=_request("list-scenarios"), runner=fail)

    assert first.succeeded
    assert not second.succeeded
    assert second.error == "RuntimeError: backend unavailable"
    assert (harness.run_dir / first.stdout.path).read_bytes() == b"target-a\n"
    assert len(harness.completed_actions()) == 2
    assert harness.latest_status() is RunStatus.FAILED_ACTION


def test_human_required_operation_needs_explicit_authorization(tmp_path):
    harness = Harness.create(workspace=tmp_path, objective="authorized test")

    with pytest.raises(PermissionError, match="explicit human authorization"):
        harness.execute(
            request=_request("stop-server"),
            runner=lambda: ExecutionResult(
                command=("fake-pyrit", "stop-server"),
                returncode=0,
                stdout=b"",
                stderr=b"",
            ),
        )

    authorized = harness.execute(
        request=_request("stop-server", human_authorized=True),
        runner=lambda: ExecutionResult(
            command=("fake-pyrit", "stop-server"),
            returncode=0,
            stdout=b"stopped\n",
            stderr=b"",
        ),
    )
    assert authorized.succeeded


def test_concurrency_ceiling_is_deterministic(tmp_path):
    harness = Harness.create(
        workspace=tmp_path,
        objective="authorized test",
        policy=PermissionPolicy(max_concurrency=1),
    )

    with pytest.raises(PermissionError, match="exceeds allowed maximum"):
        harness.execute(
            request=_request("run", metadata={"max_concurrency": 2}),
            runner=lambda: ExecutionResult(
                command=("fake-pyrit", "run"),
                returncode=0,
                stdout=b"",
                stderr=b"",
            ),
        )


def test_human_note_can_capture_action_context_correction_and_instruction(tmp_path):
    harness = Harness.create(workspace=tmp_path, objective="authorized test")
    harness.add_human_note(
        action_taken="logged in again",
        context="old session cannot be resumed",
        correction="token was valid; server ended the session",
        instruction="continue from the current page",
        authorization="continue within the existing target scope",
    )

    event = harness.events()[-1]
    assert event["event"] == "HUMAN_NOTE"
    assert event["payload"]["action_taken"] == "logged in again"
    assert event["payload"]["context"] == "old session cannot be resumed"
    assert event["payload"]["correction"] == "token was valid; server ended the session"
    assert event["payload"]["instruction"] == "continue from the current page"
    assert event["payload"]["authorization"] == "continue within the existing target scope"
