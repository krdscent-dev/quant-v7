"""User-facing UI layer for the V12 dashboard output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.v12_ui_schema import UIComponent, V12UISchema


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _safe_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _confidence_state(confidence: float) -> str:
    if confidence < 0.35:
        return "LOW CONFIDENCE"
    if confidence < 0.65:
        return "WATCH"
    return "NORMAL"


def _risk_override(risk_level: float) -> bool:
    return _clamp(risk_level) >= 0.66


@dataclass(frozen=True)
class V12UILayer:
    """Convert dashboard JSON into a human-readable interaction layout."""

    def build(self, dashboard_json: Mapping[str, Any] | None) -> dict[str, Any]:
        dashboard = dict(dashboard_json or {})
        panels = dashboard.get("panels", [])
        if not isinstance(panels, list):
            panels = []

        market_panel = next((panel for panel in panels if panel.get("panel") == "market_overview"), {})
        risk_panel = next((panel for panel in panels if panel.get("panel") == "risk"), {})
        performance_panel = next((panel for panel in panels if panel.get("panel") == "performance"), {})
        decision_panel = next((panel for panel in panels if panel.get("panel") == "decision_core"), {})

        market_data = {
            "structure": _safe_float(market_panel.get("structure", 0.5)),
            "flow": _safe_float(market_panel.get("flow", 0.5)),
            "narrative": _safe_float(market_panel.get("narrative", 0.5)),
            "cycle": _safe_float(market_panel.get("cycle", 0.5)),
        }
        risk_level = _safe_float(risk_panel.get("risk_level", 0.5))
        exposure = _safe_float(risk_panel.get("exposure", 0.5))
        stability = _safe_float(risk_panel.get("stability", 0.5))
        decision_action = str(decision_panel.get("action", "HOLD"))
        if decision_action not in {"BUY", "HOLD", "REDUCE"}:
            decision_action = "HOLD"
        confidence = _safe_float(decision_panel.get("confidence", 0.3), 0.3)
        reasoning = decision_panel.get("reasoning", [])
        if not isinstance(reasoning, list):
            reasoning = [str(reasoning)] if reasoning else []
        if not reasoning:
            reasoning = ["neutral"]

        override = _risk_override(risk_level)
        if override:
            reason_text = "Risk override active"
        else:
            reason_text = "Manual refresh ready"

        schema = V12UISchema(
            mode="MANUAL_REFRESH_ONLY",
            confidence_state=_confidence_state(confidence),
            components=(
                UIComponent(
                    type="button",
                    label="Refresh Snapshot",
                    data={
                        "action": "REFRESH ANALYSIS",
                        "mode": "manual_only",
                        "last_refresh_time": dashboard.get("last_refresh_time", dashboard.get("timestamp", "")),
                    },
                ),
                UIComponent(
                    type="market_panel",
                    data=market_data,
                    label="Market Overview",
                ),
                UIComponent(
                    type="risk_panel",
                    data={
                        "risk_level": risk_level,
                        "exposure": exposure,
                        "stability": stability,
                        "override": override,
                    },
                    label="Risk Control",
                    highlight=override,
                ),
                UIComponent(
                    type="decision_card",
                    data={
                        "action": decision_action,
                        "confidence": confidence,
                        "risk_override": override,
                        "risk_level": risk_level,
                        "reason": reason_text,
                        "performance": {
                            "return": _safe_float(_safe_mapping(performance_panel).get("return", 0.5)),
                            "drawdown": _safe_float(_safe_mapping(performance_panel).get("drawdown", 0.5)),
                            "win_rate": _safe_float(_safe_mapping(performance_panel).get("win_rate", 0.5)),
                        },
                    },
                    label="Decision Core",
                    highlight=True,
                ),
                UIComponent(
                    type="reasoning_panel",
                    data={
                        "items": reasoning,
                        "last_refresh_time": dashboard.get("last_refresh_time", dashboard.get("timestamp", "")),
                        "comparison_available": bool(dashboard.get("comparison", {}).get("available", False)),
                    },
                    label="Reasoning",
                ),
            ),
        )
        payload = schema.to_dict()
        payload["dashboard"] = dashboard
        payload["risk_override"] = override
        payload["status"] = "LOW CONFIDENCE" if confidence < 0.35 else "NORMAL"
        return payload


def build_v12_ui(dashboard_json: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convenience wrapper for the UI layout schema."""

    return V12UILayer().build(dashboard_json)

