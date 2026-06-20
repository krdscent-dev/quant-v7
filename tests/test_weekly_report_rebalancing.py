from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportRebalancingTest(unittest.TestCase):
    def test_weekly_report_contains_rebalance_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Rebalance Plan", text)
        self.assertIn("Rebalance Actions", text)
        self.assertIn("Buy List", text)
        self.assertIn("Hold List", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
