from __future__ import annotations

from core.v12_1_structure_engine import MarketStructureEngine


def test_core_structure_engine_bull_classification() -> None:
    engine = MarketStructureEngine()
    result = engine.analyze_market_structure(
        {
            "close": 10.5,
            "high": 10.7,
            "low": 10.45,
            "historical_close_series": [9.8, 10.0, 10.1, 10.3, 10.4, 10.45, 10.5],
        }
    )

    assert result["regime"] in {"BULL", "RANGE", "TRANSITION"}
    assert 0.0 <= result["trend_score"] <= 1.0
    assert result["volatility_state"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0.0 <= result["structure_strength"] <= 1.0


def test_core_structure_engine_falls_back_without_history() -> None:
    engine = MarketStructureEngine()
    result = engine.analyze_market_structure({"close": 10.0, "high": 10.1, "low": 9.9})

    assert result["regime"] in {"BULL", "BEAR", "RANGE", "TRANSITION"}
    assert 0.0 <= result["trend_score"] <= 1.0
    assert result["volatility_state"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0.0 <= result["structure_strength"] <= 1.0

