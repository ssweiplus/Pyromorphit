"""Composition facade for a host Agent.

The facade exposes independently meaningful PyRIT capabilities. It intentionally
contains no attack-selection or semantic retry policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from pyromorphit.capabilities import CatalogCapability, HTTPTargetCapability, ScenarioCapability, TargetCapability
from pyromorphit.harness import Harness, PermissionPolicy
from pyromorphit.model import ActionRecord, RunStatus
from pyromorphit.pyrit_cli import PyRITCLI


_AGENT_CAPABILITIES = frozenset({"pyrit_scan", "pyrit_target", "pyrit_scenario"})
_AGENT_OPERATIONS = frozenset(
    {
        "run",
        "list-scenarios",
        "list-initializers",
        "list-targets",
        "list-converters",
        "scenario-results",
        "scenario-history",
        "start-server",
        "target.create",
        "target.send",
        "scenario.run",
    }
)
_HUMAN_OPERATIONS = frozenset({"add-initializer", "stop-server"})


def _agent_policy(max_concurrency: int) -> PermissionPolicy:
    return PermissionPolicy(
        allowed_capabilities=_AGENT_CAPABILITIES,
        allowed_operations=_AGENT_OPERATIONS,
        human_required_operations=_HUMAN_OPERATIONS,
        max_concurrency=max_concurrency,
    )


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
        harness = Harness.create(
            workspace=workspace,
            objective=objective,
            constraints=constraints,
            policy=_agent_policy(max_concurrency),
        )
        return cls(
            harness=harness,
            pyrit_cli=PyRITCLI(command=tuple(pyrit_command), env=dict(pyrit_env or {})),
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
        harness = Harness.open(workspace=workspace, run_id=run_id)
        # Runs created by the first slice only knew about pyrit_scan. Expanding the
        # policy here is a compatibility migration; the saved concurrency ceiling remains authoritative.
        harness.policy = _agent_policy(harness.policy.max_concurrency)
        return cls(
            harness=harness,
            pyrit_cli=PyRITCLI(command=tuple(pyrit_command), env=dict(pyrit_env or {})),
        )

    @property
    def run_id(self) -> str:
        return self.harness.run_id

    @property
    def catalog(self) -> CatalogCapability:
        return CatalogCapability()

    @property
    def targets(self) -> TargetCapability:
        return TargetCapability(self.harness)

    @property
    def http(self) -> HTTPTargetCapability:
        return HTTPTargetCapability(self.targets)

    @property
    def scenarios(self) -> ScenarioCapability:
        return ScenarioCapability(self.harness, self.targets)

    def execute_pyrit(
        self,
        args: Sequence[str],
        *,
        human_authorized: bool = False,
        timeout_s: float | None = None,
    ) -> ActionRecord:
        """Escape hatch for PyRIT CLI operations not yet promoted to a capability."""
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
