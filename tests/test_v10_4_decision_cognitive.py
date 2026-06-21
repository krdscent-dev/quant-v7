"""Tests for V10.4 cognitive graph decision integration."""

from __future__ import annotations

from core.decision_engine import DecisionEngine


def test_strong_causal_chain_without_blocking_bottleneck_supports_add() -> None:
    decision = DecisionEngine().decide(
        symbol="000001.SZ",
        score=45.0,
        regime="STRUCTURAL",
        confidence=0.70,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.80,
            "sector_leader_flag": True,
            "sector_rank": 1,
            "causal_chain": [
                "AI Computing",
                "AI CapEx Expansion",
                "Supply Validation",
                "Order Confirmation",
                "Revenue Conversion",
            ],
            "bottleneck_node": "NONE",
            "chain_strength": "STRONG",
        },
    )

    assert decision["action"] == "ADD"
    assert decision["causal_chain"][0] == "AI Computing"
    assert decision["bottleneck_node"] == "NONE"


def test_strong_causal_chain_with_bottleneck_caps_to_hold_or_small_add() -> None:
    decision = DecisionEngine().decide(
        symbol="000002.SZ",
        score=45.0,
        regime="BEAR",
        confidence=0.70,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.60,
            "sector_leader_flag": False,
            "sector_rank": 2,
            "causal_chain": [
                "AI Computing",
                "AI CapEx Expansion",
                "Supply Validation",
                "Order Confirmation",
            ],
            "bottleneck_node": "Supply Validation",
            "chain_strength": "STRONG",
        },
    )

    assert decision["action"] == "HOLD"
    assert decision["bottleneck_node"] == "Supply Validation"


def test_no_causal_structure_defaults_to_observe_not_invalidate() -> None:
    decision = DecisionEngine().decide(
        symbol="000003.SZ",
        score=40.0,
        regime="BEAR",
        confidence=0.60,
        context={
            "sector": "UNKNOWN",
            "causal_chain": [],
            "bottleneck_node": "NONE",
            "chain_strength": "NONE",
        },
    )

    assert decision["action"] == "OBSERVE"
    assert decision["action"] != "INVALIDATE"
