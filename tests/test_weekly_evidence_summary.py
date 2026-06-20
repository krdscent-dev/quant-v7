from __future__ import annotations

import unittest

from core.research_engine import run_research_pipeline


class WeeklyEvidenceSummaryTest(unittest.TestCase):
    def test_pipeline_returns_evidence_summary(self) -> None:
        result = run_research_pipeline("000001.SZ")
        self.assertIn("evidence_summary", result)
        self.assertIn("overall_confidence", result["evidence_summary"])

