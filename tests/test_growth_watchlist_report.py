from __future__ import annotations

from pathlib import Path
import unittest

from core.weekly_pipeline import generate_weekly_dashboard_report


class GrowthWatchlistReportTest(unittest.TestCase):
    def test_growth_watchlist_sections_exist(self) -> None:
        path = generate_weekly_dashboard_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Growth Watch List", text)
        self.assertIn("AI算力", text)
        self.assertIn("新材料", text)
        self.assertIn("Theme", text)
        self.assertIn("Trend Tracking", text)

    def test_growth_watchlist_state_written(self) -> None:
        generate_weekly_dashboard_report()
        state_path = Path.cwd() / "data" / "processed" / "growth_watchlist_state.yaml"
        self.assertTrue(state_path.exists())
        state_text = state_path.read_text(encoding="utf-8")
        self.assertIn("AI算力", state_text)
        self.assertIn("last_updated", state_text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
