"""Audit contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuditCheck:
    category: str
    item: str
    status: str
    severity: str
    message: str


@dataclass(frozen=True)
class AuditReport:
    timestamp: str
    checks: list[AuditCheck] = field(default_factory=list)
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    overall_status: str = "PASS"
    skill_readiness: dict[str, str] = field(default_factory=dict)

