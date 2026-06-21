from __future__ import annotations

import unittest

from core.v12_dashboard_adapter import V12DashboardAdapter, adapt_v12_dashboard


class V12DashboardAdapterTest(unittest.TestCase):
    def test_adapter_transforms_normalized_report(self) -> None:
        normalized = {
            "market_state": {"structure": 0.8, "flow": 0.7, "narrative": 0.6, "cycle": 0.9},
            "capital_state": {"risk_level": 0.2, "exposure": 0.4},
            "performance": {"return": 0.62, "drawdown": 0.18, "win_rate": 0.67},
            "system_health": {"stability": 0.81, "overfitting_risk": 0.2, "data_quality": 0.88},
            "decision": {"action": "BUY", "confidence": 0.84, "risk_level": "LOW"},
            "explanation": {"key_factors": ["structure", "cycle"], "dominant_driver": "structure"},
        }

        dashboard = V12DashboardAdapter().adapt(normalized)

        assert list(dashboard) == ["panels"]
        assert len(dashboard["panels"]) == 4
        assert dashboard["panels"][0]["panel"] == "market_overview"
        assert dashboard["panels"][0]["structure"] == 0.8
        assert dashboard["panels"][1]["panel"] == "risk"
        assert dashboard["panels"][1]["stability"] == 0.81
        assert dashboard["panels"][2]["panel"] == "performance"
        assert dashboard["panels"][2]["win_rate"] == 0.67
        assert dashboard["panels"][3]["panel"] == "decision_core"
        assert dashboard["panels"][3]["action"] == "BUY"
        assert dashboard["panels"][3]["confidence"] == 0.84
        assert dashboard["panels"][3]["reasoning"] == ["structure", "cycle"]

    def test_adapter_falls_back_to_neutral_values(self) -> None:
        dashboard = adapt_v12_dashboard({})

        assert dashboard["panels"][0] == {
            "panel": "market_overview",
            "structure": 0.5,
            "flow": 0.5,
            "narrative": 0.5,
            "cycle": 0.5,
        }
        assert dashboard["panels"][1] == {
            "panel": "risk",
            "risk_level": 0.5,
            "exposure": 0.5,
            "stability": 0.5,
        }
        assert dashboard["panels"][3]["action"] == "HOLD"
        assert dashboard["panels"][3]["confidence"] == 0.5
        assert dashboard["panels"][3]["reasoning"] == ["neutral"]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
