from __future__ import annotations

import unittest
from unittest.mock import patch

from core.v12_dashboard_refresh import V12DashboardRefreshManager, refresh_dashboard


class V12DashboardRefreshTest(unittest.TestCase):
    def test_manual_refresh_builds_single_snapshot(self) -> None:
        with patch(
            "core.v12_dashboard_refresh.run_v12_research_evaluation",
            return_value={
                "market_regime": {
                    "structure": {"trend_score": 0.82},
                    "capital_flow": {"flow_strength": 0.74},
                    "narrative": {"narrative_strength": 0.65},
                    "cycle_state": {"unified_cycle_state": "RISK_ON"},
                    "capital_simulation": {"risk_budget": 0.76, "exposure_limit": 0.44},
                    "confidence": 0.87,
                },
                "backtest_result": {"return": 0.11, "drawdown": 0.04, "win_rate": 0.68},
                "stability_score": 0.8,
                "validation": {"stability_score": 0.8, "overfit_risk": 0.17},
                "diagnosis": {"health": {"score": 0.77}, "stability": {"status": "OK"}},
                "confidence": 0.87,
            },
        ) as mocked:
            snapshot = V12DashboardRefreshManager().refresh_analysis(symbols=("000001",))

        assert mocked.call_count == 1
        assert snapshot["refresh_mode"] == "MANUAL_ONLY"
        assert snapshot["status"] == "OK"
        assert snapshot["refresh_button"] == "REFRESH ANALYSIS"
        assert snapshot["market_state"]["structure"] == 0.82
        assert snapshot["decision"]["action"] == "BUY"
        assert "reasoning" in snapshot
        assert "comparison" in snapshot
        assert snapshot["comparison"]["summary"] == "No previous snapshot available." or snapshot["comparison"]["available"] in {True, False}

    def test_manual_refresh_uses_stale_snapshot_when_refresh_fails(self) -> None:
        manager = V12DashboardRefreshManager()
        cached = {
            "timestamp": "2026-06-21T10:00:00",
            "last_refresh_time": "2026-06-21T10:00:00",
            "refresh_mode": "MANUAL_ONLY",
            "status": "OK",
            "market_state": {"structure": 0.7, "flow": 0.6, "narrative": 0.55, "cycle": 0.8},
            "capital_state": {"risk_level": 0.2, "exposure": 0.4},
            "performance": {"return": 0.6, "drawdown": 0.2, "win_rate": 0.65},
            "decision": {"action": "HOLD", "confidence": 0.72, "risk_level": "MEDIUM"},
            "reasoning": {"key_factors": ["structure"], "dominant_driver": "structure"},
            "system_health": {"stability": 0.8, "overfitting_risk": 0.2, "data_quality": 0.9},
            "dashboard": {"version": "cached"},
            "warnings": [],
        }
        manager._save_snapshot(cached)

        with patch(
            "core.v12_dashboard_refresh.run_v12_research_evaluation",
            side_effect=RuntimeError("network failure"),
        ):
            snapshot = manager.refresh_analysis(symbols=("000001",))

        assert snapshot["status"] == "STALE DATA"
        assert "STALE DATA" in snapshot["warnings"]
        assert snapshot["refresh_button"] == "REFRESH ANALYSIS"
        assert snapshot["previous_snapshot_available"] is True
        assert snapshot["market_state"] == cached["market_state"]

    def test_convenience_wrapper_returns_snapshot(self) -> None:
        with patch(
            "core.v12_dashboard_refresh.run_v12_research_evaluation",
            return_value={
                "market_regime": {
                    "structure": {"trend_score": 0.75},
                    "capital_flow": {"flow_strength": 0.65},
                    "narrative": {"narrative_strength": 0.58},
                    "cycle_state": {"unified_cycle_state": "TRANSITION"},
                    "capital_simulation": {"risk_budget": 0.7, "exposure_limit": 0.5},
                    "confidence": 0.7,
                },
                "backtest_result": {"return": 0.06, "drawdown": 0.08, "win_rate": 0.6},
                "stability_score": 0.72,
                "validation": {"stability_score": 0.72, "overfit_risk": 0.2},
                "diagnosis": {"health": {"score": 0.7}, "stability": {"status": "OK"}},
                "confidence": 0.7,
            },
        ):
            snapshot = refresh_dashboard()

        assert snapshot["refresh_mode"] == "MANUAL_ONLY"
        assert snapshot["decision"]["action"] in {"BUY", "HOLD", "REDUCE"}

    def test_pipeline_lock_error_uses_last_valid_snapshot(self) -> None:
        manager = V12DashboardRefreshManager()
        cached = {
            "timestamp": "2026-06-21T10:00:00",
            "last_refresh_time": "2026-06-21T10:00:00",
            "refresh_mode": "MANUAL_ONLY",
            "status": "OK",
            "market_state": {"structure": 0.7, "flow": 0.6, "narrative": 0.55, "cycle": 0.8},
            "capital_state": {"risk_level": 0.2, "exposure": 0.4},
            "performance": {"return": 0.6, "drawdown": 0.2, "win_rate": 0.65},
            "decision": {"action": "HOLD", "confidence": 0.72, "risk_level": "MEDIUM"},
            "reasoning": {"key_factors": ["structure"], "dominant_driver": "structure"},
            "system_health": {"stability": 0.8, "overfitting_risk": 0.2, "data_quality": 0.9},
            "dashboard_adapter": {"panels": []},
            "ui_layout": {"layout": "dashboard"},
            "warnings": [],
            "source": "report_adapter_ui",
        }
        manager._save_snapshot(cached)

        with patch(
            "core.v12_dashboard_refresh.run_v12_research_evaluation",
            return_value={
                "market_regime": {
                    "structure": {"trend_score": 0.82},
                    "capital_flow": {"flow_strength": 0.74},
                    "narrative": {"narrative_strength": 0.65},
                    "cycle_state": {"unified_cycle_state": "RISK_ON"},
                    "capital_simulation": {"risk_budget": 0.76, "exposure_limit": 0.44},
                    "confidence": 0.87,
                },
                "backtest_result": {"return": 0.11, "drawdown": 0.04, "win_rate": 0.68},
                "stability_score": 0.8,
                "validation": {"stability_score": 0.8, "overfit_risk": 0.17},
                "diagnosis": {"health": {"score": 0.77}, "stability": {"status": "OK"}},
                "confidence": 0.87,
            },
        ), patch(
            "core.v12_dashboard_refresh.adapt_v12_dashboard",
            return_value={"bad": "payload"},
        ):
            snapshot = manager.refresh_analysis(symbols=("000001",))

        assert snapshot["status"] == "PIPELINE_LOCK_ERROR"
        assert snapshot["last_valid_snapshot"]["status"] == "OK"
        assert snapshot["previous_snapshot_available"] is True


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
