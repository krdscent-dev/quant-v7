from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportPortfolioTest(unittest.TestCase):
    def test_weekly_report_contains_portfolio_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Portfolio Snapshot", text)
        self.assertIn("Portfolio Ranking", text)
        self.assertIn("Core Candidates", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
