"""Tests for V11.1 conflict resolution and arbitration."""

from __future__ import annotations

from agents.conflict_resolver import ConflictResolver
from agents.decision_arbitrator import DecisionArbitrator


def test_alpha_buy_risk_reduce_triggers_conflict() -> None:
    resolver = ConflictResolver()

    conflicts = resolver.detect_conflicts(
        {
            "AlphaAgent": "ADD",
            "RiskAgent": "REDUCE",
            "MacroAgent": "HOLD",
            "SectorAgent": "HOLD",
            "PortfolioAgent": "ADD",
        }
    )

    assert conflicts


def test_weighted_arbitration_prioritizes_risk() -> None:
    result = DecisionArbitrator().arbitrate(
        {
            "AlphaAgent": {"suggested_action": "ADD"},
            "RiskAgent": {"risk_action": "REDUCE", "risk_score": 0.8},
            "MacroAgent": {"macro_regime": "STRUCTURAL"},
            "SectorAgent": {"sector_strength": 0.9},
            "PortfolioAgent": {"final_action": "ADD"},
        }
    )

    assert result["conflict_detected"] is True
    assert result["final_decision"] in {"HOLD", "REDUCE"}
    assert result["final_decision"] != "ADD"


def test_unresolved_conflict_falls_back_to_hold() -> None:
    result = DecisionArbitrator().arbitrate(
        {
            "AlphaAgent": {"suggested_action": "ADD"},
            "RiskAgent": {"risk_action": "REDUCE", "risk_score": 0.2},
            "MacroAgent": {"macro_regime": "STRUCTURAL"},
            "SectorAgent": {"sector_strength": 0.9},
            "PortfolioAgent": {"final_action": "ADD"},
        }
    )

    assert result["conflict_detected"] is True
    assert "arbitration_reason" in result


def test_no_conflict_keeps_constructive_decision() -> None:
    result = DecisionArbitrator().arbitrate(
        {
            "AlphaAgent": {"suggested_action": "ADD"},
            "RiskAgent": {"risk_action": "ALLOW", "risk_score": 0.1},
            "MacroAgent": {"macro_regime": "STRUCTURAL"},
            "SectorAgent": {"sector_strength": 0.9},
            "PortfolioAgent": {"final_action": "ADD"},
        }
    )

    assert result["conflict_detected"] is False
    assert result["final_decision"] in {"SMALL_ADD", "ADD"}
