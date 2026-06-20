"""Explainability contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class FactorContribution:
    factor_name: str
    factor_score: float
    factor_weight: float
    confidence_score: float
    contribution_score: float
    contribution_pct: float


@dataclass(frozen=True)
class ScoreExplanation:
    symbol: str
    period: str
    total_score: float
    top_positive_factors: list[FactorContribution] = field(default_factory=list)
    top_negative_factors: list[FactorContribution] = field(default_factory=list)
    confidence_score: float = 0.0
    summary: str = ""


@dataclass(frozen=True)
class DecisionExplanation:
    symbol: str
    period: str
    final_decision: str
    decision_reasons: list[str] = field(default_factory=list)
    supporting_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    summary: str = ""

