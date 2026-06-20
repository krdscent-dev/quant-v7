"""Position sizing engine."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .position_contract import PositionRecommendation, PositionSnapshot
from .position_explainer import PositionExplainer
from .sizing_rules import SizingRules


class PositionSizingEngine:
    def __init__(self) -> None:
        self.rules = SizingRules()
        self.explainer = PositionExplainer()

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _bucket(self, candidate: Mapping[str, Any]) -> str:
        return str(candidate.get("bucket", "WATCHLIST")).upper()

    def _confidence(self, candidate: Mapping[str, Any]) -> float:
        return self._clamp(float(candidate.get("confidence_score", 0.0)))

    def _risk(self, candidate: Mapping[str, Any]) -> float:
        return self._clamp(float(candidate.get("risk_score", 0.0)))

    def recommend(self, candidate: Mapping[str, Any]) -> PositionRecommendation:
        bucket = self._bucket(candidate)
        confidence_score = self._confidence(candidate)
        risk_score = self._risk(candidate)
        strategic_score = float(candidate.get("strategic_score", 0.0))
        base_weight = self.rules.base_weight(bucket)
        recommended_weight = self.rules.recommended_weight(bucket, confidence_score, risk_score)
        max_weight = self.rules.max_weight(bucket)
        min_weight = self.rules.min_weight(bucket)
        if recommended_weight > max_weight:
            recommended_weight = max_weight
        if 0.0 < recommended_weight < min_weight:
            recommended_weight = min_weight
        warnings: list[str] = []
        if confidence_score < 0.60 and recommended_weight > 0:
            warnings.append("confidence_low")
        if risk_score >= 0.70 and recommended_weight > 0:
            warnings.append("risk_high")
        if bucket in {"WATCHLIST", "EXCLUDED"}:
            recommended_weight = 0.0
        sizing_reason = self.explainer.explain(
            str(candidate.get("symbol", "UNKNOWN")),
            bucket,
            recommended_weight,
            strategic_score,
            confidence_score,
            risk_score,
        )
        return PositionRecommendation(
            symbol=str(candidate.get("symbol", "UNKNOWN")),
            bucket=bucket,
            strategic_score=round(strategic_score, 2),
            confidence_score=round(confidence_score, 2),
            risk_score=round(risk_score, 2),
            recommended_weight=round(recommended_weight, 4),
            max_weight=max_weight,
            min_weight=min_weight,
            sizing_reason=sizing_reason,
            warnings=warnings,
            evidence_refs=dict(candidate.get("evidence_refs", {})),
        )

    def build_snapshot(self, candidates: list[Mapping[str, Any]], period: str = "TTM") -> PositionSnapshot:
        recommendations = [self.recommend(candidate) for candidate in candidates]
        total_allocated = round(sum(item.recommended_weight for item in recommendations), 4)
        remaining_cash = round(max(0.0, 1.0 - total_allocated), 4)
        warnings = [warn for item in recommendations for warn in item.warnings]
        allocation_summary = (
            f"Core Allocation: {round(sum(item.recommended_weight for item in recommendations if item.bucket == 'CORE') * 100, 2)}% "
            f"Satellite Allocation: {round(sum(item.recommended_weight for item in recommendations if item.bucket == 'SATELLITE') * 100, 2)}% "
            f"Cash: {round(remaining_cash * 100, 2)}%"
        )
        return PositionSnapshot(
            period=period,
            recommendations=recommendations,
            total_allocated=total_allocated,
            remaining_cash=remaining_cash,
            warnings=warnings,
            allocation_summary=allocation_summary,
        )

    def snapshot_to_dict(self, snapshot: PositionSnapshot) -> dict[str, Any]:
        return {
            "period": snapshot.period,
            "recommendations": [asdict(item) for item in snapshot.recommendations],
            "total_allocated": snapshot.total_allocated,
            "remaining_cash": snapshot.remaining_cash,
            "warnings": list(snapshot.warnings),
            "allocation_summary": snapshot.allocation_summary,
        }

