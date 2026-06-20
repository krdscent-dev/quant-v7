from __future__ import annotations

import unittest

from src.agent_workflow.workflow_contract import WorkflowRun, WorkflowStep


class WorkflowContractTest(unittest.TestCase):
    def test_workflow_step_creation(self) -> None:
        step = WorkflowStep(
            step_name="Provider Fetch",
            status="SUCCESS",
            started_at="2026-06-20T00:00:00+00:00",
            ended_at="2026-06-20T00:00:01+00:00",
            input_summary={"symbols": ["000001.SZ"]},
            output_summary={"provider_count": 3},
            warnings=["none"],
            errors=[],
        )
        self.assertEqual(step.step_name, "Provider Fetch")
        self.assertEqual(step.status, "SUCCESS")

    def test_workflow_run_creation(self) -> None:
        run = WorkflowRun(
            run_id="run1",
            period="TTM",
            symbols=["000001.SZ"],
            steps=[],
            final_status="SUCCESS",
            summary="ok",
            warnings=[],
            errors=[],
        )
        self.assertEqual(run.run_id, "run1")
        self.assertEqual(run.final_status, "SUCCESS")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
