"""Score explanation builder."""

from __future__ import annotations

from typing import Any, Mapping

from .contribution_analyzer import ContributionAnalyzer
from .explanation_contract import ScoreExplanation


class ScoreExplainer:
    """Build score explanations with positive and negative contributions."""

    def __init__(self) -> None:
        self.analyzer = ContributionAnalyzer()

    def explain(self, factor_dict: Mapping[str, Any], total_score: float, symbol: str, period: str) -> ScoreExplanation:
        contributions = self.analyzer.analyze(factor_dict)
        positives = contributions[:5]
        negatives = sorted(contributions, key=lambda item: item.contribution_score)[:5]
        confidence_score = float(factor_dict.get("confidence_score", 1.0))
        if confidence_score > 1.0:
            confidence_score /= 100.0
        summary = (
            f"{symbol} 在 {period} 周期内的总分为 {total_score:.2f}。"
            f" 主要正向因子为 {', '.join(item.factor_name for item in positives[:3])}。"
            f" 主要拖累因子为 {', '.join(item.factor_name for item in negatives[:3])}。"
        )
        return ScoreExplanation(
            symbol=symbol,
            period=period,
            total_score=round(float(total_score), 2),
            top_positive_factors=positives,
            top_negative_factors=negatives,
            confidence_score=round(confidence_score, 2),
            summary=summary,
        )
