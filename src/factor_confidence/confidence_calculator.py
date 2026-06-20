"""Factor confidence calculator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .confidence_contract import ConfidenceBreakdown, FactorConfidence


class ConfidenceCalculator:
    """Calculate unified factor confidence."""

    VALIDATION_MAP = {
        "PASS": 1.00,
        "MINOR_DIFF": 0.85,
        "MISSING": 0.60,
        "MAJOR_DIFF": 0.35,
        "INVALID": 0.00,
    }

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def validation_score(self, validation_status: str) -> float:
        return self.VALIDATION_MAP.get(str(validation_status).upper(), 0.0)

    def provider_score(self, provider_trust_score: float) -> float:
        return self._clamp(float(provider_trust_score))

    def completeness_score(self, completeness_ratio: float) -> float:
        return self._clamp(float(completeness_ratio))

    def stability_score(self, stability_ratio: float) -> float:
        return self._clamp(float(stability_ratio))

    def calculate_final_confidence(
        self,
        validation_confidence: float,
        provider_confidence: float,
        completeness_confidence: float,
        stability_confidence: float,
    ) -> float:
        return self._clamp(
            validation_confidence * 0.40
            + provider_confidence * 0.30
            + completeness_confidence * 0.20
            + stability_confidence * 0.10
        )

    def calculate_factor_confidence(
        self,
        *,
        symbol: str,
        period: str,
        factor_name: str,
        validation_status: str,
        provider_trust_score: float,
        completeness_ratio: float,
        stability_ratio: float,
        warnings: list[str] | None = None,
    ) -> FactorConfidence:
        validation_confidence = self.validation_score(validation_status)
        provider_confidence = self.provider_score(provider_trust_score)
        completeness_confidence = self.completeness_score(completeness_ratio)
        stability_confidence = self.stability_score(stability_ratio)
        final_confidence = self.calculate_final_confidence(
            validation_confidence,
            provider_confidence,
            completeness_confidence,
            stability_confidence,
        )
        breakdown = ConfidenceBreakdown(
            validation_weight=0.40,
            provider_weight=0.30,
            completeness_weight=0.20,
            stability_weight=0.10,
            validation_score=round(validation_confidence, 2),
            provider_score=round(provider_confidence, 2),
            completeness_score=round(completeness_confidence, 2),
            stability_score=round(stability_confidence, 2),
            final_score=round(final_confidence, 2),
        )
        return FactorConfidence(
            symbol=symbol,
            period=period,
            factor_name=factor_name,
            validation_confidence=round(validation_confidence, 2),
            provider_confidence=round(provider_confidence, 2),
            completeness_confidence=round(completeness_confidence, 2),
            stability_confidence=round(stability_confidence, 2),
            final_confidence=round(final_confidence, 2),
            warnings=list(warnings or []),
            confidence_breakdown=breakdown,
        )

