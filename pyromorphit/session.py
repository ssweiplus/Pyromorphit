"""Thin composition facade for a host Agent.

The facade intentionally contains no attack-selection or semantic retry policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from pyromorphit.harness import Harness, PermissionPolicy
from pyromorphit.model import ActionRecord, RunStatus
from pyromorphit.pyrit_cli import PyRITCLI


@dataclass
class PyromorphitSession:
    harness: Harness
    pyrit_cli: PyRITCLI

    @classmethod
    def create(
        cls,
        *,
        workspace: str | Path,
        objective: str,
        constraints: dict[str, Any] | None = None,
        max_concurrency: int = 1,
        pyrit_command: Sequence[str] = ("pyrit_scan",),
        pyrit_env: Mapping[str, str] | None = None,
    ) -> "PyromorphitSession":
        policy = PermissionPolicy(max_concurrency=max_concurrency)
        harness = Harness.create(
            workspace=workspace,
            objective=objective,
            constraints=constraints,
            policy=policy,
        )
        return cls(
            harness=harness,
            pyrit_cli=PyRITCLI(
                command=tuple(pyrit_command),
                env=dict(pyrit_env or {}),
            ),
        )

    @classmethod
    def open(
        cls,
        *,
        workspace: str | Path,
        run_id: str,
        pyrit_command: Sequence[str] = ("pyrit_scan",),
        pyrit_env: Mapping[str, str] | None = None,
    ) -> "PyromorphitSession":
        return cls(
            harness=Harness.open(workspace=workspace, run_id=run_id),
            pyrit_cli=PyRITCLI(
                command=tuple(pyrit_command),
                env=dict(pyrit_env or {}),
            ),
        )

    @property
    def run_id(self) -> str:
        return self.harness.run_id

    def execute_pyrit(
        self,
        args: Sequence[str],
        *,
        human_authorized: bool = False,
        timeout_s: float | None = None,
    ) -> ActionRecord:
        request = self.pyrit_cli.prepare_request(
            args=args,
            max_concurrency=self.harness.policy.max_concurrency,
            human_authorized=human_authorized,
        )
        return self.harness.execute(
            request=request,
            runner=lambda: self.pyrit_cli.run(args=request.args, timeout_s=timeout_s),
        )

    def add_human_note(
        self,
        *,
        action_taken: str | None = None,
        context: str | None = None,
        correction: str | None = None,
        instruction: str | None = None,
        authorization: str | None = None,
    ) -> None:
        self.harness.add_human_note(
            action_taken=action_taken,
            context=context,
            correction=correction,
            instruction=instruction,
            authorization=authorization,
        )

    def set_status(self, status: RunStatus, *, reason: str | None = None) -> None:
        self.harness.set_status(status, reason=reason)
