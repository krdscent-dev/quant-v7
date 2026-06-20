from __future__ import annotations

import unittest

from src.backtest.backtest_contract import BacktestResult
from src.exports.metrics_exporter import MetricsExporter
from src.risk.risk_contract import PortfolioRiskReport, RiskCheckResult


class MetricsExporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exporter = MetricsExporter()

    def test_metrics_export_for_backtest(self) -> None:
        result = BacktestResult(
            period="TTM",
            equity_curve=[{"date": "2026-06-21", "equity": 100.0}],
            total_return=0.12,
            annualized_return=0.20,
            max_drawdown=0.05,
            volatility=0.10,
            sharpe_ratio=1.2,
            turnover=0.3,
            win_rate=0.6,
            warnings=[],
        )
        metrics = self.exporter.to_dict(result)
        self.assertAlmostEqual(metrics["total_return"], 0.12)
        self.assertAlmostEqual(metrics["sharpe_ratio"], 1.2)

    def test_metrics_export_for_risk_report(self) -> None:
        report = PortfolioRiskReport(
            period="TTM",
            total_risk_score=0.42,
            risk_level="MEDIUM",
            checks=[RiskCheckResult("position", True, "LOW", "ok")],
            warnings=[],
            suggested_actions=[],
        )
        metrics = self.exporter.to_dict(report)
        self.assertAlmostEqual(metrics["total_risk_score"], 0.42)
        self.assertEqual(self.exporter.to_records(report)[0]["total_risk_score"], 0.42)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
