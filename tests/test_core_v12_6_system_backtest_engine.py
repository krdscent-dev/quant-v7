from __future__ import annotations

from tempfile import TemporaryDirectory

from analytics.v12_6_attribution_engine import V126AttributionEngine
from core.v12_6_system_backtest_engine import V126SystemBacktestEngine
from logs.v12_6_trade_logger import V126TradeLogger


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
                "sector_data": {
                    "AI Computing": 120.0,
                    "Advanced Packaging": 80.0,
                },
                "stock_data": {
                    "000977.SZ": {"volume": 80.0, "price_change": 0.05, "is_leader": True},
                    "688041.SH": {"volume": 20.0, "price_change": 0.02, "is_leader": False},
                },
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
                "sector_data": {
                    "AI Computing": 80.0,
                    "Materials": 30.0,
                },
                "stock_data": {
                    "000977.SZ": {"volume": 50.0, "price_change": 0.03, "is_leader": True},
                    "688041.SH": {"volume": 50.0, "price_change": -0.01, "is_leader": False},
                },
            },
        },
    ]


def test_core_v126_system_backtest_generates_equity_curve_and_attribution() -> None:
    with TemporaryDirectory() as temp_dir:
        logger = V126TradeLogger(f"{temp_dir}/trade_log.jsonl")
        engine = V126SystemBacktestEngine(
            trade_logger=logger,
            attribution_engine=V126AttributionEngine(),
        )
        result = engine.simulate(_sample_history())

        assert result.equity_curve
        assert result.trade_log
        assert set(result.attribution) == {"market_structure", "capital_control", "execution"}
        assert result.total_return != 0.0
        assert 0.0 <= result.win_rate <= 1.0
        assert result.max_drawdown >= 0.0
        assert logger.read_trades()


def test_core_v126_system_backtest_handles_incomplete_data() -> None:
    with TemporaryDirectory() as temp_dir:
        logger = V126TradeLogger(f"{temp_dir}/trade_log.jsonl")
        engine = V126SystemBacktestEngine(trade_logger=logger)
        result = engine.simulate(
            [
                {
                    "timestamp": "2026-06-21T09:30:00+00:00",
                    "future_return": 0.0,
                    "market_data": {},
                }
            ]
        )

        assert result.equity_curve
        assert result.trade_log
        assert result.warnings or result.total_return == 0.0

