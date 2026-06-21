from __future__ import annotations

from core.v12_4_cycle_engine import CycleEngine, build_cycle_state


def test_core_cycle_engine_detects_risk_on_state() -> None:
    result = build_cycle_state(
        {
            "volatility": 0.25,
            "flow_strength": 0.72,
            "narrative_strength": 0.68,
        }
    )

    assert result["liquidity_cycle"] == "EXPANSION"
    assert result["sentiment_cycle"] == "GREED"
    assert result["industry_cycle"] == "MATURITY"
    assert result["unified_cycle_state"] == "RISK_ON"


def test_core_cycle_engine_detects_risk_off_state() -> None:
    result = CycleEngine().build_cycle_state(
        {
            "volatility": 0.85,
            "flow_strength": 0.20,
            "narrative_strength": 0.30,
        }
    )

    assert result["liquidity_cycle"] == "CONTRACTION"
    assert result["sentiment_cycle"] == "PANIC"
    assert result["industry_cycle"] == "DECLINE"
    assert result["unified_cycle_state"] == "RISK_OFF"


def test_core_cycle_engine_falls_back_on_missing_data() -> None:
    result = CycleEngine().build_cycle_state({})

    assert result == {
        "liquidity_cycle": "UNKNOWN",
        "sentiment_cycle": "NEUTRAL",
        "industry_cycle": "MATURITY",
        "unified_cycle_state": "TRANSITION",
    }

