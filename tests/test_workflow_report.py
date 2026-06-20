from __future__ import annotations

import unittest

from src.agent_workflow.workflow_contract import WorkflowRun, WorkflowStep
from src.agent_workflow.workflow_report import WorkflowReport


class WorkflowReportTest(unittest.TestCase):
    def test_render_markdown(self) -> None:
        run = WorkflowRun(
            run_id="run1",
            period="TTM",
            symbols=["000001.SZ"],
            steps=[
                WorkflowStep(step_name="Provider Fetch", status="SUCCESS"),
                WorkflowStep(step_name="Strategic Score", status="FAILED", errors=["oops"]),
                WorkflowStep(step_name="Weekly Report", status="SKIPPED"),
            ],
            final_status="FAILED",
            summary="summary",
            warnings=["warn"],
            errors=["oops"],
        )
        text = WorkflowReport().render_markdown(run)
        self.assertIn("Workflow Status", text)
        self.assertIn("Successful Steps", text)
        self.assertIn("Failed Steps", text)
        self.assertIn("Skipped Steps", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
