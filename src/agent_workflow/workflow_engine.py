"""Workflow engine for orchestrating research steps."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
import uuid

from .workflow_contract import WorkflowRun, WorkflowStep


WorkflowHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class WorkflowEngine:
    def __init__(self) -> None:
        self._registry: dict[str, WorkflowHandler] = {}
        self._skip_after_failure = True
        self._force_skip_steps: set[str] = set()
        self._step_order: list[str] = []

    def register_step(self, step_name: str, handler: WorkflowHandler) -> None:
        self._registry[step_name] = handler
        if step_name not in self._step_order:
            self._step_order.append(step_name)

    def skip_step_on_failure(self, step_name: str | None = None) -> None:
        if step_name is None:
            self._skip_after_failure = True
            return
        self._force_skip_steps.add(step_name)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _summarize(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, Mapping):
            summary: dict[str, Any] = {}
            for key, value in payload.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    summary[key] = value
                elif isinstance(value, Mapping):
                    summary[key] = self._summarize(value)
                elif isinstance(value, list):
                    summary[key] = value[:5]
                else:
                    summary[key] = str(value)
            return summary
        return {"value": str(payload)}

    def run_step(self, step_name: str, context: Mapping[str, Any]) -> WorkflowStep:
        started_at = self._now()
        if step_name not in self._registry:
            return WorkflowStep(
                step_name=step_name,
                status="SKIPPED",
                started_at=started_at,
                ended_at=self._now(),
                input_summary=self._summarize(context),
                output_summary={"skipped": True, "reason": "step_not_registered"},
                warnings=["step_not_registered"],
                errors=[],
            )
        handler = self._registry[step_name]
        warnings: list[str] = []
        errors: list[str] = []
        output: Mapping[str, Any] | None = None
        try:
            output = handler(context)
            status = "SUCCESS"
            if isinstance(output, Mapping):
                warnings.extend(str(item) for item in output.get("warnings", []) if item)
                errors.extend(str(item) for item in output.get("errors", []) if item)
                if errors:
                    status = "FAILED"
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            status = "FAILED"
            errors.append(f"{step_name}: {exc}")
            output = {}
        ended_at = self._now()
        return WorkflowStep(
            step_name=step_name,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            input_summary=self._summarize(context),
            output_summary=self._summarize(output or {}),
            warnings=warnings,
            errors=errors,
        )

    def collect_warnings(self, workflow_run: WorkflowRun) -> list[str]:
        warnings = list(workflow_run.warnings)
        for step in workflow_run.steps:
            warnings.extend(step.warnings)
        return warnings

    def collect_errors(self, workflow_run: WorkflowRun) -> list[str]:
        errors = list(workflow_run.errors)
        for step in workflow_run.steps:
            errors.extend(step.errors)
        return errors

    def run_workflow(
        self,
        *,
        period: str,
        symbols: list[str],
        context: Mapping[str, Any] | None = None,
        step_order: list[str] | None = None,
    ) -> WorkflowRun:
        run_id = uuid.uuid4().hex
        base_context = dict(context or {})
        base_context.setdefault("period", period)
        base_context.setdefault("symbols", list(symbols))
        steps: list[WorkflowStep] = []
        warnings: list[str] = []
        errors: list[str] = []
        final_status = "SUCCESS"
        encountered_failure = False

        order = step_order or list(self._step_order)
        for step_name in order:
            if encountered_failure and (self._skip_after_failure or step_name in self._force_skip_steps):
                step = WorkflowStep(
                    step_name=step_name,
                    status="SKIPPED",
                    started_at=self._now(),
                    ended_at=self._now(),
                    input_summary=self._summarize(base_context),
                    output_summary={"skipped": True, "reason": "previous_failure"},
                    warnings=[],
                    errors=[],
                )
                steps.append(step)
                continue
            step = self.run_step(step_name, base_context)
            steps.append(step)
            warnings.extend(step.warnings)
            errors.extend(step.errors)
            if step.status == "FAILED":
                final_status = "FAILED"
                encountered_failure = True

        summary = (
            f"Workflow {run_id} completed with {len([s for s in steps if s.status == 'SUCCESS'])} successful steps, "
            f"{len([s for s in steps if s.status == 'FAILED'])} failed steps and "
            f"{len([s for s in steps if s.status == 'SKIPPED'])} skipped steps."
        )
        if final_status != "FAILED" and errors:
            final_status = "FAILED"
        return WorkflowRun(
            run_id=run_id,
            period=period,
            symbols=list(symbols),
            steps=steps,
            final_status=final_status,
            summary=summary,
            warnings=warnings,
            errors=errors,
        )

