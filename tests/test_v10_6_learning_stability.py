"""V10.6 self-learning validation tests."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.decision_engine import DecisionEngine
from core.v10_portfolio_autopilot import V10PortfolioAutopilot
from core.execution_engine import ExecutionEngine
from core.human_approval_engine import HumanApprovalEngine
from core.v10_proposal_engine import V10ProposalEngine
from core.v10_self_learning_engine import DEFAULT_FACTOR_WEIGHTS, V10SelfLearningEngine


def _state_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v10_stability_{uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_backtest_stability_no_auto_weight_oscillation_without_approval() -> None:
    engine = V10SelfLearningEngine(_state_path())
    before = dict(engine.state.factor_weights)
    proposal_engine = V10ProposalEngine()

    for _ in range(12):
        proposals = proposal_engine.generate_proposals(
            [
                {
                    "outcome": "WIN",
                    "confidence": 0.30,
                    "contributing_factors": ["tau_factor_score", "order_confirmation_score"],
                },
                {
                    "outcome": "LOSS",
                    "confidence": 0.80,
                    "contributing_factors": ["advanced_packaging_score"],
                },
            ],
            {
                "factor_weights": engine.state.factor_weights,
                "confidence_bias": engine.state.confidence_bias,
                "confidence_sensitivity": engine.state.confidence_sensitivity,
            },
        )
        reviewed = HumanApprovalEngine().review(proposals, approvals={})
        result = ExecutionEngine(engine.state_path).apply_approved(reviewed)
        assert result["state_changed"] is False
        assert engine.state.factor_weights == before


def test_learning_validity_proposals_no_reverse_learning() -> None:
    engine = V10SelfLearningEngine(_state_path())
    proposal_engine = V10ProposalEngine()

    win_proposals = proposal_engine.generate_proposals(
        [
            {
                "outcome": "WIN",
                "confidence": 0.50,
                "contributing_factors": ["tau_factor_score"],
            }
        ],
        {"factor_weights": engine.state.factor_weights},
    )
    loss_proposals = proposal_engine.generate_proposals(
        [
            {
                "outcome": "LOSS",
                "confidence": 0.50,
                "contributing_factors": ["supernode_score"],
            }
        ],
        {"factor_weights": engine.state.factor_weights},
    )

    assert win_proposals[0].proposed_value > win_proposals[0].current_value
    assert loss_proposals[0].proposed_value < loss_proposals[0].current_value


def test_same_input_does_not_produce_contradictory_actions() -> None:
    engine = DecisionEngine()
    context = {
        "sector": "AI Computing",
        "sector_strength": 0.80,
        "sector_leader_flag": False,
        "sector_rank": 2,
        "causal_chain": ["AI Computing", "AI CapEx Expansion", "Order Confirmation", "Revenue Conversion"],
        "bottleneck_node": "Order Confirmation",
        "chain_strength": "PARTIAL",
        "confidence_bias": 0.0,
        "confidence_sensitivity": 1.0,
    }

    actions = {
        engine.decide("000977.SZ", 45.0, "BEAR", 0.45, context)["action"]
        for _ in range(5)
    }

    assert len(actions) == 1


def test_portfolio_integrity_risk_control_still_active() -> None:
    autopilot = V10PortfolioAutopilot()
    decisions = autopilot.apply_constraints(
        [
            {"symbol": "A", "sector": "AI Computing", "action": "SMALL_ADD", "confidence": 0.7},
            {"symbol": "B", "sector": "AI Computing", "action": "SMALL_ADD", "confidence": 0.7},
            {"symbol": "C", "sector": "AI Computing", "action": "HOLD", "confidence": 0.7},
            {"symbol": "D", "sector": "Advanced Materials", "action": "OBSERVE", "confidence": 0.7},
        ]
    )

    assert any(row["portfolio_exposure"] > 0.35 for row in decisions)
    assert any(row["action"] == "REDUCE" for row in decisions if row["sector"] == "AI Computing")
    assert all("risk_score" in row for row in decisions)


def test_defaults_are_not_mutated_by_proposal_runs() -> None:
    engine = V10SelfLearningEngine(_state_path())
    V10ProposalEngine().generate_proposals(
        [
            {
                "outcome": "WIN",
                "confidence": 0.30,
                "contributing_factors": ["order_confirmation_score"],
            }
        ],
        {"factor_weights": engine.state.factor_weights},
    )

    assert DEFAULT_FACTOR_WEIGHTS["order_confirmation_score"] == 0.15


def test_stabilize_state_clamps_factor_concentration() -> None:
    engine = V10SelfLearningEngine(_state_path())
    engine.state.factor_weights["order_confirmation_score"] = 0.80
    engine.state.factor_weights["advanced_material_score"] = 0.01

    context = engine.stabilize_state()

    weights = context["adaptive_factor_weights"]
    assert weights["order_confirmation_score"] <= 0.30
    assert weights["advanced_material_score"] >= 0.06
