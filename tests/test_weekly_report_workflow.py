from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportWorkflowTest(unittest.TestCase):
    def test_weekly_report_contains_workflow_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Workflow Summary", text)
        self.assertIn("Workflow Status", text)
        self.assertIn("Workflow Warnings", text)
        self.assertIn("Workflow Errors", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
