"""Stress detection for V12.9."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class StressReport:
    """Stress state derived from system and market inputs."""

    state: str
    severity: str
    stress_score: float
    warnings: list[str]


class StressGuard:
    """Detect extreme market conditions and system stress."""

    def assess(
        self,
        backtest_result: Mapping[str, Any],
        health_report: Mapping[str, Any],
        stability_report: Mapping[str, Any],
        market_state: Mapping[str, Any] | None = None,
    ) -> StressReport:
        market_state = dict(market_state or {})
        total_return = float(backtest_result.get("total_return", 0.0) or 0.0)
        max_drawdown = float(backtest_result.get("max_drawdown", 0.0) or 0.0)
        win_rate = float(backtest_result.get("win_rate", 0.0) or 0.0)
        health_score = float(health_report.get("score", 0.0) or 0.0)
        health_status = str(health_report.get("status", "WARNING"))
        stability_status = str(stability_report.get("status", "WARNING"))
        drift_score = float(stability_report.get("drift_score", 0.0) or 0.0)
        latency_status = str(market_state.get("latency_status", "LOW_LATENCY"))
        regime = str(market_state.get("regime", "UNKNOWN"))

        stress_score = (
            0.30 * max_drawdown
            + 0.20 * max(0.0, 0.5 - win_rate)
            + 0.20 * (1.0 - health_score)
            + 0.15 * drift_score
            + 0.15 * (0.20 if latency_status == "HIGH_LATENCY" else 0.08 if latency_status == "MEDIUM_LATENCY" else 0.0)
        )
        if regime == "BEAR":
            stress_score += 0.08
        if total_return < 0:
            stress_score += min(0.10, abs(total_return))
        stress_score = max(0.0, min(1.0, stress_score))

        warnings: list[str] = []
        if max_drawdown >= 0.15:
            warnings.append("drawdown_stress")
        if health_status == "CRITICAL":
            warnings.append("health_critical")
        if stability_status == "UNSTABLE":
            warnings.append("system_instability")
        if latency_status == "HIGH_LATENCY":
            warnings.append("data_latency_high")

        if stress_score >= 0.70 or "health_critical" in warnings or "system_instability" in warnings:
            state = "EXTREME"
            severity = "HIGH"
        elif stress_score >= 0.45:
            state = "ELEVATED"
            severity = "MEDIUM"
        else:
            state = "NORMAL"
            severity = "LOW"

        return StressReport(
            state=state,
            severity=severity,
            stress_score=round(stress_score, 4),
            warnings=warnings,
        )

