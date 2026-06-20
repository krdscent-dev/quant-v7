from __future__ import annotations

import unittest

from src.audit.audit_contract import AuditCheck, AuditReport
from src.audit.audit_report import AuditReportRenderer


class AuditReportTest(unittest.TestCase):
    def test_audit_report_creation_and_rendering(self) -> None:
        report = AuditReport(
            timestamp="2026-06-21T00:00:00+00:00",
            checks=[
                AuditCheck(
                    category="GIT",
                    item="workspace_clean",
                    status="PASS",
                    severity="LOW",
                    message="workspace clean",
                )
            ],
            passed_count=1,
            warning_count=0,
            failed_count=0,
            overall_status="PASS",
            skill_readiness={
                "Skill A Data Analysis": "PARTIAL",
                "Skill B Graph Analysis": "READY",
            },
        )
        renderer = AuditReportRenderer()
        payload = renderer.to_dict(report)
        self.assertEqual(payload["passed_count"], 1)
        self.assertEqual(payload["overall_status"], "PASS")
        self.assertEqual(payload["skill_readiness"]["Skill B Graph Analysis"], "READY")

        markdown = renderer.render_markdown(report)
        self.assertIn("V9 RC1 Audit", markdown)
        self.assertIn("workspace_clean", markdown)
        self.assertIn("Skill B Graph Analysis", markdown)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
