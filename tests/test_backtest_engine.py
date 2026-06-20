from __future__ import annotations

import unittest

from src.backtest.backtest_contract import BacktestConfig
from src.backtest.backtest_engine import BacktestEngine


class BacktestEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BacktestEngine()

    def test_run_generates_result(self) -> None:
        price_data = {
            "000001.SZ": [
                {"date": "2026-06-01", "close": 10.0},
                {"date": "2026-06-02", "close": 10.5},
                {"date": "2026-06-03", "close": 11.0},
                {"date": "2026-06-04", "close": 11.5},
            ],
            "600000.SH": [
                {"date": "2026-06-01", "close": 20.0},
                {"date": "2026-06-02", "close": 20.4},
                {"date": "2026-06-03", "close": 20.8},
                {"date": "2026-06-04", "close": 21.2},
            ],
        }
        rebalance_plans = [
            {
                "date": "2026-06-01",
                "actions": [
                    {"symbol": "000001.SZ", "target_weight": 0.6, "delta_weight": 0.6},
                    {"symbol": "600000.SH", "target_weight": 0.4, "delta_weight": 0.4},
                ],
            }
        ]
        config = BacktestConfig(
            start_date="2026-06-01",
            end_date="2026-06-04",
            initial_cash=1_000_000.0,
            rebalance_frequency="W",
            transaction_cost=0.0,
            slippage=0.0,
        )
        result = self.engine.run(price_data, rebalance_plans, config)
        self.assertEqual(result.period, "2026-06-01->2026-06-04")
        self.assertGreater(len(result.equity_curve), 0)
        self.assertGreater(result.total_return, 0.0)
        self.assertGreater(result.annualized_return, 0.0)
        self.assertGreater(result.turnover, 0.0)
        self.assertIsInstance(result.warnings, list)

    def test_no_price_data_returns_warning(self) -> None:
        config = BacktestConfig(
            start_date="2026-06-01",
            end_date="2026-06-04",
            initial_cash=1_000_000.0,
            rebalance_frequency="W",
            transaction_cost=0.0,
            slippage=0.0,
        )
        result = self.engine.run({}, [], config)
        self.assertEqual(result.total_return, 0.0)
        self.assertIn("no_price_data", result.warnings)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
