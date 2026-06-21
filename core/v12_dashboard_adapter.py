"""Adapter from the normalized V12 report to dashboard-ready JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _safe_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


@dataclass(frozen=True)
class V12DashboardAdapter:
    """Transform the standardized V12 schema into dashboard JSON."""

    neutral: float = 0.5

    def adapt(self, normalized_report: Mapping[str, Any] | None) -> dict[str, Any]:
        report = dict(normalized_report or {})
        market_state = _safe_mapping(report.get("market_state"))
        capital_state = _safe_mapping(report.get("capital_state"))
        performance = _safe_mapping(report.get("performance"))
        system_health = _safe_mapping(report.get("system_health"))
        decision = _safe_mapping(report.get("decision"))
        explanation = _safe_mapping(report.get("explanation"))

        structure = _safe_float(market_state.get("structure", self.neutral), self.neutral)
        flow = _safe_float(market_state.get("flow", self.neutral), self.neutral)
        narrative = _safe_float(market_state.get("narrative", self.neutral), self.neutral)
        cycle = _safe_float(market_state.get("cycle", self.neutral), self.neutral)

        risk_level = _safe_float(capital_state.get("risk_level", self.neutral), self.neutral)
        exposure = _safe_float(capital_state.get("exposure", self.neutral), self.neutral)
        stability = _safe_float(system_health.get("stability", self.neutral), self.neutral)

        ret = _safe_float(performance.get("return", self.neutral), self.neutral)
        drawdown = _safe_float(performance.get("drawdown", self.neutral), self.neutral)
        win_rate = _safe_float(performance.get("win_rate", self.neutral), self.neutral)

        action = str(decision.get("action", "HOLD"))
        if action not in {"BUY", "HOLD", "REDUCE"}:
            action = "HOLD"
        confidence = _safe_float(decision.get("confidence", self.neutral), self.neutral)
        reasoning = _safe_list(explanation.get("key_factors", []))
        if not reasoning:
            dominant_driver = explanation.get("dominant_driver", "neutral")
            reasoning = [str(dominant_driver)] if dominant_driver else []
        if not reasoning:
            reasoning = ["neutral"]

        return {
            "panels": [
                {
                    "panel": "market_overview",
                    "structure": structure,
                    "flow": flow,
                    "narrative": narrative,
                    "cycle": cycle,
                },
                {
                    "panel": "risk",
                    "risk_level": risk_level,
                    "exposure": exposure,
                    "stability": stability,
                },
                {
                    "panel": "performance",
                    "return": ret,
                    "drawdown": drawdown,
                    "win_rate": win_rate,
                },
                {
                    "panel": "decision_core",
                    "action": action,
                    "confidence": confidence,
                    "reasoning": reasoning,
                },
            ]
        }


def adapt_v12_dashboard(normalized_report: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convenience wrapper for dashboard JSON transformation."""

    return V12DashboardAdapter().adapt(normalized_report)

