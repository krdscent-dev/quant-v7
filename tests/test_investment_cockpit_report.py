from __future__ import annotations

import os
import unittest
from pathlib import Path

from core.weekly_pipeline import generate_investment_cockpit_report


class InvestmentCockpitReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_fast_mode = os.environ.get("CODEX_TEST_FAST")
        os.environ["CODEX_TEST_FAST"] = "1"

    def tearDown(self) -> None:
        if self._previous_fast_mode is None:
            os.environ.pop("CODEX_TEST_FAST", None)
        else:
            os.environ["CODEX_TEST_FAST"] = self._previous_fast_mode

    def test_cockpit_report_sections_exist(self) -> None:
        path = generate_investment_cockpit_report()
        self.assertTrue(path.name.startswith("V9_3_investment_cockpit_"))
        text = path.read_text(encoding="utf-8")
        expected_sections = [
            "00 Market Regime Summary",
            "01 Sector Summary",
            "02 Theme Ranking",
            "03 Theme Momentum",
            "04 Growth Watch List",
            "05 Valuation Guard",
            "06 Score Interpretation",
            "07 Candidate Cards 2.0",
            "08 Position Recommendation Engine",
            "09 Confidence Engine",
            "10 Watchlist Lifecycle",
            "11 Scenario Engine",
            "12 Final Decision Engine",
        ]
        for section in expected_sections:
            self.assertIn(section, text)
        self.assertIn("AI算力", text)
        self.assertIn("新材料", text)
        self.assertIn("价格区间数据不足", text)

    def test_cockpit_visuals_or_log_exist(self) -> None:
        generate_investment_cockpit_report()
        asset_dir = Path.cwd() / "reports" / "weekly" / "assets"
        expected_assets = [
            asset_dir / "sector_ranking.png",
            asset_dir / "theme_momentum.png",
            asset_dir / "portfolio_dashboard.png",
            asset_dir / "valuation_guard.png",
        ]
        log_path = Path.cwd() / "logs" / "investment_cockpit_visualization_error.log"
        has_asset = any(path.exists() for path in expected_assets)
        self.assertTrue(has_asset or log_path.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
