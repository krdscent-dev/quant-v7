from __future__ import annotations

import unittest
from unittest.mock import patch

import main as v12_main


class MainPipelineEntryTest(unittest.TestCase):
    def test_locked_pipeline_runs_in_fixed_order(self) -> None:
        call_order: list[str] = []

        def mark(name, value):
            call_order.append(name)
            return value

        with patch("main.load_market_data", side_effect=lambda symbols=None: mark("load_market_data", {"symbols": ("000001",)})), patch(
            "main.run_v12_engine",
            side_effect=lambda market_data: mark("run_v12_engine", {"recommendation": "GO", "decision": "OK"}),
        ), patch(
            "main.generate_research_report",
            side_effect=lambda v12_result: mark("generate_research_report", {"markdown": "a.md", "json": "a.json"}),
        ), patch(
            "main.normalize_schema",
            side_effect=lambda v12_result: mark(
                "normalize_schema",
                {
                    "market_state": {"structure": 0.7, "flow": 0.6, "narrative": 0.55, "cycle": 0.8},
                    "capital_state": {"risk_level": 0.2, "exposure": 0.4},
                    "performance": {"return": 0.6, "drawdown": 0.2, "win_rate": 0.65},
                    "system_health": {"stability": 0.8, "overfitting_risk": 0.2, "data_quality": 0.9},
                    "decision": {"action": "HOLD", "confidence": 0.72, "risk_level": "MEDIUM"},
                    "explanation": {"key_factors": ["structure"], "dominant_driver": "structure"},
                },
            ),
        ), patch(
            "main.adapt_to_dashboard",
            side_effect=lambda normalized: mark(
                "adapt_to_dashboard",
                {
                    "panels": [
                        {"panel": "market_overview", "structure": 0.7, "flow": 0.6, "narrative": 0.55, "cycle": 0.8},
                        {"panel": "risk", "risk_level": 0.2, "exposure": 0.4, "stability": 0.8},
                        {"panel": "performance", "return": 0.6, "drawdown": 0.2, "win_rate": 0.65},
                        {"panel": "decision_core", "action": "HOLD", "confidence": 0.72, "reasoning": ["structure"]},
                    ]
                },
            ),
        ), patch(
            "main.render_ui",
            side_effect=lambda dashboard: mark(
                "render_ui",
                {
                    "layout": "dashboard",
                    "status": "NORMAL",
                    "components": [],
                },
            ),
        ), patch(
            "main.compute_final_decision",
            side_effect=lambda v12_result, normalized, dashboard, ui: mark(
                "compute_final_decision",
                {"action": "HOLD", "confidence": 0.72, "risk_level": "MEDIUM"},
            ),
        ):
            pipeline = v12_main.run_v12_locked_pipeline(symbols=("000001",))

        assert call_order == [
            "load_market_data",
            "run_v12_engine",
            "generate_research_report",
            "normalize_schema",
            "adapt_to_dashboard",
            "render_ui",
            "compute_final_decision",
        ]
        assert pipeline["final_decision"]["action"] == "HOLD"
        assert pipeline["report_paths"]["markdown"] == "a.md"

    def test_compute_final_decision_forces_hold_on_architecture_violation(self) -> None:
        decision = v12_main.compute_final_decision(
            {"recommendation": "GO"},
            {
                "decision": {"action": "BUY", "confidence": 0.9, "risk_level": "LOW"},
                "explanation": {"key_factors": ["structure"], "dominant_driver": "structure"},
            },
            {"decision_core": {"final_action": "BUY"}},
            {"status": "ARCHITECTURE VIOLATION"},
        )

        assert decision["action"] == "HOLD"
        assert decision["confidence"] == 0.3
        assert decision["ui_status"] == "ARCHITECTURE VIOLATION"


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
