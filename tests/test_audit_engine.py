from __future__ import annotations

import unittest

from core.weekly_pipeline import generate_weekly_report
from src.audit.audit_engine import AuditEngine


class AuditEngineTest(unittest.TestCase):
    def test_audit_engine_runs_and_covers_all_categories(self) -> None:
        report = AuditEngine().run()
        categories = {item.category for item in report.checks}
        self.assertTrue({"GIT", "ARCHITECTURE", "TEST", "DOCUMENTATION", "CONFIG", "SKILL_READINESS"}.issubset(categories))
        self.assertIn(report.overall_status, {"PASS", "WARNING", "FAIL"})
        self.assertIn("Skill A Data Analysis", report.skill_readiness)
        self.assertIn("Skill D Visualization", report.skill_readiness)

    def test_weekly_report_includes_audit_sections(self) -> None:
        path = generate_weekly_report()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Audit Report", text)
        self.assertIn("Skill Readiness", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
