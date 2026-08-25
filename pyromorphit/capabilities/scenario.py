"""Scenario discovery and execution without user-authored orchestration code."""

from __future__ import annotations

import json
from typing import Any, Sequence

from pyromorphit.capabilities.catalog import CatalogCapability, to_jsonable
from pyromorphit.capabilities.target import TargetCapability
from pyromorphit.model import ActionRecord, ActionRequest, ExecutionResult


class ScenarioCapability:
    """Describe and run PyRIT scenarios from declarative parameters."""

    def __init__(self, harness: Any, targets: TargetCapability) -> None:
        self.harness = harness
        self.targets = targets
        self.catalog = CatalogCapability()

    @staticmethod
    def _registry() -> Any:
        return CatalogCapability._registry("scenario")

    def list_types(self) -> list[dict[str, Any]]:
        return self.catalog.list_types("scenario")

    def describe_type(self, name: str) -> dict[str, Any]:
        return self.catalog.describe("scenario", name)

    async def run(
        self,
        *,
        name: str,
        target: str,
        techniques: Sequence[str] | None = None,
        scenario_params: dict[str, Any] | None = None,
        run_params: dict[str, Any] | None = None,
        scenario_result_id: str | None = None,
        human_authorized: bool = False,
    ) -> ActionRecord:
        """Run a scenario against a named target using data-only configuration."""
        effective_run_params = dict(run_params or {})
        effective_run_params["objective_target"] = self.targets.get(target)
        effective_run_params["max_concurrency"] = self.harness.policy.max_concurrency
        if techniques is not None:
            effective_run_params["scenario_techniques"] = list(techniques)

        request = ActionRequest(
            capability="pyrit_scenario",
            operation="scenario.run",
            args=(name, target),
            human_authorized=human_authorized,
            metadata={
                "scenario": name,
                "target": target,
                "techniques": list(techniques or []),
                "max_concurrency": self.harness.policy.max_concurrency,
                "scenario_result_id": scenario_result_id,
            },
        )

        async def runner() -> ExecutionResult:
            registry = self._registry()
            scenario = await registry.create_and_initialize_async(
                name,
                scenario_params=dict(scenario_params or {}),
                scenario_result_id=scenario_result_id,
                **effective_run_params,
            )
            result = await scenario.run_async()
            body = json.dumps(to_jsonable(result), ensure_ascii=False).encode("utf-8")
            return ExecutionResult(
                command=("pyrit_scenario", "run", name, target),
                returncode=0,
                stdout=body,
                stderr=b"",
            )

        return await self.harness.execute_async(request=request, runner=runner)
