"""Factor confidence contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConfidenceBreakdown:
    validation_weight: float
    provider_weight: float
    completeness_weight: float
    stability_weight: float
    validation_score: float
    provider_score: float
    completeness_score: float
    stability_score: float
    final_score: float


@dataclass(frozen=True)
class FactorConfidence:
    symbol: str
    period: str
    factor_name: str
    validation_confidence: float
    provider_confidence: float
    completeness_confidence: float
    stability_confidence: float
    final_confidence: float
    warnings: list[str] = field(default_factory=list)
    confidence_breakdown: ConfidenceBreakdown | None = None

