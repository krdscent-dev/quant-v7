from __future__ import annotations

from core.v12_validation_engine import V12SystemValidationEngine


def _sample_history() -> list[dict[str, object]]:
    return [
        {
            "timestamp": "2026-06-21T09:30:00+00:00",
            "symbol": "000977.SZ",
            "future_return": 0.03,
            "market_data": {
                "close": 10.5,
                "high": 10.8,
                "low": 10.2,
                "volatility": 0.30,
                "sector_data": {"AI Computing": 120.0, "Advanced Packaging": 80.0},
                "stock_data": {"000977.SZ": {"volume": 80.0, "price_change": 0.05, "is_leader": True}},
            },
        },
        {
            "timestamp": "2026-06-22T09:30:00+00:00",
            "symbol": "688041.SH",
            "future_return": -0.02,
            "market_data": {
                "close": 20.0,
                "high": 20.4,
                "low": 19.4,
                "volatility": 0.05,
                "sector_data": {"AI Computing": 80.0, "Materials": 30.0},
                "stock_data": {"688041.SH": {"volume": 50.0, "price_change": -0.01, "is_leader": False}},
            },
        },
    ]


def test_v12_validation_engine_returns_structured_report() -> None:
    result = V12SystemValidationEngine().validate(_sample_history())

    assert set(result) == {
        "stability_score",
        "profit_score",
        "overfit_risk",
        "overall_score",
        "failure_points",
        "recommendation",
    }
    assert 0.0 <= result["stability_score"] <= 1.0
    assert 0.0 <= result["profit_score"] <= 1.0
    assert 0.0 <= result["overfit_risk"] <= 1.0
    assert 0.0 <= result["overall_score"] <= 1.0
    assert isinstance(result["failure_points"], list)
    assert isinstance(result["recommendation"], str)


def test_v12_validation_engine_handles_empty_history() -> None:
    result = V12SystemValidationEngine().validate([])

    assert result["stability_score"] == 0.0
    assert result["profit_score"] == 0.0
    assert result["overall_score"] == 0.0
    assert result["failure_points"]

