from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report


class WeeklyReportKnowledgeBaseTest(unittest.TestCase):
    def test_weekly_report_contains_knowledge_base_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Knowledge Base Records", text)
        self.assertIn("Historical Score Changes", text)
        self.assertIn("Historical Decision Changes", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
