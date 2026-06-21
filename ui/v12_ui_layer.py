"""User-facing V12 UI layer.

This layer only consumes the dashboard adapter output. It does not inspect
raw report objects or any upstream model output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.v12_dashboard_adapter import validate_dashboard_adapter_output
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


def _risk_override(risk_level: float) -> bool:
    return _clamp(risk_level) >= 0.66


@dataclass(frozen=True)
class V12UILayer:
    """Convert adapter output into a human-readable interaction layout."""

    def build(self, adapter_output: Mapping[str, Any] | None) -> dict[str, Any]:
        if not validate_dashboard_adapter_output(adapter_output):
            schema = V12UISchema(
                mode="MANUAL_REFRESH_ONLY",
                confidence_state="LOW CONFIDENCE",
                components=(
                    UIComponent(
                        type="status_banner",
                        label="NO VALID SNAPSHOT",
                        data={"message": "NO VALID SNAPSHOT", "severity": "warning"},
                        highlight=True,
                    ),
                    UIComponent(
                        type="button",
                        label="Refresh Snapshot",
                        data={"action": "REFRESH ANALYSIS", "mode": "manual_only"},
                    ),
                    UIComponent(
                        type="decision_card",
                        label="Decision Core",
                        highlight=True,
                        data={"action": "HOLD", "confidence": 0.3, "reason": "NO VALID SNAPSHOT"},
                    ),
                ),
            )
            payload = schema.to_dict()
            payload["status"] = "NO VALID SNAPSHOT"
            return payload

        dashboard = dict(adapter_output or {})
        panels = dashboard.get("panels", [])
        if not isinstance(panels, list):
            panels = []

        market_panel = next((panel for panel in panels if isinstance(panel, Mapping) and panel.get("panel") == "market_overview"), {})
        risk_panel = next((panel for panel in panels if isinstance(panel, Mapping) and panel.get("panel") == "risk"), {})
        performance_panel = next((panel for panel in panels if isinstance(panel, Mapping) and panel.get("panel") == "performance"), {})
        decision_panel = next((panel for panel in panels if isinstance(panel, Mapping) and panel.get("panel") == "decision_core"), {})

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
        reason_text = "Risk override active" if override else "Manual refresh ready"
        schema = V12UISchema(
            mode="MANUAL_REFRESH_ONLY",
            confidence_state="LOW CONFIDENCE" if confidence < 0.35 else "WATCH" if confidence < 0.65 else "NORMAL",
            components=(
                UIComponent(
                    type="button",
                    label="Refresh Snapshot",
                    data={"action": "REFRESH ANALYSIS", "mode": "manual_only"},
                ),
                UIComponent(
                    type="market_panel",
                    data={
                        "structure": _safe_float(market_panel.get("structure", 0.5)),
                        "flow": _safe_float(market_panel.get("flow", 0.5)),
                        "narrative": _safe_float(market_panel.get("narrative", 0.5)),
                        "cycle": _safe_float(market_panel.get("cycle", 0.5)),
                    },
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
                        "comparison_available": False,
                    },
                    label="Reasoning",
                ),
            ),
        )
        payload = schema.to_dict()
        payload["status"] = "LOW CONFIDENCE" if confidence < 0.35 else "NORMAL"
        payload["risk_override"] = override
        return payload


def build_v12_ui(adapter_output: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convenience wrapper for the UI layout schema."""

    return V12UILayer().build(adapter_output)
