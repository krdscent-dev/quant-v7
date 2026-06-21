"""Portfolio weight allocation from alpha rankings."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable

from portfolio.alpha_ranker import RankedSymbol
from portfolio.multi_symbol_data_engine import _clamp


@dataclass(frozen=True)
class PortfolioWeight:
    symbol: str
    alpha_score: float
    rank: int
    weight: float
    base_weight: float
    concentration_factor: float
    data_source: str
    data_status: str


class PortfolioAllocator:
    """Translate ranked alpha scores into normalized portfolio weights."""

    def allocate(self, ranked_symbols: Iterable[RankedSymbol]) -> list[PortfolioWeight]:
        items = list(ranked_symbols)
        if not items:
            return []

        concentration_factor = 1.15
        adjusted_scores = [exp(_clamp(item.alpha_score, 0.0, 100.0) / 30.0) for item in items]
        total = sum(adjusted_scores) or 1.0
        base_weights = [score / total for score in adjusted_scores]

        weights = [
            PortfolioWeight(
                symbol=item.symbol,
                alpha_score=item.alpha_score,
                rank=item.rank,
                weight=round(base_weight, 6),
                base_weight=round(base_weight, 6),
                concentration_factor=concentration_factor,
                data_source=item.data_source,
                data_status=item.data_status,
            )
            for item, base_weight in zip(items, base_weights, strict=False)
        ]

        normalized_total = sum(weight.weight for weight in weights) or 1.0
        if abs(normalized_total - 1.0) > 1e-9:
            weights = [
                PortfolioWeight(
                    symbol=weight.symbol,
                    alpha_score=weight.alpha_score,
                    rank=weight.rank,
                    weight=round(weight.weight / normalized_total, 6),
                    base_weight=weight.base_weight,
                    concentration_factor=weight.concentration_factor,
                    data_source=weight.data_source,
                    data_status=weight.data_status,
                )
                for weight in weights
            ]
        return weights

