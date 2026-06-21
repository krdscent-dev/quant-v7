from __future__ import annotations

from core.v12_5_capital_control_engine import CapitalControlEngine, build_capital_control


def test_core_capital_control_aggressive_mode() -> None:
    result = build_capital_control(
        {
            "regime": "BULL",
            "flow_strength": 0.85,
            "narrative_strength": 0.82,
            "cycle_state": "RISK_ON",
        },
        {"current_exposure": 0.10, "max_drawdown": 0.05},
    )

    assert result["risk_mode"] == "AGGRESSIVE"
    assert 1.2 <= result["position_multiplier"] <= 1.5
    assert 0.0 <= result["risk_budget"] <= 1.0
    assert result["exposure_limit"] == 1.0
    assert result["leverage_adjustment"] == 1.2


def test_core_capital_control_defensive_mode() -> None:
    result = CapitalControlEngine().build_capital_control(
        {
            "regime": "BEAR",
            "flow_strength": 0.30,
            "narrative_strength": 0.20,
            "cycle_state": "RISK_OFF",
        },
        {"current_exposure": 0.30, "max_drawdown": 0.20},
    )

    assert result["risk_mode"] == "DEFENSIVE"
    assert 0.4 <= result["position_multiplier"] <= 0.7
    assert result["exposure_limit"] == 0.5
    assert result["leverage_adjustment"] == 0.5


def test_core_capital_control_fallback() -> None:
    result = CapitalControlEngine().build_capital_control({})

    assert result == {
        "position_multiplier": 1.0,
        "risk_budget": 0.5,
        "exposure_limit": 1.0,
        "leverage_adjustment": 1.0,
        "risk_mode": "NEUTRAL",
    }

