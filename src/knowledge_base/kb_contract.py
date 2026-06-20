"""Knowledge base contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ResearchRecord:
    record_id: str
    symbol: str
    period: str
    strategic_score: float
    final_decision: str
    confidence_score: float
    evidence_refs: Mapping[str, Any] = field(default_factory=dict)
    explanation_summary: str = ""
    portfolio_bucket: str = ""
    recommended_weight: float = 0.0
    risk_level: str = ""
    rebalance_action: str = ""
    backtest_metrics: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class ResearchKnowledgeBase:
    records: list[ResearchRecord] = field(default_factory=list)
    index_by_symbol: dict[str, list[str]] = field(default_factory=dict)
    index_by_period: dict[str, list[str]] = field(default_factory=dict)
    version: int = 0

