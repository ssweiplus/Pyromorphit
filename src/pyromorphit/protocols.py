"""Ports between semantic planning and deterministic execution."""

from __future__ import annotations

from typing import Protocol

from .models import AgentDecision, CapabilityDescriptor, CapabilityResult, RunState


class Planner(Protocol):
    """Owns semantic interpretation and composition."""

    async def decide(self, *, state: RunState, capabilities: list[CapabilityDescriptor]) -> AgentDecision:
        """Choose the next semantic action from current evidence."""


class Capability(Protocol):
    """Independently meaningful deterministic/executable capability."""

    @property
    def descriptor(self) -> CapabilityDescriptor:
        """Describe the capability to the planner."""

    async def execute(self, *, instruction: str) -> CapabilityResult:
        """Execute one bounded instruction and return normalized evidence."""
