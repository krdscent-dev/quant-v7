"""Tests for V12.1 deterministic market structure engine."""

from __future__ import annotations

from market.v12_1_structure_engine import V121MarketStructureEngine, analyze_market_structure


def test_v121_classifies_bull_structure() -> None:
    result = analyze_market_structure(trend_score=0.8, volatility=0.2, price_momentum=0.7)

    assert result.regime == "BULL"
    assert result.volatility_state == "LOW"
    assert result.structure_strength > 0.7


def test_v121_classifies_bear_structure() -> None:
    result = analyze_market_structure(trend_score=0.2, volatility=0.8, price_momentum=0.1)

    assert result.regime == "BEAR"
    assert result.volatility_state == "HIGH"


def test_v121_classifies_range_structure() -> None:
    result = analyze_market_structure(trend_score=0.5, volatility=0.4, price_momentum=0.4)

    assert result.regime == "RANGE"
    assert result.volatility_state == "STABLE"


def test_v121_classifies_transition_when_trend_changes_fast() -> None:
    result = analyze_market_structure(trend_score=0.2, volatility=0.4, price_momentum=0.8)

    assert result.regime == "TRANSITION"
    assert "diverging" in result.reason


def test_v121_class_wrapper_returns_structured_object() -> None:
    result = V121MarketStructureEngine().analyze_market_structure(
        trend_score=0.7,
        volatility=0.3,
        price_momentum=0.6,
    )

    assert result.regime == "BULL"
    assert hasattr(result, "structure_strength")
