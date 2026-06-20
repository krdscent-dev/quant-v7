from __future__ import annotations

import unittest

from src.backtest.backtest_metrics import BacktestMetrics


class BacktestMetricsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = BacktestMetrics()

    def test_total_return(self) -> None:
        self.assertAlmostEqual(self.metrics.total_return([100.0, 110.0, 121.0]), 0.21, places=6)

    def test_annualized_return(self) -> None:
        curve = [100.0] + [100.0] * 251 + [110.0]
        self.assertAlmostEqual(self.metrics.annualized_return(curve), 0.10, places=2)

    def test_max_drawdown(self) -> None:
        self.assertAlmostEqual(self.metrics.max_drawdown([100.0, 120.0, 90.0, 95.0]), 0.25, places=6)

    def test_volatility(self) -> None:
        vol = self.metrics.volatility([0.01, -0.01, 0.01, -0.01])
        self.assertGreater(vol, 0.0)

    def test_sharpe_ratio(self) -> None:
        sharpe = self.metrics.sharpe_ratio([0.01, 0.01, 0.01, 0.01])
        self.assertEqual(sharpe, 0.0)

    def test_turnover(self) -> None:
        self.assertAlmostEqual(self.metrics.turnover([0.1, 0.2]), 0.15, places=6)

    def test_win_rate(self) -> None:
        self.assertAlmostEqual(self.metrics.win_rate([0.1, -0.1, 0.2, 0.0]), 0.5, places=6)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
