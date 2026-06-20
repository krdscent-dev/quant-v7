"""Portfolio contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class PortfolioCandidate:
    symbol: str
    period: str
    strategic_score: float
    final_decision: str
    confidence_score: float
    risk_score: float
    evidence_refs: Mapping[str, Any] = field(default_factory=dict)
    explanation: str = ""
    bucket: str = "WATCHLIST"


@dataclass(frozen=True)
class PortfolioScore:
    symbol: str
    total_score: float
    strategic_score: float
    confidence_score: float
    risk_adjusted_score: float
    rank: int
    bucket: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PortfolioSnapshot:
    period: str
    candidates: list[PortfolioCandidate]
    ranked_candidates: list[PortfolioScore]
    core_candidates: list[PortfolioScore]
    satellite_candidates: list[PortfolioScore]
    watchlist_candidates: list[PortfolioScore]
    excluded_candidates: list[PortfolioScore]
    summary: str
    warnings: list[str] = field(default_factory=list)
    portfolio_summary: str = ""

