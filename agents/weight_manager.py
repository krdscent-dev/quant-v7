"""Adaptive agent weight manager for V11.2."""

from __future__ import annotations

from typing import Mapping

from agents.agent_performance_tracker import AgentPerformance


DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "RiskAgent": 0.40,
    "AlphaAgent": 0.30,
    "MacroAgent": 0.15,
    "SectorAgent": 0.10,
    "PortfolioAgent": 0.05,
}


class AgentWeightManager:
    """Update agent importance from historical performance."""

    MIN_WEIGHT = 0.05
    MAX_WEIGHT = 0.55
    STEP = 0.03

    def update_weights(
        self,
        performance_summary: Mapping[str, AgentPerformance],
        current_weights: Mapping[str, float] | None = None,
    ) -> dict[str, float]:
        weights = dict(current_weights or DEFAULT_AGENT_WEIGHTS)
        for agent, performance in performance_summary.items():
            if agent not in weights:
                continue
            adjusted = float(weights[agent])
            if performance.accuracy > 0.60 or performance.pnl_contribution > 0.0:
                adjusted += self.STEP
            if performance.accuracy < 0.45 or performance.pnl_contribution < 0.0:
                adjusted -= self.STEP
            weights[agent] = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, adjusted))
        return self._normalize(weights)

    def _normalize(self, weights: Mapping[str, float]) -> dict[str, float]:
        total = sum(float(value) for value in weights.values())
        if total <= 0:
            return dict(DEFAULT_AGENT_WEIGHTS)
        normalized = {
            agent: max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, float(value) / total))
            for agent, value in weights.items()
        }
        normalized_total = sum(normalized.values())
        return {
            agent: round(value / normalized_total, 4)
            for agent, value in normalized.items()
        }
