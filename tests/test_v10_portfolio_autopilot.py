"""Tests for V10.5 portfolio autopilot constraints."""

from __future__ import annotations

from core.v10_portfolio_autopilot import V10PortfolioAutopilot


def test_calculate_exposure_by_sector() -> None:
    autopilot = V10PortfolioAutopilot()

    exposure = autopilot.calculate_exposure(
        [
            {"symbol": "A", "sector": "AI Computing", "action": "SMALL_ADD"},
            {"symbol": "B", "sector": "AI Computing", "action": "OBSERVE"},
            {"symbol": "C", "sector": "Advanced Packaging", "action": "SMALL_ADD"},
        ]
    )

    assert exposure["AI Computing"] > exposure["Advanced Packaging"]
    assert round(sum(exposure.values()), 2) == 1.0


def test_risk_score_increases_with_concentration() -> None:
    autopilot = V10PortfolioAutopilot()

    risk = autopilot.risk_score({"AI Computing": 0.80, "Advanced Packaging": 0.20})

    assert risk > 0.40


def test_rebalance_signal_marks_over_and_under_exposure() -> None:
    autopilot = V10PortfolioAutopilot()

    signals = autopilot.rebalance_signal(
        {"AI Computing": 0.40, "Advanced Packaging": 0.05, "Domestic": 0.20}
    )

    assert signals["AI Computing"] == "REDUCE"
    assert signals["Advanced Packaging"] == "INCREASE"
    assert signals["Domestic"] == "NEUTRAL"


def test_apply_constraints_reduces_overexposed_sector() -> None:
    autopilot = V10PortfolioAutopilot()

    decisions = autopilot.apply_constraints(
        [
            {"symbol": "A", "sector": "AI Computing", "action": "SMALL_ADD", "confidence": 0.7},
            {"symbol": "B", "sector": "AI Computing", "action": "SMALL_ADD", "confidence": 0.7},
            {"symbol": "C", "sector": "Advanced Packaging", "action": "OBSERVE", "confidence": 0.7},
        ]
    )

    ai_actions = [row["action"] for row in decisions if row["sector"] == "AI Computing"]

    assert "REDUCE" in ai_actions
    assert all("portfolio_exposure" in row for row in decisions)
    assert all("risk_score" in row for row in decisions)


def test_high_portfolio_risk_shifts_add_to_hold() -> None:
    autopilot = V10PortfolioAutopilot()

    action, reason = autopilot._final_action(
        action="SMALL_ADD",
        sector_exposure=0.20,
        portfolio_risk=0.80,
        signal="NEUTRAL",
    )

    assert action == "HOLD"
    assert "Portfolio risk" in reason
