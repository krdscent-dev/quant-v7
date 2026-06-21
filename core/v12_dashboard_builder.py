"""LEGACY_LOCKED dashboard builder.

This module is retained for compatibility only and must not be used in the
production V12 path. The production flow is:
Report -> Adapter -> UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.v12_dashboard_schema import DashboardMetric, DashboardPanel, V12DashboardSchema

LEGACY_LOCKED = True


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _risk_color(value: float) -> str:
    if value <= 0.33:
        return "green"
    if value <= 0.66:
        return "yellow"
    return "red"


def _confidence_state(confidence: float) -> str:
    if confidence < 0.35:
        return "LOW CONFIDENCE"
    if confidence < 0.65:
        return "WATCH"
    return "NORMAL"


@dataclass(frozen=True)
class V12DashboardBuilder:
    """Convert a normalized report into a JSON layout structure."""

    def build(self, normalized_report: Mapping[str, Any] | None) -> dict[str, Any]:
        report = dict(normalized_report or {})
        fallback_state = not bool(report)
        market_state = report.get("market_state", {})
        capital_state = report.get("capital_state", {})
        performance = report.get("performance", {})
        system_health = report.get("system_health", {})
        decision = report.get("decision", {})
        explanation = report.get("explanation", {})

        structure = _clamp(_safe_float(market_state.get("structure", 0.5)))
        flow = _clamp(_safe_float(market_state.get("flow", 0.5)))
        narrative = _clamp(_safe_float(market_state.get("narrative", 0.5)))
        cycle = _clamp(_safe_float(market_state.get("cycle", 0.5)))
        risk_level = _clamp(_safe_float(capital_state.get("risk_level", 0.5)))
        exposure = _clamp(_safe_float(capital_state.get("exposure", 0.5)))
        ret = _clamp(_safe_float(performance.get("return", 0.5)))
        drawdown = _clamp(_safe_float(performance.get("drawdown", 0.5)))
        win_rate = _clamp(_safe_float(performance.get("win_rate", 0.5)))
        stability = _clamp(_safe_float(system_health.get("stability", 0.5)))
        overfit = _clamp(_safe_float(system_health.get("overfitting_risk", 0.5)))
        data_quality = _clamp(_safe_float(system_health.get("data_quality", 0.5)))
        action = str(decision.get("action", "HOLD"))
        confidence = _clamp(_safe_float(decision.get("confidence", 0.3), 0.3))
        decision_risk = str(decision.get("risk_level", "MEDIUM"))
        reasoning = explanation.get("dominant_driver", "neutral fallback")
        key_factors = list(explanation.get("key_factors", []))

        panels = [
            DashboardPanel(
                panel_id="decision_core",
                title="Decision Core Panel",
                priority=1,
                dominant=True,
                layout="hero",
                chart_type="label+gauge",
                metrics=(
                    DashboardMetric("final_action", "Final Action", 1.0 if action == "BUY" else 0.5 if action == "HOLD" else 0.25, "label", "red" if action == "REDUCE" else "green" if action == "BUY" else "yellow"),
                    DashboardMetric("confidence", "Confidence", confidence, "gauge", "green" if confidence >= 0.65 else "yellow" if confidence >= 0.35 else "red"),
                ),
                data_binding={
                    "final_action": action,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "risk_level": decision_risk,
                },
                description="Largest visual element. The decision summary always leads the layout.",
            ),
            DashboardPanel(
                panel_id="market_overview",
                title="Market Overview Panel",
                priority=2,
                layout="grid",
                chart_type="line+bar",
                metrics=(
                    DashboardMetric("structure", "Structure", structure, "bar"),
                    DashboardMetric("flow", "Flow", flow, "bar"),
                    DashboardMetric("narrative", "Narrative", narrative, "bar"),
                    DashboardMetric("cycle", "Cycle", cycle, "bar"),
                ),
                data_binding={
                    "structure": structure,
                    "flow": flow,
                    "narrative": narrative,
                    "cycle": cycle,
                },
                description="Compare the four market-state signals side by side.",
            ),
            DashboardPanel(
                panel_id="capital_risk",
                title="Capital & Risk Panel",
                priority=3,
                layout="split",
                chart_type="indicator+gauge",
                metrics=(
                    DashboardMetric("risk_level", "Risk Level", risk_level, "indicator", _risk_color(risk_level)),
                    DashboardMetric("exposure", "Exposure", exposure, "gauge", _risk_color(exposure)),
                ),
                data_binding={
                    "risk_level": risk_level,
                    "exposure": exposure,
                    "risk_color": _risk_color(risk_level),
                },
                description="Summarize capital pressure and exposure at a glance.",
            ),
            DashboardPanel(
                panel_id="performance",
                title="Performance Panel",
                priority=4,
                layout="chart",
                chart_type="line",
                metrics=(
                    DashboardMetric("return", "Return", ret, "line"),
                    DashboardMetric("drawdown", "Drawdown", drawdown, "line", "red" if drawdown >= 0.5 else "yellow"),
                    DashboardMetric("win_rate", "Win Rate", win_rate, "line", "green" if win_rate >= 0.6 else "yellow"),
                ),
                data_binding={
                    "return": ret,
                    "drawdown": drawdown,
                    "win_rate": win_rate,
                    "equity_curve": report.get("backtest_result", {}).get("equity_curve", []),
                },
                description="Show performance time series or summary metrics when the curve is unavailable.",
            ),
            DashboardPanel(
                panel_id="system_health",
                title="System Health Panel",
                priority=5,
                layout="grid",
                chart_type="gauge+indicator",
                metrics=(
                    DashboardMetric("stability", "Stability", stability, "gauge", "green" if stability >= 0.66 else "yellow" if stability >= 0.35 else "red"),
                    DashboardMetric("overfitting_risk", "Overfitting Risk", overfit, "gauge", "red" if overfit >= 0.66 else "yellow"),
                    DashboardMetric("data_quality", "Data Quality", data_quality, "gauge", "green" if data_quality >= 0.66 else "yellow" if data_quality >= 0.35 else "red"),
                ),
                data_binding={
                    "stability": stability,
                    "overfitting_risk": overfit,
                    "data_quality": data_quality,
                },
                description="Surface system integrity and confidence in the data pipeline.",
            ),
        ]

        visual_mappings = {
            "market_state": {
                "structure": "bar",
                "flow": "bar",
                "narrative": "bar",
                "cycle": "bar",
            },
            "capital_state": {
                "risk_level": "red_yellow_green_indicator",
                "exposure": "gauge",
            },
            "performance": {
                "return": "line",
                "drawdown": "line",
                "win_rate": "line",
                "equity_curve": "line_chart",
            },
            "system_health": {
                "stability": "gauge",
                "overfitting_risk": "gauge",
                "data_quality": "gauge",
            },
            "decision": {
                "action": "large_center_label",
                "confidence": "gauge",
                "reasoning": "text",
            },
            "dominance_rule": "decision_first",
        }

        if fallback_state:
            confidence = 0.3
            action = "HOLD"
            decision_risk = "HIGH"
            reasoning = "neutral fallback"
            key_factors = ["structure", "flow"]

        schema = V12DashboardSchema(
            confidence_state=_confidence_state(confidence),
            headline="Decision first, data second",
            panels=tuple(panels),
            visual_mappings=visual_mappings,
            fallback_state=fallback_state,
        )
        payload = schema.to_dict()
        payload["decision_core"] = {
            "final_action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "risk_level": decision_risk,
            "key_factors": key_factors,
        }
        payload["market_state"] = {
            "structure": structure,
            "flow": flow,
            "narrative": narrative,
            "cycle": cycle,
        }
        payload["capital_state"] = {"risk_level": risk_level, "exposure": exposure}
        payload["performance"] = {"return": ret, "drawdown": drawdown, "win_rate": win_rate}
        payload["system_health"] = {
            "stability": stability,
            "overfitting_risk": overfit,
            "data_quality": data_quality,
        }
        payload["decision"] = {
            "action": action,
            "confidence": confidence,
            "risk_level": decision_risk,
        }
        payload["explanation"] = {
            "key_factors": key_factors,
            "dominant_driver": reasoning,
        }
        return payload


def build_v12_dashboard(normalized_report: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convenience wrapper for callers that need the dashboard JSON."""

    return V12DashboardBuilder().build(normalized_report)
