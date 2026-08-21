"""Agent-owned semantic orchestration loop."""

from __future__ import annotations

from collections.abc import Iterable

from .harness import ExecutionHarness
from .models import DecisionKind, RunState, RunStatus
from .protocols import Capability, Planner


class PyromorphAgent:
    """Compose capabilities from evidence without turning the harness into a workflow engine."""

    def __init__(
        self,
        *,
        planner: Planner,
        capabilities: Iterable[Capability],
        harness: ExecutionHarness | None = None,
        max_steps: int = 12,
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.planner = planner
        self.harness = harness or ExecutionHarness()
        self.max_steps = max_steps
        self.capabilities = {cap.descriptor.name: cap for cap in capabilities}
        if not self.capabilities:
            raise ValueError("At least one capability is required")

    async def run(self, *, goal: str) -> RunState:
        state = self.harness.start_run(goal=goal)
        return await self._drive(state)

    async def resume(self, *, run_id: str, human_input: str | None = None) -> RunState:
        state = self.harness.load_state(run_id)
        if human_input is not None:
            self.harness.add_human_input(state=state, text=human_input)
        elif state.status in {RunStatus.WAITING_FOR_HUMAN, RunStatus.PAUSED}:
            return state
        elif state.status is RunStatus.COMPLETED:
            return state
        else:
            state.status = RunStatus.RUNNING
            self.harness.save_state(state)
        return await self._drive(state)

    async def _drive(self, state: RunState) -> RunState:
        descriptors = [cap.descriptor for cap in self.capabilities.values()]
        while len(state.steps) < self.max_steps:
            decision = await self.planner.decide(state=state, capabilities=descriptors)

            if decision.kind is DecisionKind.RUN_CAPABILITY:
                capability = self.capabilities.get(decision.capability or "")
                if capability is None:
                    # Make an invalid semantic choice visible as local evidence rather than crashing the run.
                    state.status = RunStatus.WAITING_FOR_HUMAN
                    state.pending_question = (
                        f"Planner requested unknown capability {decision.capability!r}. "
                        "Please correct the direction or capability selection."
                    )
                    self.harness.save_state(state)
                    return state
                await self.harness.execute_capability(
                    state=state,
                    capability=capability,
                    instruction=decision.instruction or "",
                    decision_summary=decision.summary,
                )
                continue

            if decision.kind is DecisionKind.ASK_HUMAN:
                state.status = RunStatus.WAITING_FOR_HUMAN
                state.pending_question = decision.instruction
                self.harness.save_state(state)
                return state

            if decision.kind is DecisionKind.PAUSE:
                state.status = RunStatus.PAUSED
                state.final_summary = decision.summary or None
                self.harness.save_state(state)
                return state

            if decision.kind is DecisionKind.FINISH:
                state.status = RunStatus.PARTIALLY_COMPLETE if state.failed_steps else RunStatus.COMPLETED
                state.final_summary = decision.summary or "Run finished."
                self.harness.save_state(state)
                return state

        state.status = RunStatus.PARTIALLY_COMPLETE
        state.final_summary = f"Stopped at the configured max_steps={self.max_steps}; completed evidence remains reusable."
        self.harness.save_state(state)
        return state
