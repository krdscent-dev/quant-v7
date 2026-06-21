"""Detect sector capital rotation from sector-strength signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CapitalFlowSignal:
    sector: str
    flow_score: float
    rank: int
    direction: str


class CapitalFlowEngine:
    """Rank sectors by relative capital-flow proxy."""

    def rank_flows(self, sector_scores: Mapping[str, float]) -> list[CapitalFlowSignal]:
        ranked = sorted(
            ((str(sector), float(score or 0.0)) for sector, score in sector_scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        rows: list[CapitalFlowSignal] = []
        for index, (sector, score) in enumerate(ranked, start=1):
            if score >= 0.75:
                direction = "INFLOW"
            elif score >= 0.50:
                direction = "ROTATION"
            else:
                direction = "OUTFLOW"
            rows.append(CapitalFlowSignal(sector, round(score, 4), index, direction))
        return rows

