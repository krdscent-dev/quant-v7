"""Tests for V10.7 audit and governance system."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.execution_engine import ExecutionEngine
from core.human_approval_engine import HumanApprovalEngine
from core.proposal_schema import create_proposal
from core.v10_audit_engine import V10AuditEngine
from core.v10_change_tracker import V10ChangeTracker
from core.v10_governance import V10Governance
from core.v10_proposal_engine import V10ProposalEngine
from core.v10_self_learning_engine import V10SelfLearningEngine
from core.v10_version_control import V10VersionControl


def _path(name: str) -> Path:
    path = Path.cwd() / "reports" / "cache" / f"{name}_{uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_audit_engine_logs_event() -> None:
    audit_path = _path("audit").with_suffix(".jsonl")
    audit = V10AuditEngine(audit_path)

    audit.log_event("TEST_EVENT", {"ok": True})

    records = audit.read_recent()
    assert records[-1]["event_type"] == "TEST_EVENT"
    assert records[-1]["payload"]["ok"] is True


def test_version_control_snapshot_and_rollback() -> None:
    state_path = _path("state")
    state_path.write_text('{"factor_weights": {"a": 1.0}}', encoding="utf-8")
    version = V10VersionControl(state_path, state_path.parent / f"versions_{uuid4().hex}")

    snapshot = version.snapshot("stable")
    state_path.write_text('{"factor_weights": {"a": 0.5}}', encoding="utf-8")
    rollback = version.rollback(snapshot["version_id"])

    assert rollback["rolled_back"] is True
    assert '"a": 1.0' in state_path.read_text(encoding="utf-8")


def test_governance_blocks_unapproved_and_invalid_proposals() -> None:
    pending = create_proposal("FACTOR_WEIGHT_CHANGE", "tau_factor_score", 0.2, 0.205, "test")
    invalid = create_proposal("FACTOR_WEIGHT_CHANGE", "tau_factor_score", 0.2, 0.40, "too large")
    invalid = HumanApprovalEngine().review([invalid], approvals={invalid.proposal_id: True})[0]

    result = V10Governance().validate([pending, invalid])

    assert pending in result.rejected_proposals
    assert invalid in result.rejected_proposals
    assert result.errors


def test_execution_logs_approved_change() -> None:
    state_path = _path("exec_state")
    audit_path = _path("exec_audit").with_suffix(".jsonl")
    engine = V10SelfLearningEngine(state_path)
    proposal = V10ProposalEngine().generate_proposals(
        [
            {
                "symbol": "000977.SZ",
                "outcome": "WIN",
                "confidence": 0.50,
                "contributing_factors": ["tau_factor_score"],
            }
        ],
        {"factor_weights": engine.state.factor_weights},
    )[0]
    approved = HumanApprovalEngine().review([proposal], approvals={proposal.proposal_id: True})
    valid = V10Governance().validate(approved).valid_proposals

    result = ExecutionEngine(state_path, audit_engine=V10AuditEngine(audit_path)).apply_approved(valid)

    assert result["state_changed"] is True
    assert result["change_records"]
    assert "SYSTEM_CHANGE_APPLIED" in audit_path.read_text(encoding="utf-8")


def test_change_tracker_records_before_after() -> None:
    record = V10ChangeTracker().track_change(
        target="tau_factor_score",
        before=0.20,
        after=0.205,
        reason="approved proposal",
        proposal_id="prop_test",
    )

    assert record.before == 0.20
    assert record.after == 0.205
    assert record.proposal_id == "prop_test"
