"""Tests for V10 human-in-the-loop self-learning mode."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.execution_engine import ExecutionEngine
from core.human_approval_engine import HumanApprovalEngine
from core.v10_proposal_engine import V10ProposalEngine
from core.v10_self_learning_engine import V10SelfLearningEngine


def _state_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v10_hitl_learning_{uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_update_weights_is_blocked_and_does_not_change_state() -> None:
    path = _state_path()
    engine = V10SelfLearningEngine(path)
    before = dict(engine.state.factor_weights)

    result = engine.update_weights(
        [
            {
                "outcome": "WIN",
                "confidence": 0.30,
                "contributing_factors": ["tau_factor_score"],
            }
        ]
    )

    assert result["direct_update_blocked"] is True
    assert engine.state.factor_weights == before


def test_proposal_engine_generates_weight_increase_for_win() -> None:
    engine = V10SelfLearningEngine(_state_path())
    proposal_engine = V10ProposalEngine()

    proposals = proposal_engine.generate_proposals(
        [
            {
                "symbol": "000977.SZ",
                "outcome": "WIN",
                "confidence": 0.30,
                "contributing_factors": ["tau_factor_score"],
            }
        ],
        {
            "factor_weights": engine.state.factor_weights,
            "confidence_bias": engine.state.confidence_bias,
            "confidence_sensitivity": engine.state.confidence_sensitivity,
        },
    )

    weight_proposals = [item for item in proposals if item.proposal_type == "FACTOR_WEIGHT_CHANGE"]
    assert weight_proposals
    assert weight_proposals[0].proposed_value > weight_proposals[0].current_value
    assert all(item.status == "PENDING" for item in proposals)


def test_human_approval_rejects_missing_approval_by_default() -> None:
    engine = V10SelfLearningEngine(_state_path())
    proposal = V10ProposalEngine().generate_proposals(
        [
            {
                "symbol": "000977.SZ",
                "outcome": "WIN",
                "confidence": 0.30,
                "contributing_factors": ["tau_factor_score"],
            }
        ],
        {"factor_weights": engine.state.factor_weights},
    )[0]

    reviewed = HumanApprovalEngine().review([proposal], approvals={})

    assert reviewed[0].status == "REJECTED"


def test_execution_applies_only_approved_proposals() -> None:
    path = _state_path()
    engine = V10SelfLearningEngine(path)
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

    result = ExecutionEngine(path).apply_approved(approved)

    assert result["state_changed"] is True
    assert result["applied_count"] == 1
    updated = V10SelfLearningEngine(path)
    assert updated.state.factor_weights["tau_factor_score"] > engine.state.factor_weights["tau_factor_score"]


def test_execution_ignores_rejected_proposals() -> None:
    path = _state_path()
    engine = V10SelfLearningEngine(path)
    before = dict(engine.state.factor_weights)
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
    rejected = HumanApprovalEngine().review([proposal], approvals={})

    result = ExecutionEngine(path).apply_approved(rejected)

    assert result["state_changed"] is False
    updated = V10SelfLearningEngine(path)
    assert updated.state.factor_weights == before


def test_evaluate_decision_creates_paper_feedback() -> None:
    engine = V10SelfLearningEngine(_state_path())

    records = engine.evaluate_decision(
        [
            {
                "symbol": "000977.SZ",
                "sector": "AI Computing",
                "action": "SMALL_ADD",
                "confidence": 0.20,
                "risk_score": 0.30,
                "causal_chain": ["AI Computing", "AI CapEx Expansion", "Order Confirmation", "Revenue Conversion"],
            }
        ]
    )

    assert records[0]["outcome"] == "WIN"
    assert "tau_factor_score" in records[0]["contributing_factors"]


def test_detect_model_bias_returns_required_fields() -> None:
    engine = V10SelfLearningEngine(_state_path())

    bias = engine.detect_model_bias()

    assert "dominant_factor" in bias
    assert "weakest_factor" in bias
    assert "confidence_bias" in bias
