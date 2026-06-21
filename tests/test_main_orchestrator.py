"""Tests for the unified V12-V11 orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.main_orchestrator import MainOrchestrator
from core.v10_audit_engine import V10AuditEngine


@dataclass(frozen=True)
class DummyResult:
    code: str
    name: str
    theme: str
    strategic_score: float


def _audit_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v12_main_orchestrator_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_main_orchestrator_returns_unified_output() -> None:
    orchestrator = MainOrchestrator(
        [
            DummyResult("000977.SZ", "sample", "AI Computing", 85.0),
            DummyResult("600703.SH", "sample", "Advanced Materials", 72.0),
            DummyResult("002156.SZ", "sample", "Advanced Packaging", 80.0),
        ],
        audit_engine=V10AuditEngine(_audit_path()),
    )

    result = orchestrator.run({"confidence_bias": 0.0, "confidence_sensitivity": 1.0})

    assert "market_state" in result.__dict__
    assert "capital_state" in result.__dict__
    assert "decisions" in result.__dict__
    assert result.market_state["regime"] in {"BULL", "BEAR", "RANGE", "TRANSITION"}
    assert result.capital_state["risk_score"] >= 0.0
    assert isinstance(result.decisions, list)
