from __future__ import annotations

import unittest

from src.agent_workflow.workflow_engine import WorkflowEngine


class WorkflowEngineTest(unittest.TestCase):
    def test_register_and_run_success(self) -> None:
        engine = WorkflowEngine()

        def step_a(context):
            return {"ok": True, "warnings": ["soft_warning"]}

        engine.register_step("Step A", step_a)
        run = engine.run_workflow(period="TTM", symbols=["000001.SZ"], context={"foo": "bar"}, step_order=["Step A"])
        self.assertEqual(len(run.steps), 1)
        self.assertEqual(run.steps[0].status, "SUCCESS")
        self.assertIn("soft_warning", run.steps[0].warnings)

    def test_run_failure_and_skip(self) -> None:
        engine = WorkflowEngine()

        def step_a(context):
            return {"ok": True}

        def step_b(context):
            raise RuntimeError("boom")

        def step_c(context):
            return {"ok": True}

        engine.register_step("Step A", step_a)
        engine.register_step("Step B", step_b)
        engine.register_step("Step C", step_c)
        engine.skip_step_on_failure("Step C")
        run = engine.run_workflow(period="TTM", symbols=["000001.SZ"], context={}, step_order=["Step A", "Step B", "Step C"])
        statuses = {step.step_name: step.status for step in run.steps}
        self.assertEqual(statuses["Step B"], "FAILED")
        self.assertEqual(statuses["Step C"], "SKIPPED")
        self.assertIn("boom", " ".join(run.errors))

    def test_collect_warnings_and_errors(self) -> None:
        engine = WorkflowEngine()

        def step_a(context):
            return {"warnings": ["warn1"], "errors": ["err1"]}

        engine.register_step("Step A", step_a)
        run = engine.run_workflow(period="TTM", symbols=["000001.SZ"], context={}, step_order=["Step A"])
        self.assertIn("warn1", engine.collect_warnings(run))
        self.assertIn("err1", engine.collect_errors(run))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
