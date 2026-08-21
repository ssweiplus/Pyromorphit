from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyromorphit.agent import PyromorphAgent
from pyromorphit.harness import ExecutionHarness
from pyromorphit.models import AgentDecision, CapabilityDescriptor, CapabilityResult, DecisionKind, RunStatus


@dataclass
class FakeCapability:
    name: str = "probe"
    fail: bool = False

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(name=self.name, description="test capability", tags=["test"])

    async def execute(self, *, instruction: str) -> CapabilityResult:
        if self.fail:
            raise RuntimeError("local boom")
        return CapabilityResult(success=True, summary=f"observed: {instruction}", raw={"instruction": instruction})


class ScriptedPlanner:
    def __init__(self, decisions: list[AgentDecision]) -> None:
        self.decisions = list(decisions)

    async def decide(self, *, state, capabilities):
        del state, capabilities
        if not self.decisions:
            raise AssertionError("planner script exhausted")
        return self.decisions.pop(0)


@pytest.mark.asyncio
async def test_local_failure_is_preserved_and_run_can_finish(tmp_path):
    planner = ScriptedPlanner(
        [
            AgentDecision(
                kind=DecisionKind.RUN_CAPABILITY,
                capability="probe",
                instruction="first try",
                summary="collect evidence",
            ),
            AgentDecision(kind=DecisionKind.FINISH, summary="enough evidence"),
        ]
    )
    harness = ExecutionHarness(root=tmp_path / "runs")
    agent = PyromorphAgent(planner=planner, capabilities=[FakeCapability(fail=True)], harness=harness)

    state = await agent.run(goal="test recovery")

    assert state.status is RunStatus.PARTIALLY_COMPLETE
    assert len(state.steps) == 1
    assert state.steps[0].success is False
    assert "RuntimeError" in state.steps[0].result_summary
    assert (tmp_path / "runs" / state.run_id / "state.json").exists()
    assert (tmp_path / "runs" / state.run_id / state.steps[0].evidence.path.split(state.run_id + "/")[-1]).exists()


@pytest.mark.asyncio
async def test_human_intervention_can_resume_without_losing_steps(tmp_path):
    first_planner = ScriptedPlanner(
        [
            AgentDecision(
                kind=DecisionKind.RUN_CAPABILITY,
                capability="probe",
                instruction="baseline",
                summary="start",
            ),
            AgentDecision(
                kind=DecisionKind.ASK_HUMAN,
                instruction="Please provide the missing authorization context.",
                summary="authority required",
            ),
        ]
    )
    harness = ExecutionHarness(root=tmp_path / "runs")
    first_agent = PyromorphAgent(planner=first_planner, capabilities=[FakeCapability()], harness=harness)

    waiting = await first_agent.run(goal="test human recovery")
    assert waiting.status is RunStatus.WAITING_FOR_HUMAN
    assert len(waiting.steps) == 1

    second_planner = ScriptedPlanner([AgentDecision(kind=DecisionKind.FINISH, summary="human context received")])
    resumed_agent = PyromorphAgent(planner=second_planner, capabilities=[FakeCapability()], harness=harness)
    done = await resumed_agent.resume(run_id=waiting.run_id, human_input="Authorized for this test scope.")

    assert done.status is RunStatus.COMPLETED
    assert len(done.steps) == 1
    assert done.human_inputs[-1] == "Authorized for this test scope."
