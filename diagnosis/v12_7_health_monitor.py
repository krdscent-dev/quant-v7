"""System health monitoring for V12.7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HealthAssessment:
    """Snapshot of system health."""

    status: str
    severity: str
    drawdown_risk: str
    accuracy_risk: str
    risk_level: str
    score: float
    warnings: list[str]


class HealthMonitor:
    """Assess system health from backtest and performance signals."""

    def assess(
        self,
        backtest_result: Mapping[str, Any],
        trade_logs: list[Mapping[str, Any]],
        performance_metrics: Mapping[str, Any] | None = None,
    ) -> HealthAssessment:
        performance_metrics = dict(performance_metrics or {})
        total_return = float(backtest_result.get("total_return", 0.0) or 0.0)
        max_drawdown = float(backtest_result.get("max_drawdown", 0.0) or 0.0)
        win_rate = float(backtest_result.get("win_rate", 0.0) or 0.0)
        trade_count = len(trade_logs)
        positive_trades = sum(1 for trade in trade_logs if float(trade.get("pnl", 0.0) or 0.0) > 0)
        realized_win_rate = positive_trades / trade_count if trade_count else 0.0
        agent_accuracy = float(performance_metrics.get("agent_accuracy", realized_win_rate) or realized_win_rate)
        risk_events = int(performance_metrics.get("risk_events", 0) or 0)
        volatility = float(performance_metrics.get("volatility", 0.0) or 0.0)

        score = 0.35 + total_return * 6.0 - max_drawdown * 3.0 + win_rate * 0.25 + agent_accuracy * 0.2
        score -= min(0.35, risk_events * 0.04 + volatility * 0.12)
        score = max(0.0, min(1.0, score))

        if score >= 0.75 and max_drawdown < 0.08:
            status = "HEALTHY"
            severity = "LOW"
        elif score >= 0.55 and max_drawdown < 0.15:
            status = "WARNING"
            severity = "MEDIUM"
        else:
            status = "CRITICAL"
            severity = "HIGH"

        drawdown_risk = "ELEVATED" if max_drawdown >= 0.10 else "MANAGEABLE"
        accuracy_risk = "ELEVATED" if agent_accuracy < 0.55 else "MANAGEABLE"
        risk_level = "HIGH" if max_drawdown >= 0.15 or risk_events >= 3 else "MEDIUM" if max_drawdown >= 0.08 else "LOW"

        warnings: list[str] = []
        if max_drawdown >= 0.10:
            warnings.append("max_drawdown_above_10pct")
        if agent_accuracy < 0.55:
            warnings.append("agent_accuracy_below_55pct")
        if risk_events:
            warnings.append("risk_events_detected")
        if win_rate < 0.5:
            warnings.append("win_rate_below_50pct")

        return HealthAssessment(
            status=status,
            severity=severity,
            drawdown_risk=drawdown_risk,
            accuracy_risk=accuracy_risk,
            risk_level=risk_level,
            score=round(score, 4),
            warnings=warnings,
        )

