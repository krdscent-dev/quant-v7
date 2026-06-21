from __future__ import annotations

import unittest

from core.v12_dashboard_builder import V12DashboardBuilder, build_v12_dashboard


class V12DashboardBuilderTest(unittest.TestCase):
    def test_dashboard_includes_decision_core_first(self) -> None:
        normalized = {
            "market_state": {"structure": 0.81, "flow": 0.74, "narrative": 0.63, "cycle": 0.88},
            "capital_state": {"risk_level": 0.24, "exposure": 0.41},
            "performance": {"return": 0.64, "drawdown": 0.22, "win_rate": 0.67},
            "system_health": {"stability": 0.79, "overfitting_risk": 0.19, "data_quality": 0.87},
            "decision": {"action": "BUY", "confidence": 0.84, "risk_level": "LOW"},
            "explanation": {"key_factors": ["structure", "cycle"], "dominant_driver": "structure"},
        }

        dashboard = V12DashboardBuilder().build(normalized)

        assert dashboard["version"] == "v12-dashboard-schema-v1"
        assert dashboard["confidence_state"] == "NORMAL"
        assert dashboard["fallback_state"] is False
        assert dashboard["decision_core"]["final_action"] == "BUY"
        assert dashboard["decision_core"]["confidence"] == 0.84
        assert dashboard["panels"][0]["panel_id"] == "decision_core"
        assert dashboard["panels"][0]["dominant"] is True
        assert dashboard["panels"][0]["chart_type"] == "label+gauge"
        assert dashboard["panels"][1]["panel_id"] == "market_overview"
        assert dashboard["panels"][2]["panel_id"] == "capital_risk"
        assert dashboard["panels"][3]["panel_id"] == "performance"
        assert dashboard["panels"][4]["panel_id"] == "system_health"
        assert dashboard["visual_mappings"]["decision"]["action"] == "large_center_label"
        assert dashboard["visual_mappings"]["dominance_rule"] == "decision_first"
        assert dashboard["market_state"]["structure"] == 0.81
        assert dashboard["capital_state"]["risk_level"] == 0.24
        assert dashboard["performance"]["win_rate"] == 0.67
        assert dashboard["system_health"]["data_quality"] == 0.87

    def test_dashboard_defaults_to_low_confidence_when_missing_data(self) -> None:
        dashboard = build_v12_dashboard({})

        assert dashboard["fallback_state"] is True
        assert dashboard["confidence_state"] == "LOW CONFIDENCE"
        assert dashboard["decision"]["action"] == "HOLD"
        assert dashboard["decision_core"]["confidence"] == 0.3
        assert dashboard["decision_core"]["risk_level"] == "HIGH"
        assert dashboard["market_state"] == {
            "structure": 0.5,
            "flow": 0.5,
            "narrative": 0.5,
            "cycle": 0.5,
        }


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
