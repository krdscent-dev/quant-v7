"""Risk explanation helpers."""

from __future__ import annotations

from typing import Any

from .risk_contract import PortfolioRiskReport


class RiskExplainer:
    def explain(self, report: PortfolioRiskReport, portfolio_snapshot: dict[str, Any], position_snapshot: dict[str, Any]) -> list[str]:
        messages = list(report.warnings)
        for check in report.checks:
            if not check.passed:
                messages.append(check.message)
        return messages

