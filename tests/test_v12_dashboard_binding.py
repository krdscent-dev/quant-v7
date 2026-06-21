from __future__ import annotations

import unittest

from core.v12_dashboard_adapter import adapt_v12_dashboard
from ui.v12_ui_layer import build_v12_ui


class V12DashboardBindingTest(unittest.TestCase):
    def test_ui_rejects_raw_report_like_payload(self) -> None:
        raw_like_payload = {
            "market_state": {"structure": 0.8, "flow": 0.7, "narrative": 0.6, "cycle": 0.9},
            "capital_state": {"risk_level": 0.2, "exposure": 0.4},
            "performance": {"return": 0.62, "drawdown": 0.18, "win_rate": 0.67},
            "system_health": {"stability": 0.81, "overfitting_risk": 0.2, "data_quality": 0.88},
            "decision": {"action": "BUY", "confidence": 0.84, "risk_level": "LOW"},
            "explanation": {"key_factors": ["structure", "cycle"], "dominant_driver": "structure"},
        }

        ui = build_v12_ui(raw_like_payload)

        assert ui["status"] == "NO VALID SNAPSHOT"
        assert ui["components"][0]["type"] == "status_banner"
        assert ui["components"][0]["label"] == "NO VALID SNAPSHOT"
        assert ui["components"][2]["data"]["action"] == "HOLD"
        assert ui["components"][2]["data"]["confidence"] == 0.3

    def test_ui_accepts_adapter_output_only(self) -> None:
        dashboard_adapter_output = adapt_v12_dashboard(
            {
                "market_state": {"structure": 0.8, "flow": 0.7, "narrative": 0.6, "cycle": 0.9},
                "capital_state": {"risk_level": 0.2, "exposure": 0.4},
                "performance": {"return": 0.62, "drawdown": 0.18, "win_rate": 0.67},
                "system_health": {"stability": 0.81, "overfitting_risk": 0.2, "data_quality": 0.88},
                "decision": {"action": "BUY", "confidence": 0.84, "risk_level": "LOW"},
                "explanation": {"key_factors": ["structure", "cycle"], "dominant_driver": "structure"},
            }
        )

        ui = build_v12_ui(dashboard_adapter_output)

        assert ui["status"] == "NORMAL"
        assert ui["components"][0]["type"] == "button"
        assert ui["components"][3]["type"] == "decision_card"
        assert ui["components"][3]["data"]["action"] == "BUY"
        assert ui["components"][3]["highlight"] is True


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
