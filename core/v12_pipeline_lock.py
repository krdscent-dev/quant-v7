"""Strict pipeline lock helpers for the V12 dashboard flow."""

from __future__ import annotations

from typing import Any, Mapping

REQUIRED_PANEL_ORDER = ("market_overview", "risk", "performance", "decision_core")


def validate_adapter_payload(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    panels = payload.get("panels")
    if not isinstance(panels, list) or len(panels) != 4:
        return False
    for panel, expected_name in zip(panels, REQUIRED_PANEL_ORDER, strict=True):
        if not isinstance(panel, Mapping):
            return False
        if str(panel.get("panel", "")) != expected_name:
            return False
    return True


def pipeline_lock_error_state(last_valid_snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "PIPELINE_LOCK_ERROR",
        "error": "PIPELINE_LOCK_ERROR",
        "message": "Adapter output did not match the locked schema.",
        "last_valid_snapshot": dict(last_valid_snapshot or {}),
    }
    return payload

