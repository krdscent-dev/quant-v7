"""Track agent accuracy and PnL contribution for V11.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AgentPerformance:
    agent_name: str
    accuracy: float
    pnl_contribution: float
    sample_count: int


class AgentPerformanceTracker:
    """Summarize historical agent performance logs."""

    DEFAULT_AGENTS = ("RiskAgent", "AlphaAgent", "MacroAgent", "SectorAgent", "PortfolioAgent")

    def summarize(self, performance_log: Iterable[Mapping[str, object]] | None = None) -> dict[str, AgentPerformance]:
        records = list(performance_log or [])
        if not records:
            return {
                agent: AgentPerformance(agent, accuracy=0.50, pnl_contribution=0.0, sample_count=0)
                for agent in self.DEFAULT_AGENTS
            }

        grouped: dict[str, list[Mapping[str, object]]] = {agent: [] for agent in self.DEFAULT_AGENTS}
        for record in records:
            agent = str(record.get("agent_name", ""))
            if agent in grouped:
                grouped[agent].append(record)

        summary: dict[str, AgentPerformance] = {}
        for agent, items in grouped.items():
            if not items:
                summary[agent] = AgentPerformance(agent, accuracy=0.50, pnl_contribution=0.0, sample_count=0)
                continue
            wins = sum(1 for item in items if str(item.get("outcome", "")).upper() == "WIN")
            pnl = sum(float(item.get("pnl_contribution", 0.0) or 0.0) for item in items)
            summary[agent] = AgentPerformance(
                agent_name=agent,
                accuracy=round(wins / len(items), 4),
                pnl_contribution=round(pnl, 4),
                sample_count=len(items),
            )
        return summary
