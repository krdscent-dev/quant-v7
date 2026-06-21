"""Structural bias detection for V12.7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class BiasFinding:
    """Detected system bias."""

    bias_name: str
    severity: str
    message: str
    evidence: dict[str, Any]


class BiasDetector:
    """Detect overweight / underperformance / concentration bias."""

    def detect(
        self,
        trade_logs: list[Mapping[str, Any]],
        agent_weights: Mapping[str, float] | None = None,
        performance_metrics: Mapping[str, Any] | None = None,
    ) -> list[BiasFinding]:
        agent_weights = dict(agent_weights or {})
        performance_metrics = dict(performance_metrics or {})
        findings: list[BiasFinding] = []

        if agent_weights:
            risk_weight = float(agent_weights.get("RiskAgent", 0.0) or 0.0)
            alpha_weight = float(agent_weights.get("AlphaAgent", 0.0) or 0.0)
            if risk_weight >= 0.35:
                findings.append(
                    BiasFinding(
                        bias_name="risk_overweight",
                        severity="HIGH" if risk_weight >= 0.40 else "MEDIUM",
                        message="Risk agent weight is elevated and may crowd out alpha generation.",
                        evidence={"risk_weight": round(risk_weight, 4)},
                    )
                )
            if alpha_weight <= 0.25:
                findings.append(
                    BiasFinding(
                        bias_name="alpha_underperformance",
                        severity="HIGH" if alpha_weight <= 0.20 else "MEDIUM",
                        message="Alpha agent weight is relatively weak versus risk control.",
                        evidence={"alpha_weight": round(alpha_weight, 4)},
                    )
                )

        actions = [str(trade.get("action", "OBSERVE")).upper() for trade in trade_logs]
        observe_ratio = actions.count("OBSERVE") / len(actions) if actions else 0.0
        hold_ratio = actions.count("HOLD") / len(actions) if actions else 0.0
        small_add_ratio = actions.count("SMALL_ADD") / len(actions) if actions else 0.0
        if observe_ratio >= 0.35 and small_add_ratio < 0.30:
            findings.append(
                BiasFinding(
                    bias_name="defensive_action_bias",
                    severity="MEDIUM",
                    message="System is leaning toward observation more often than active positioning.",
                    evidence={
                        "observe_ratio": round(observe_ratio, 4),
                        "hold_ratio": round(hold_ratio, 4),
                        "small_add_ratio": round(small_add_ratio, 4),
                    },
                )
            )

        confidence_bias = str(performance_metrics.get("confidence_bias", "neutral") or "neutral")
        if confidence_bias in {"underconfidence_bias_detected", "overconfidence_bias_detected"}:
            findings.append(
                BiasFinding(
                    bias_name="confidence_calibration_bias",
                    severity="MEDIUM",
                    message=f"Confidence calibration drift detected: {confidence_bias}.",
                    evidence={"confidence_bias": confidence_bias},
                )
            )

        if not findings:
            findings.append(
                BiasFinding(
                    bias_name="no_material_bias",
                    severity="LOW",
                    message="No material structural bias detected.",
                    evidence={"trade_count": len(trade_logs)},
                )
            )
        return findings

