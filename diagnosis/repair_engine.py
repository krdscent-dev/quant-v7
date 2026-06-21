"""Repair suggestion engine for V12.7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bias_detector import BiasFinding
from .v12_7_health_monitor import HealthAssessment


@dataclass(frozen=True)
class RepairSuggestion:
    """Ranked repair suggestion."""

    priority: int
    severity: str
    title: str
    action: str
    rationale: str
    expected_effect: str


class RepairEngine:
    """Generate non-destructive optimization suggestions."""

    def propose(
        self,
        health: HealthAssessment,
        biases: list[BiasFinding],
        backtest_result: dict[str, Any],
    ) -> list[RepairSuggestion]:
        suggestions: list[RepairSuggestion] = []

        if health.status == "CRITICAL":
            suggestions.append(
                RepairSuggestion(
                    priority=1,
                    severity="HIGH",
                    title="Reduce exposure and pause new expansion",
                    action="Tighten portfolio ceiling and favor HOLD/OBSERVE until drawdown normalizes.",
                    rationale="Health score is critical and drawdown risk is elevated.",
                    expected_effect="Lower drawdown and reduce forced rotation pressure.",
                )
            )
        elif health.status == "WARNING":
            suggestions.append(
                RepairSuggestion(
                    priority=2,
                    severity="MEDIUM",
                    title="Rebalance toward stronger confirmations",
                    action="Increase weight for high-confidence, high-confirmation signals only.",
                    rationale="Health is acceptable but needs tighter quality control.",
                    expected_effect="Improve hit rate and reduce weak signal exposure.",
                )
            )

        for bias in biases:
            if bias.bias_name == "risk_overweight":
                suggestions.append(
                    RepairSuggestion(
                        priority=1 if bias.severity == "HIGH" else 2,
                        severity=bias.severity,
                        title="Moderate risk-agent dominance",
                        action="Cap risk-agent influence and rebalance toward alpha validation.",
                        rationale=bias.message,
                        expected_effect="Restore balance between defense and opportunity capture.",
                    )
                )
            elif bias.bias_name == "alpha_underperformance":
                suggestions.append(
                    RepairSuggestion(
                        priority=2,
                        severity=bias.severity,
                        title="Restore alpha research focus",
                        action="Review alpha filters and widen opportunity discovery in strong themes.",
                        rationale=bias.message,
                        expected_effect="Reduce false negatives in emerging themes.",
                    )
                )
            elif bias.bias_name == "defensive_action_bias":
                suggestions.append(
                    RepairSuggestion(
                        priority=3,
                        severity=bias.severity,
                        title="Reduce over-defensive posture",
                        action="Allow limited SMALL_ADD / HOLD in strong sector leadership setups.",
                        rationale=bias.message,
                        expected_effect="Prevent the system from freezing in neutral market states.",
                    )
                )
            elif bias.bias_name == "confidence_calibration_bias":
                suggestions.append(
                    RepairSuggestion(
                        priority=3,
                        severity=bias.severity,
                        title="Recalibrate confidence scoring",
                        action="Recheck confidence thresholds against recent win/loss outcomes.",
                        rationale=bias.message,
                        expected_effect="Improve decision calibration and reduce bias drift.",
                    )
                )

        if not suggestions:
            suggestions.append(
                RepairSuggestion(
                    priority=9,
                    severity="LOW",
                    title="Maintain current configuration",
                    action="No structural repair needed; continue monitoring.",
                    rationale="No high-severity issues detected.",
                    expected_effect="Stable continuation with minimal intervention.",
                )
            )
        return sorted(suggestions, key=lambda item: (item.priority, item.title))

