from __future__ import annotations

from pathlib import Path
import unittest

from src.audit.audit_engine import AuditEngine


class FreezeReadinessTest(unittest.TestCase):
    def test_freeze_readiness_inputs(self) -> None:
        base_dir = Path.cwd()
        for rel_path in [
            "docs/architecture/Round28.md",
            "docs/architecture/Round29.md",
            "docs/architecture/Round40.md",
            "requirements.txt",
        ]:
            self.assertTrue((base_dir / rel_path).exists(), rel_path)

        report = AuditEngine(base_dir).run()
        self.assertEqual(report.failed_count, 0)
        self.assertEqual(report.skill_readiness["Skill A Data Analysis"], "READY")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
