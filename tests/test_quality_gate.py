from __future__ import annotations

import unittest

from src.quality.quality_contract import QualityCheck
from src.quality.quality_gate import QualityGate


class QualityGateTest(unittest.TestCase):
    def test_quality_check_creation(self) -> None:
        check = QualityCheck(
            check_name="core_modules",
            status="PASS",
            message="ok",
            severity="LOW",
        )
        self.assertEqual(check.check_name, "core_modules")
        self.assertEqual(check.status, "PASS")

    def test_quality_gate_rc1_ready(self) -> None:
        report = QualityGate().run()
        self.assertTrue(report.rc1_ready)
        self.assertGreater(report.passed_count, 0)
        self.assertEqual(report.failed_count, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
