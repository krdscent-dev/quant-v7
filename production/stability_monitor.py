"""System stability monitor for V12.9."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping


@dataclass(frozen=True)
class StabilityReport:
    """Summary of signal consistency and model drift."""

    status: str
    drift_score: float
    inconsistency_score: float
    sync_score: float
    warnings: list[str]


class StabilityMonitor:
    """Detect inconsistent signals and model drift."""

    def assess(
        self,
        trade_logs: list[Mapping[str, Any]],
        v11_decisions: list[Mapping[str, Any]],
        repair_loop_report: Mapping[str, Any] | None = None,
    ) -> StabilityReport:
        repair_loop_report = dict(repair_loop_report or {})
        if not trade_logs and not v11_decisions:
            return StabilityReport(
                status="UNSTABLE",
                drift_score=1.0,
                inconsistency_score=1.0,
                sync_score=0.0,
                warnings=["no_signal_data"],
            )

        symbol_actions: dict[str, set[str]] = {}
        action_alignment: list[float] = []
        confidence_series: list[float] = []
        for trade in trade_logs:
            symbol = str(trade.get("symbol", "UNKNOWN"))
            action = str(trade.get("action", "OBSERVE")).upper()
            symbol_actions.setdefault(symbol, set()).add(action)
            confidence_series.append(float(trade.get("confidence", 0.0) or 0.0))

        for decision in v11_decisions:
            confidence = float(decision.get("market_intelligence", {}).get("capital_flow_score", 0.0) or 0.0)
            confidence_series.append(confidence)
            actions = {
                str(decision.get("final_weighted_decision", decision.get("final_action", "OBSERVE"))).upper(),
                str(decision.get("final_action", "OBSERVE")).upper(),
            }
            action_alignment.append(1.0 if len(actions) == 1 else 0.8)

        unique_action_ratio = mean((len(actions) for actions in symbol_actions.values())) if symbol_actions else 1.0
        repeated_symbol_ratio = sum(1 for actions in symbol_actions.values() if len(actions) > 1) / max(len(symbol_actions), 1)
        confidence_dispersion = 0.0
        if confidence_series:
            avg_conf = mean(confidence_series)
            confidence_dispersion = mean(abs(value - avg_conf) for value in confidence_series)

        drift_score = max(0.0, min(1.0, 0.45 * repeated_symbol_ratio + 0.35 * confidence_dispersion + 0.20 * (1.0 - mean(action_alignment) if action_alignment else 0.0)))
        inconsistency_score = max(0.0, min(1.0, 0.6 * repeated_symbol_ratio + 0.4 * min(1.0, unique_action_ratio / 3.0)))
        sync_score = 1.0 if trade_logs and v11_decisions else 0.0

        warnings: list[str] = []
        if repeated_symbol_ratio > 0.10:
            warnings.append("symbol_action_flip_detected")
        if confidence_dispersion > 0.12:
            warnings.append("confidence_dispersion_elevated")
        if action_alignment and mean(action_alignment) < 0.9:
            warnings.append("decision_alignment_degraded")

        score = 1.0 - (0.45 * drift_score + 0.35 * inconsistency_score + 0.20 * (1.0 - sync_score))
        if score >= 0.80:
            status = "STABLE"
        elif score >= 0.60:
            status = "WARNING"
        else:
            status = "UNSTABLE"
        return StabilityReport(
            status=status,
            drift_score=round(drift_score, 4),
            inconsistency_score=round(inconsistency_score, 4),
            sync_score=round(sync_score, 4),
            warnings=warnings,
        )
