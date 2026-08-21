"""Expose PyRIT attack techniques as independently meaningful Agent capabilities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Iterable

from .models import CapabilityDescriptor, CapabilityResult

if TYPE_CHECKING:
    from pyrit.prompt_target import PromptTarget
    from pyrit.scenario.core.attack_technique_factory import AttackTechniqueFactory
    from pyrit.score import TrueFalseScorer


class PyRITTechniqueCapability:
    """Thin semantic boundary around one registered PyRIT AttackTechniqueFactory."""

    def __init__(
        self,
        *,
        factory: "AttackTechniqueFactory",
        objective_target: "PromptTarget",
        objective_scorer: "TrueFalseScorer | None" = None,
        adversarial_chat: "PromptTarget | None" = None,
        max_concurrency: int = 1,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        self.factory = factory
        self.objective_target = objective_target
        self.objective_scorer = objective_scorer
        self.adversarial_chat = adversarial_chat
        self.max_concurrency = max_concurrency

    @property
    def descriptor(self) -> CapabilityDescriptor:
        description = self.factory.description or f"PyRIT technique using {self.factory.attack_class.__name__}."
        return CapabilityDescriptor(
            name=self.factory.name,
            description=description,
            tags=list(self.factory.technique_tags),
        )

    async def execute(self, *, instruction: str) -> CapabilityResult:
        from pyrit.executor.attack import AttackExecutor, AttackScoringConfig
        from pyrit.models import AttackSeedGroup, SeedObjective
        from pyrit.scenario import AtomicAttack

        objective = instruction.strip()
        if not objective:
            raise ValueError("PyRIT technique objective must not be empty")

        runtime_adversarial = self.adversarial_chat or self.factory.resolve_adversarial_chat()
        create_kwargs: dict[str, object] = {}
        # A caller-supplied adversarial target fills only the factory's lazy slot.
        if self.adversarial_chat is not None and self.factory.adversarial_chat is None:
            create_kwargs["adversarial_chat"] = self.adversarial_chat

        technique = self.factory.create(
            objective_target=self.objective_target,
            attack_scoring_config=AttackScoringConfig(objective_scorer=self.objective_scorer),
            **create_kwargs,
        )
        seed_group = AttackSeedGroup(seeds=[SeedObjective(value=objective)])
        atomic_attack = AtomicAttack(
            atomic_attack_name=f"agent_{self.factory.name}_{uuid.uuid4().hex[:10]}",
            attack_technique=technique,
            seed_groups=[seed_group],
            adversarial_chat=runtime_adversarial,
            objective_scorer=self.objective_scorer,
        )
        results = await atomic_attack.run_async(
            executor=AttackExecutor(max_concurrency=self.max_concurrency),
            return_partial_on_failure=True,
        )

        completed = [self._attack_result_view(result) for result in results.completed_results]
        incomplete = [
            {"objective": failed_objective, "exception_type": type(exc).__name__, "message": str(exc)}
            for failed_objective, exc in results.incomplete_objectives
        ]
        if incomplete:
            summary = (
                f"{self.factory.name}: {len(completed)} execution(s) completed; "
                f"{len(incomplete)} incomplete. Raw evidence was retained."
            )
        elif completed:
            outcome = completed[0].get("outcome", "unknown")
            reason = completed[0].get("outcome_reason") or "no outcome reason"
            summary = f"{self.factory.name}: execution completed with outcome={outcome}; {reason}"
        else:
            summary = f"{self.factory.name}: execution returned no completed result."

        return CapabilityResult(
            success=not incomplete and bool(completed),
            summary=summary,
            raw={"completed": completed, "incomplete": incomplete},
        )

    @staticmethod
    def _attack_result_view(result: object) -> dict[str, object]:
        outcome = getattr(result, "outcome", None)
        return {
            "objective": getattr(result, "objective", None),
            "outcome": getattr(outcome, "value", outcome),
            "outcome_reason": getattr(result, "outcome_reason", None),
            "conversation_id": getattr(result, "conversation_id", None),
            "execution_time_ms": getattr(result, "execution_time_ms", None),
            "total_retries": getattr(result, "total_retries", None),
            "targeted_harm_categories": getattr(result, "targeted_harm_categories", None),
        }


def build_registry_capabilities(
    *,
    objective_target: "PromptTarget",
    objective_scorer: "TrueFalseScorer | None" = None,
    adversarial_chat: "PromptTarget | None" = None,
    include_names: Iterable[str] | None = None,
    include_tags: Iterable[str] | None = None,
    exclude_names: Iterable[str] | None = None,
    max_concurrency: int = 1,
) -> list[PyRITTechniqueCapability]:
    """Build Agent capabilities from the populated PyRIT AttackTechniqueRegistry."""
    from pyrit.registry import AttackTechniqueRegistry

    factories = AttackTechniqueRegistry.get_registry_singleton().get_factories_or_raise()
    wanted_names = set(include_names or [])
    wanted_tags = set(include_tags or [])
    excluded = set(exclude_names or [])

    selected = []
    for name, factory in factories.items():
        if name in excluded:
            continue
        if wanted_names and name not in wanted_names:
            continue
        if wanted_tags and not (set(factory.technique_tags) & wanted_tags):
            continue
        selected.append(
            PyRITTechniqueCapability(
                factory=factory,
                objective_target=objective_target,
                objective_scorer=objective_scorer,
                adversarial_chat=adversarial_chat,
                max_concurrency=max_concurrency,
            )
        )
    if not selected:
        raise ValueError("No PyRIT techniques matched the requested capability filters")
    return selected
