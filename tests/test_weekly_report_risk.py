from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportRiskTest(unittest.TestCase):
    def test_weekly_report_contains_risk_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Risk Report", text)
        self.assertIn("Risk Warnings", text)
        self.assertIn("Risk Suggested Actions", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
