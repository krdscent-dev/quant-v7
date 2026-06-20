from __future__ import annotations

import unittest

from core.weekly_pipeline import build_weekly_report_data
from src.backtest.backtest_contract import BacktestResult
from src.exports.tabular_exporter import TabularExporter
from src.portfolio.portfolio_contract import PortfolioCandidate, PortfolioScore, PortfolioSnapshot
from src.risk.risk_contract import PortfolioRiskReport, RiskCheckResult


class TabularExporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exporter = TabularExporter()

    def test_dict_export(self) -> None:
        snapshot = PortfolioSnapshot(
            period="TTM",
            candidates=[
                PortfolioCandidate(
                    symbol="000001.SZ",
                    period="TTM",
                    strategic_score=88.0,
                    final_decision="BUY",
                    confidence_score=0.9,
                    risk_score=0.2,
                )
            ],
            ranked_candidates=[
                PortfolioScore(
                    symbol="000001.SZ",
                    total_score=90.0,
                    strategic_score=88.0,
                    confidence_score=0.9,
                    risk_adjusted_score=70.4,
                    rank=1,
                    bucket="CORE",
                )
            ],
            core_candidates=[],
            satellite_candidates=[],
            watchlist_candidates=[],
            excluded_candidates=[],
            summary="summary",
            warnings=[],
            portfolio_summary="portfolio summary",
        )
        payload = self.exporter.to_dict(snapshot)
        self.assertEqual(payload["period"], "TTM")
        self.assertIn("candidates", payload)

    def test_records_export(self) -> None:
        snapshot = PortfolioSnapshot(
            period="TTM",
            candidates=[
                PortfolioCandidate(
                    symbol="000001.SZ",
                    period="TTM",
                    strategic_score=88.0,
                    final_decision="BUY",
                    confidence_score=0.9,
                    risk_score=0.2,
                )
            ],
            ranked_candidates=[],
            core_candidates=[],
            satellite_candidates=[],
            watchlist_candidates=[],
            excluded_candidates=[],
            summary="summary",
            warnings=[],
            portfolio_summary="portfolio summary",
        )
        records = self.exporter.to_records(snapshot)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "000001.SZ")

    def test_records_export_for_reports(self) -> None:
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
        records = self.exporter.to_records(result)
        self.assertEqual(records[0]["date"], "2026-06-21")

        report = PortfolioRiskReport(
            period="TTM",
            total_risk_score=0.42,
            risk_level="MEDIUM",
            checks=[RiskCheckResult("position", True, "LOW", "ok")],
            warnings=[],
            suggested_actions=[],
        )
        report_records = self.exporter.to_records(report)
        self.assertEqual(report_records[0]["check_name"], "position")

    def test_weekly_report_records(self) -> None:
        rows = build_weekly_report_data()
        records = self.exporter.to_records(rows)
        self.assertGreater(len(records), 0)
        self.assertIn("company_code", records[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
