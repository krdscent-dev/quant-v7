"""Registry for active V11.3 agents."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from agents.agent_factory import AgentDescriptor


DEFAULT_ACTIVE_AGENTS = (
    "MacroAgent",
    "SectorAgent",
    "AlphaAgent",
    "RiskAgent",
    "PortfolioAgent",
    "DecisionArbitrator",
    "AuditAgent",
)


class AgentRegistry:
    """Maintain active agent descriptors for the orchestrator."""

    def __init__(self, agents: Iterable[AgentDescriptor] | None = None) -> None:
        self._agents: dict[str, AgentDescriptor] = {}
        if agents is None:
            agents = [AgentDescriptor(agent, agent) for agent in DEFAULT_ACTIVE_AGENTS]
        for agent in agents:
            self.register(agent)

    def register(self, agent: AgentDescriptor) -> None:
        self._agents[agent.agent_name] = agent

    def remove(self, agent_name: str) -> None:
        self._agents.pop(agent_name, None)

    def has_agent(self, agent_name: str) -> bool:
        return agent_name in self._agents

    def active_agent_names(self) -> list[str]:
        return sorted(self._agents)

    def as_records(self) -> list[dict[str, object]]:
        return [asdict(item) for item in self._agents.values()]
