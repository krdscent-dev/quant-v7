from __future__ import annotations

import unittest

from src.quality.quality_contract import QualityCheck, QualityReport
from src.quality.quality_report import QualityReportRenderer


class QualityReportTest(unittest.TestCase):
    def test_quality_report_creation(self) -> None:
        report = QualityReport(
            timestamp="2026-06-20T00:00:00+00:00",
            checks=[QualityCheck("core_modules", "PASS", "ok", "LOW")],
            passed_count=1,
            failed_count=0,
            warnings=[],
            rc1_ready=True,
        )
        payload = QualityReportRenderer().to_dict(report)
        self.assertEqual(payload["passed_count"], 1)
        self.assertTrue(payload["rc1_ready"])
        markdown = QualityReportRenderer().render_markdown(report)
        self.assertIn("Quality Gate", markdown)
        self.assertIn("core_modules", markdown)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
