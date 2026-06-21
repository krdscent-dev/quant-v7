"""Cross-sectional alpha ranking for multi-symbol V12 portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from portfolio.multi_symbol_data_engine import SymbolSnapshot, _clamp


@dataclass(frozen=True)
class RankedSymbol:
    symbol: str
    alpha_score: float
    raw_score: float
    cross_section_score: float
    rank: int
    total: int
    data_source: str
    data_status: str
    trend: float
    volatility: float
    momentum: float
    breadth: float
    liquidity: float
    close: float
    timestamp: str


class AlphaRanker:
    """Produce a cross-sectional ranking from symbol snapshots."""

    def score(self, snapshot: SymbolSnapshot) -> float:
        raw_score = (
            0.28 * snapshot.trend
            + 0.22 * snapshot.momentum
            + 0.18 * snapshot.breadth
            + 0.12 * snapshot.liquidity
            + 0.10 * snapshot.volume_pressure
            + 0.10 * (1.0 - snapshot.volatility)
        )
        return _clamp(raw_score * 100.0, 0.0, 100.0)

    def rank(self, snapshots: Iterable[SymbolSnapshot]) -> list[RankedSymbol]:
        items = list(snapshots)
        if not items:
            return []

        raw_scores = [self.score(snapshot) for snapshot in items]
        average_score = mean(raw_scores)
        score_min = min(raw_scores)
        score_max = max(raw_scores)
        score_span = max(score_max - score_min, 1e-9)

        ranked_pairs = sorted(zip(items, raw_scores), key=lambda pair: pair[1], reverse=True)
        total = len(ranked_pairs)
        ranked: list[RankedSymbol] = []
        for index, (snapshot, raw_score) in enumerate(ranked_pairs, start=1):
            cross_section_score = (raw_score - score_min) / score_span if score_span else 0.5
            blended_alpha = 0.65 * raw_score + 0.35 * (cross_section_score * 100.0)
            if raw_score >= average_score:
                blended_alpha += 2.5
            ranked.append(
                RankedSymbol(
                    symbol=snapshot.symbol,
                    alpha_score=round(_clamp(blended_alpha, 0.0, 100.0), 4),
                    raw_score=round(raw_score, 4),
                    cross_section_score=round(cross_section_score * 100.0, 4),
                    rank=index,
                    total=total,
                    data_source=snapshot.data_source,
                    data_status=snapshot.data_status,
                    trend=snapshot.trend,
                    volatility=snapshot.volatility,
                    momentum=snapshot.momentum,
                    breadth=snapshot.breadth,
                    liquidity=snapshot.liquidity,
                    close=snapshot.close,
                    timestamp=snapshot.timestamp,
                )
            )
        return ranked

