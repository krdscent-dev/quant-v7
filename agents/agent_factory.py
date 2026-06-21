"""Factory for dynamic V11.3 agent creation.

The factory creates lightweight agent descriptors only. It does not instantiate
new trading logic at runtime, which keeps V11.3 compatible with the existing
agent workflow while making structural evolution auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentDescriptor:
    """Metadata for an active or candidate agent."""

    agent_name: str
    agent_type: str
    status: str = "ACTIVE"
    parent_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentFactory:
    """Create optional specialist agents from promoted base agents."""

    PROMOTION_VARIANTS = {
        "AlphaAgent": "MomentumAgent",
        "SectorAgent": "NewsAgent",
        "RiskAgent": "LiquidityAgent",
        "MacroAgent": "SentimentAgent",
    }

    def create(self, agent_type: str, parent_agent: str | None = None) -> AgentDescriptor:
        return AgentDescriptor(
            agent_name=agent_type,
            agent_type=agent_type,
            parent_agent=parent_agent,
            metadata={
                "created_by": "AgentFactory",
                "creation_reason": "Lifecycle promotion" if parent_agent else "Manual registry seed",
            },
        )

    def create_variant_for(self, parent_agent: str) -> AgentDescriptor | None:
        variant_type = self.PROMOTION_VARIANTS.get(parent_agent)
        if not variant_type:
            return None
        return self.create(variant_type, parent_agent=parent_agent)
