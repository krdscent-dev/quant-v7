"""Tests for V12.5 capital control layer."""

from __future__ import annotations

from core.v12_5_capital_control import V125CapitalControlEngine


def test_v125_builds_capital_state_from_decisions() -> None:
    engine = V125CapitalControlEngine()
    decisions = [
        {"symbol": "000977.SZ", "sector": "AI Computing", "action": "ADD"},
        {"symbol": "600703.SH", "sector": "Advanced Materials", "action": "HOLD"},
        {"symbol": "002156.SZ", "sector": "Advanced Packaging", "action": "SMALL_ADD"},
    ]

    state = engine.build_capital_state(decisions, cycle_state={"risk_appetite": "RISING"})

    assert state.exposure
    assert 0.0 <= state.risk_score <= 1.0
    assert state.capital_bias in {"EXPANSIVE", "BALANCED", "DEFENSIVE"}
    assert state.allocation_ceiling in {0.05, 0.10, 0.15}


def test_v125_applies_constraints_without_stock_selection() -> None:
    engine = V125CapitalControlEngine()
    adjusted = engine.apply_constraints(
        [
            {"symbol": "000977.SZ", "sector": "AI Computing", "action": "ADD"},
            {"symbol": "600703.SH", "sector": "Advanced Materials", "action": "HOLD"},
        ]
    )

    assert len(adjusted) == 2
    assert all("portfolio_exposure" in row for row in adjusted)
    assert all("rebalance_signal" in row for row in adjusted)
