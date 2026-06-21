"""Tests for V10.3 sector-aware decisions."""

from __future__ import annotations

from core.decision_engine import DecisionEngine


def test_strong_sector_leader_gets_leader_bias_before_bear_sizing() -> None:
    decision = DecisionEngine().decide(
        symbol="000001.SZ",
        score=45.0,
        regime="BEAR",
        confidence=0.70,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.90,
            "sector_leader_flag": True,
            "sector_rank": 1,
            "theme": "AI算力",
            "theme_tags": ["AI算力", "AI Computing"],
        },
    )

    assert decision["action"] == "SMALL_ADD"
    assert decision["sector"] == "AI Computing"
    assert decision["sector_strength"] == 0.90
    assert decision["leader_flag"] is True


def test_second_ranked_strong_sector_name_is_hold() -> None:
    decision = DecisionEngine().decide(
        symbol="000002.SZ",
        score=45.0,
        regime="STRUCTURAL",
        confidence=0.70,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.90,
            "sector_leader_flag": False,
            "sector_rank": 2,
        },
    )

    assert decision["action"] == "HOLD"
    assert decision["leader_flag"] is False


def test_weak_sector_does_not_freeze_to_invalidate() -> None:
    decision = DecisionEngine().decide(
        symbol="000003.SZ",
        score=65.0,
        regime="BEAR",
        confidence=0.60,
        context={
            "sector": "Weak Sector",
            "sector_strength": 0.30,
            "sector_leader_flag": False,
            "sector_rank": 3,
        },
    )

    assert decision["action"] in {"OBSERVE", "REDUCE"}
    assert decision["action"] != "INVALIDATE"
