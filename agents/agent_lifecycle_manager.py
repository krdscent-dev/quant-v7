"""Lifecycle manager for V11.3 dynamic agent evolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from agents.agent_factory import AgentDescriptor, AgentFactory
from agents.agent_performance_tracker import AgentPerformance
from agents.agent_registry import AgentRegistry


@dataclass(frozen=True)
class AgentLifecycleDecision:
    agent_name: str
    performance_score: float
    action: str
    reason: str


@dataclass(frozen=True)
class AgentLifecycleResult:
    active_agents: list[str]
    removed_agents: list[str]
    newly_created_agents: list[str]
    promoted_agents: list[str]
    performance_scores: dict[str, float]
    lifecycle_decisions: list[AgentLifecycleDecision] = field(default_factory=list)
    structural_changes: list[str] = field(default_factory=list)


class AgentLifecycleManager:
    """Evaluate agent performance and mutate registry metadata safely."""

    def __init__(self, registry: AgentRegistry | None = None, factory: AgentFactory | None = None) -> None:
        self.registry = registry or AgentRegistry()
        self.factory = factory or AgentFactory()

    def evaluate(
        self,
        performance_summary: Mapping[str, AgentPerformance],
        weights: Mapping[str, float] | None = None,
    ) -> AgentLifecycleResult:
        removed: list[str] = []
        created: list[str] = []
        promoted: list[str] = []
        structural_changes: list[str] = []
        lifecycle_decisions: list[AgentLifecycleDecision] = []
        scores: dict[str, float] = {}

        for agent_name, performance in performance_summary.items():
            weight = float((weights or {}).get(agent_name, 0.0) or 0.0)
            score = self._performance_score(performance, weight)
            scores[agent_name] = score

            if score < 0.40:
                lifecycle_decisions.append(
                    AgentLifecycleDecision(agent_name, score, "REMOVE", "Performance score below 0.40.")
                )
                self.registry.remove(agent_name)
                removed.append(agent_name)
                structural_changes.append(f"REMOVE {agent_name}: performance={score:.2f}")
                continue

            if score > 0.80:
                lifecycle_decisions.append(
                    AgentLifecycleDecision(agent_name, score, "PROMOTE", "Performance score above 0.80.")
                )
                promoted.append(agent_name)
                variant = self.factory.create_variant_for(agent_name)
                if variant and not self.registry.has_agent(variant.agent_name):
                    self.registry.register(variant)
                    created.append(variant.agent_name)
                    structural_changes.append(
                        f"PROMOTE {agent_name}: spawned {variant.agent_name}, performance={score:.2f}"
                    )
                else:
                    structural_changes.append(f"PROMOTE {agent_name}: weight bias only, performance={score:.2f}")
                continue

            lifecycle_decisions.append(
                AgentLifecycleDecision(agent_name, score, "KEEP", "Performance score remains in stable range.")
            )

        return AgentLifecycleResult(
            active_agents=self.registry.active_agent_names(),
            removed_agents=removed,
            newly_created_agents=created,
            promoted_agents=promoted,
            performance_scores=scores,
            lifecycle_decisions=lifecycle_decisions,
            structural_changes=structural_changes,
        )

    @staticmethod
    def _performance_score(performance: AgentPerformance, weight: float) -> float:
        pnl_component = max(0.0, min(1.0, 0.50 + performance.pnl_contribution))
        sample_adjustment = min(performance.sample_count, 20) / 100.0
        score = 0.70 * performance.accuracy + 0.20 * pnl_component + 0.10 * min(weight * 2.0, 1.0)
        score += sample_adjustment
        return round(max(0.0, min(1.0, score)), 4)
