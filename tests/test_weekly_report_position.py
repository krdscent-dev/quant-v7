from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportPositionTest(unittest.TestCase):
    def test_weekly_report_contains_position_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Position Snapshot", text)
        self.assertIn("Recommended Positions", text)
        self.assertIn("Cash Remaining", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
