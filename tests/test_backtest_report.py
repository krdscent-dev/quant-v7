from __future__ import annotations

import unittest

from src.backtest.backtest_contract import BacktestConfig, BacktestResult
from src.backtest.backtest_report import BacktestReport


class BacktestReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.report = BacktestReport()

    def test_render_markdown(self) -> None:
        config = BacktestConfig(
            start_date="2026-06-01",
            end_date="2026-06-04",
            initial_cash=1_000_000.0,
            rebalance_frequency="W",
            transaction_cost=0.0,
            slippage=0.0,
        )
        result = BacktestResult(
            period="2026-06-01->2026-06-04",
            equity_curve=[{"date": "2026-06-01", "equity": 1000000.0, "return": 0.0}],
            total_return=0.05,
            annualized_return=0.10,
            max_drawdown=0.02,
            volatility=0.03,
            sharpe_ratio=1.50,
            turnover=0.20,
            win_rate=0.75,
            warnings=[],
        )
        text = self.report.render_markdown(result, config, rebalance_count=1)
        self.assertIn("Backtest Result", text)
        self.assertIn("Backtest Summary", text)
        self.assertIn("Backtest Metrics", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
