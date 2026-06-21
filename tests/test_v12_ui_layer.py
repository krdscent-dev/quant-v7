from __future__ import annotations

import unittest

from core.v12_ui_layer import V12UILayer, build_v12_ui


class V12UILayerTest(unittest.TestCase):
    def test_ui_layout_uses_manual_refresh_and_dominant_decision_card(self) -> None:
        dashboard = {
            "timestamp": "2026-06-21T10:00:00",
            "last_refresh_time": "2026-06-21T10:00:00",
            "panels": [
                {"panel": "market_overview", "structure": 0.8, "flow": 0.7, "narrative": 0.6, "cycle": 0.9},
                {"panel": "risk", "risk_level": 0.24, "exposure": 0.41, "stability": 0.8},
                {"panel": "performance", "return": 0.62, "drawdown": 0.18, "win_rate": 0.67},
                {"panel": "decision_core", "action": "BUY", "confidence": 0.84, "reasoning": ["structure", "cycle"]},
            ],
            "comparison": {"available": True},
        }

        ui = V12UILayer().build(dashboard)

        assert ui["layout"] == "dashboard"
        assert ui["mode"] == "MANUAL_REFRESH_ONLY"
        assert ui["confidence_state"] == "NORMAL"
        assert len(ui["components"]) == 5
        assert ui["components"][0]["type"] == "button"
        assert ui["components"][0]["label"] == "Refresh Snapshot"
        assert ui["components"][1]["type"] == "market_panel"
        assert ui["components"][2]["type"] == "risk_panel"
        assert ui["components"][3]["type"] == "decision_card"
        assert ui["components"][3]["highlight"] is True
        assert ui["components"][3]["data"]["action"] == "BUY"
        assert ui["components"][4]["type"] == "reasoning_panel"
        assert ui["components"][4]["data"]["items"] == ["structure", "cycle"]
        assert ui["risk_override"] is False
        assert ui["status"] == "NORMAL"

    def test_ui_layer_overrides_visuals_when_risk_is_high(self) -> None:
        dashboard = {
            "panels": [
                {"panel": "market_overview", "structure": 0.8, "flow": 0.7, "narrative": 0.6, "cycle": 0.9},
                {"panel": "risk", "risk_level": 0.8, "exposure": 0.85, "stability": 0.3},
                {"panel": "performance", "return": 0.62, "drawdown": 0.18, "win_rate": 0.67},
                {"panel": "decision_core", "action": "BUY", "confidence": 0.84, "reasoning": ["structure", "cycle"]},
            ]
        }

        ui = build_v12_ui(dashboard)

        assert ui["risk_override"] is True
        assert ui["components"][2]["highlight"] is True
        assert ui["components"][3]["data"]["risk_override"] is True
        assert ui["components"][3]["data"]["reason"] == "Risk override active"

    def test_ui_layer_defaults_to_neutral_state_when_missing(self) -> None:
        ui = build_v12_ui({})

        assert ui["status"] == "PIPELINE_LOCK_ERROR"
        assert ui["error"] == "PIPELINE_LOCK_ERROR"
        assert ui["message"] == "Adapter output did not match the locked schema."
        assert ui["last_valid_snapshot"] == {}


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
