"""Workflow report helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .workflow_contract import WorkflowRun


class WorkflowReport:
    def to_dict(self, workflow_run: WorkflowRun) -> dict[str, Any]:
        successful_steps = [step.step_name for step in workflow_run.steps if step.status == "SUCCESS"]
        failed_steps = [step.step_name for step in workflow_run.steps if step.status == "FAILED"]
        skipped_steps = [step.step_name for step in workflow_run.steps if step.status == "SKIPPED"]
        return {
            "run_id": workflow_run.run_id,
            "period": workflow_run.period,
            "symbols": list(workflow_run.symbols),
            "final_status": workflow_run.final_status,
            "summary": workflow_run.summary,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "warning_summary": list(workflow_run.warnings),
            "error_summary": list(workflow_run.errors),
            "steps": [asdict(step) for step in workflow_run.steps],
        }

    def render_markdown(self, workflow_run: WorkflowRun) -> str:
        summary = self.to_dict(workflow_run)
        lines: list[str] = []
        lines.append("## 43. Workflow Status")
        lines.append(f"- final_status: {summary['final_status']}")
        lines.append(f"- run_id: {summary['run_id']}")
        lines.append("")
        lines.append("## 44. Successful Steps")
        if summary["successful_steps"]:
            for item in summary["successful_steps"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("## 45. Failed Steps")
        if summary["failed_steps"]:
            for item in summary["failed_steps"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("## 46. Skipped Steps")
        if summary["skipped_steps"]:
            for item in summary["skipped_steps"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("## 47. Warning Summary")
        if summary["warning_summary"]:
            for item in summary["warning_summary"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("## 48. Error Summary")
        if summary["error_summary"]:
            for item in summary["error_summary"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        lines.append("")
        return "\n".join(lines)

