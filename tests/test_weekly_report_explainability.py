from __future__ import annotations

import unittest

from core.research_engine import run_research_pipeline


class WeeklyReportExplainabilityTest(unittest.TestCase):
    def test_weekly_pipeline_returns_explanations(self) -> None:
        result = run_research_pipeline("000001.SZ")
        self.assertIn("score_explanation", result)
        self.assertIn("decision_explanation", result)

