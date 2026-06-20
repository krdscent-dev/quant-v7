"""Provider trust score calculator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .trust_contract import ProviderTrustScore


class TrustCalculator:
    """Calculate provider trust metrics."""

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def calculate_coverage_score(self, total_fields: int, missing_fields: int) -> float:
        if total_fields <= 0:
            return 0.0
        return self._clamp((total_fields - missing_fields) / total_fields)

    def calculate_consistency_score(self, agreement_ratio: float) -> float:
        return self._clamp(float(agreement_ratio))

    def calculate_freshness_score(self, days_since_update: int) -> float:
        if days_since_update <= 1:
            return 1.0
        if days_since_update <= 3:
            return 0.95
        if days_since_update <= 7:
            return 0.90
        if days_since_update <= 30:
            return 0.80
        return 0.50

    def calculate_stability_score(self, success_count: int, total_count: int) -> float:
        if total_count <= 0:
            return 0.0
        return self._clamp(success_count / total_count)

    def calculate_anomaly_score(self, anomaly_count: int, total_count: int) -> float:
        if total_count <= 0:
            return 0.0
        return self._clamp(1.0 - (anomaly_count / total_count))

    def calculate_overall_score(self, *, coverage_score: float, consistency_score: float, freshness_score: float, stability_score: float, anomaly_score: float) -> float:
        return self._clamp(
            0.25 * coverage_score
            + 0.30 * consistency_score
            + 0.20 * freshness_score
            + 0.15 * stability_score
            + 0.10 * anomaly_score
        )

    def calculate_provider_trust(
        self,
        provider_name: str,
        *,
        total_fields: int,
        missing_fields: int,
        agreement_ratio: float,
        days_since_update: int,
        success_count: int,
        total_count: int,
        anomaly_count: int,
        warning_count: int = 0,
        last_updated: str | None = None,
    ) -> ProviderTrustScore:
        coverage_score = self.calculate_coverage_score(total_fields, missing_fields)
        consistency_score = self.calculate_consistency_score(agreement_ratio)
        freshness_score = self.calculate_freshness_score(days_since_update)
        stability_score = self.calculate_stability_score(success_count, total_count)
        anomaly_score = self.calculate_anomaly_score(anomaly_count, total_count)
        overall_score = self.calculate_overall_score(
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            freshness_score=freshness_score,
            stability_score=stability_score,
            anomaly_score=anomaly_score,
        )
        return ProviderTrustScore(
            provider_name=provider_name,
            overall_score=round(overall_score, 2),
            coverage_score=round(coverage_score, 2),
            consistency_score=round(consistency_score, 2),
            freshness_score=round(freshness_score, 2),
            stability_score=round(stability_score, 2),
            anomaly_score=round(anomaly_score, 2),
            warning_count=warning_count,
            last_updated=last_updated or datetime.now(timezone.utc).isoformat(),
        )

