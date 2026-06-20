from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report
from src.quality.quality_gate import QualityGate


class RC1IntegrationTest(unittest.TestCase):
    def test_quality_gate_and_weekly_report_integration(self) -> None:
        report = QualityGate().run()
        self.assertTrue(report.rc1_ready)
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Quality Report", text)
        self.assertIn("RC1 Status", text)
        self.assertIn("Workflow Summary", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
