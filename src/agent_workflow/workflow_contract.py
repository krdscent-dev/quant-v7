"""Workflow contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


WORKFLOW_STATUSES = ("PENDING", "RUNNING", "SUCCESS", "FAILED", "SKIPPED")


@dataclass(frozen=True)
class WorkflowStep:
    step_name: str
    status: str
    started_at: str = ""
    ended_at: str = ""
    input_summary: Mapping[str, Any] = field(default_factory=dict)
    output_summary: Mapping[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    period: str
    symbols: list[str]
    steps: list[WorkflowStep]
    final_status: str
    summary: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

