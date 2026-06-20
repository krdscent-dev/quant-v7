"""Risk contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class RiskCheckResult:
    check_name: str
    passed: bool
    severity: str
    message: str
    affected_symbols: list[str] = field(default_factory=list)
    suggested_action: str = ""


@dataclass(frozen=True)
class PortfolioRiskReport:
    period: str
    total_risk_score: float
    risk_level: str
    checks: list[RiskCheckResult]
    warnings: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

