"""Position contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class PositionRecommendation:
    symbol: str
    bucket: str
    strategic_score: float
    confidence_score: float
    risk_score: float
    recommended_weight: float
    max_weight: float
    min_weight: float
    sizing_reason: str
    warnings: list[str] = field(default_factory=list)
    evidence_refs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PositionSnapshot:
    period: str
    recommendations: list[PositionRecommendation]
    total_allocated: float
    remaining_cash: float
    warnings: list[str] = field(default_factory=list)
    allocation_summary: str = ""

