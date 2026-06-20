"""Rank portfolio candidates."""

from __future__ import annotations

from .portfolio_contract import PortfolioScore


class PortfolioRanker:
    def rank(self, scores: list[PortfolioScore]) -> list[PortfolioScore]:
        ranked = sorted(scores, key=lambda item: item.total_score, reverse=True)
        return [
            PortfolioScore(
                symbol=item.symbol,
                total_score=item.total_score,
                strategic_score=item.strategic_score,
                confidence_score=item.confidence_score,
                risk_adjusted_score=item.risk_adjusted_score,
                rank=index,
                bucket=item.bucket,
                warnings=list(item.warnings),
            )
            for index, item in enumerate(ranked, start=1)
        ]

