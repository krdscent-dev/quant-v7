"""Quality gate contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QualityCheck:
    check_name: str
    status: str
    message: str
    severity: str


@dataclass(frozen=True)
class QualityReport:
    timestamp: str
    checks: list[QualityCheck] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warnings: list[str] = field(default_factory=list)
    rc1_ready: bool = False

