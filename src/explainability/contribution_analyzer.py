"""Contribution analysis for score explanations."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from strategy.strategic_score_engine import WEIGHTS

from .explanation_contract import FactorContribution


class ContributionAnalyzer:
    """Calculate factor contribution scores for strategic scoring."""

    def _confidence(self, factor_dict: Mapping[str, Any], factor_name: str) -> float:
        value = factor_dict.get(f"{factor_name}_confidence_score", factor_dict.get("confidence_score", 1.0))
        try:
            confidence = float(value)
        except Exception:
            confidence = 1.0
        if confidence > 1.0:
            confidence = confidence / 100.0
        return max(0.0, min(1.0, confidence))

    def _score(self, value: Any) -> float:
        try:
            score = float(value)
        except Exception:
            score = 0.0
        if 0.0 <= score <= 1.0:
            score *= 100.0
        return max(0.0, min(100.0, score))

    def analyze(self, factor_dict: Mapping[str, Any]) -> list[FactorContribution]:
        contributions: list[FactorContribution] = []
        for factor_name, factor_weight in WEIGHTS.items():
            factor_score = self._score(factor_dict.get(factor_name, 0.0))
            confidence_score = self._confidence(factor_dict, factor_name)
            contribution_score = factor_score * factor_weight * confidence_score
            contributions.append(
                FactorContribution(
                    factor_name=factor_name,
                    factor_score=round(factor_score, 2),
                    factor_weight=round(factor_weight, 4),
                    confidence_score=round(confidence_score, 2),
                    contribution_score=round(contribution_score, 2),
                    contribution_pct=0.0,
                )
            )

        total = sum(item.contribution_score for item in contributions) or 1.0
        normalized: list[FactorContribution] = []
        for item in contributions:
            normalized.append(
                FactorContribution(
                    factor_name=item.factor_name,
                    factor_score=item.factor_score,
                    factor_weight=item.factor_weight,
                    confidence_score=item.confidence_score,
                    contribution_score=item.contribution_score,
                    contribution_pct=round((item.contribution_score / total) * 100.0, 2),
                )
            )
        return sorted(normalized, key=lambda item: item.contribution_score, reverse=True)

    def to_dicts(self, contributions: list[FactorContribution]) -> list[dict[str, Any]]:
        return [asdict(item) for item in contributions]
