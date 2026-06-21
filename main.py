"""V10 entry point.

This script keeps the V9 strategic scoring pipeline intact and adds a thin
decision layer on top to emit ACTION-based outputs.
"""

from __future__ import annotations

from statistics import mean
from typing import Any
import os
from pathlib import Path

from core.execution_engine import ExecutionEngine
from core.human_approval_engine import HumanApprovalEngine
from core.v10_audit_engine import V10AuditEngine
from core.v10_cognitive_graph import V10CognitiveGraph
from core.decision_engine import DecisionEngine
from core.regime_engine import RegimeEngine
from core.v10_governance import V10Governance
from core.v10_portfolio_autopilot import V10PortfolioAutopilot
from core.v10_proposal_engine import V10ProposalEngine
from core.v10_self_learning_engine import V10SelfLearningEngine
from core.v10_sector_engine import V10SectorEngine
from core.v10_version_control import V10VersionControl
from core.v10_weekly_report import load_or_build_rankings
from core.v11_agents import V11AgentOrchestrator


def _confidence_from_result(result: Any) -> float:
    breakdown = getattr(result, "factor_breakdown", {}) or {}
    value = breakdown.get("final_confidence", breakdown.get("confidence_score", 0.0))
    try:
        confidence = float(value)
    except Exception:
        confidence = 0.0
    if confidence > 1.0:
        confidence /= 100.0
    return max(0.0, min(1.0, confidence))


def _market_snapshot(results: list[Any]) -> dict[str, float]:
    scores = [float(getattr(item, "strategic_score", 0.0)) for item in results]
    confidences = [_confidence_from_result(item) for item in results]
    if not scores:
        return {"trend": 0.0, "volatility": 1.0}
    top_score = max(scores)
    score_spread = max(scores) - min(scores)
    avg_conf = mean(confidences) if confidences else 0.0
    trend = max(0.0, min(1.0, top_score / 100.0))
    volatility = max(0.0, min(1.0, score_spread / 100.0 + (1.0 - avg_conf) * 0.35))
    return {"trend": trend, "volatility": volatility}


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    ranked = load_or_build_rankings(base_dir, refresh=os.environ.get("V10_REFRESH") == "1")
    regime_engine = RegimeEngine()
    decision_engine = DecisionEngine()
    portfolio_autopilot = V10PortfolioAutopilot()
    self_learning_engine = V10SelfLearningEngine(base_dir / "reports" / "cache" / "v10_learning_state.json")
    proposal_engine = V10ProposalEngine()
    approval_engine = HumanApprovalEngine()
    audit_engine = V10AuditEngine(base_dir / "reports" / "audit" / "v10_audit_log.jsonl")
    governance = V10Governance()
    version_control = V10VersionControl(
        base_dir / "reports" / "cache" / "v10_learning_state.json",
        base_dir / "reports" / "versions",
    )
    execution_engine = ExecutionEngine(
        base_dir / "reports" / "cache" / "v10_learning_state.json",
        audit_engine=audit_engine,
    )
    learning_context = self_learning_engine.adaptive_context()
    sector_engine = V10SectorEngine.from_results(ranked)
    v11_orchestrator = V11AgentOrchestrator(sector_engine, audit_engine)
    cognitive_graph = V10CognitiveGraph()
    sector_context = sector_engine.build_sector_context()
    market_data = _market_snapshot(ranked)
    regime_result = regime_engine.classify(market_data)

    print(f"Market Regime: {regime_result.regime} (trend={regime_result.trend:.2f}, volatility={regime_result.volatility:.2f})")
    print(f"Regime Reason: {regime_result.reason}")
    print("")
    print("Sector Intelligence:")
    print("sector\tstrength\trotation\tleader")
    for row in sector_engine.sector_dashboard():
        print(
            f"{row['sector']}\t"
            f"{row['sector_strength']:.2f}\t"
            f"{row['rotation_signal']}\t"
            f"{row['leader']}"
        )
    print("")
    raw_decisions: list[dict[str, Any]] = []
    for item in ranked[:10]:
        confidence = _confidence_from_result(item)
        symbol = getattr(item, "code", "UNKNOWN")
        theme = getattr(item, "theme", "UNKNOWN")
        item_sector_context = sector_context.get(str(symbol), {})
        causal = cognitive_graph.infer_for_context(
            sector=str(item_sector_context.get("sector", "UNKNOWN")),
            theme=str(theme),
        )
        decision = decision_engine.decide(
            symbol=symbol,
            score=float(getattr(item, "strategic_score", 0.0)),
            regime=regime_result,
            confidence=confidence,
            context={
                "price_zone": "UNKNOWN",
                "momentum": "UNKNOWN",
                "stage": "UNKNOWN",
                "theme": theme,
                "theme_tags": [
                    theme,
                    item_sector_context.get("sector", "UNKNOWN"),
                ],
                "causal_chain": causal.causal_chain,
                "bottleneck_node": causal.bottleneck_node,
                "chain_strength": causal.chain_strength,
                "confidence_bias": learning_context.get("confidence_bias", 0.0),
                "confidence_sensitivity": learning_context.get("confidence_sensitivity", 1.0),
                **item_sector_context,
            },
        )
        decision["score"] = round(float(getattr(item, "strategic_score", 0.0)), 2)
        raw_decisions.append(decision)

    final_decisions = portfolio_autopilot.apply_constraints(raw_decisions)
    v11_decisions = [
        v11_orchestrator.run(decision, regime_result)
        for decision in final_decisions
    ]
    performance_log = self_learning_engine.evaluate_decision(final_decisions)
    pre_snapshot = version_control.snapshot("pre_governance")
    proposals = proposal_engine.generate_proposals(
        performance_log,
        {
            "factor_weights": learning_context.get("adaptive_factor_weights", {}),
            "confidence_bias": learning_context.get("confidence_bias", 0.0),
            "confidence_sensitivity": learning_context.get("confidence_sensitivity", 1.0),
        },
    )
    reviewed_proposals = approval_engine.review(proposals, approvals={})
    governance_result = governance.validate(reviewed_proposals)
    audit_engine.log_event(
        "PROPOSALS_GENERATED",
        {"count": len(proposals), "symbols": [item.get("symbol") for item in performance_log[:10]]},
    )
    audit_engine.log_event(
        "HUMAN_REVIEW_COMPLETED",
        {
            "approved": sum(1 for item in reviewed_proposals if item.status == "APPROVED"),
            "rejected": sum(1 for item in reviewed_proposals if item.status == "REJECTED"),
        },
    )
    audit_engine.log_event(
        "GOVERNANCE_VALIDATED",
        {
            "valid": len(governance_result.valid_proposals),
            "rejected": len(governance_result.rejected_proposals),
            "warnings": governance_result.warnings[:10],
            "errors": governance_result.errors[:10],
        },
        severity="WARNING" if governance_result.errors else "INFO",
    )
    execution_result = execution_engine.apply_approved(governance_result.valid_proposals)
    post_snapshot = version_control.snapshot("post_execution")
    audit_summary = audit_engine.summary()

    print("symbol\talpha_score\trisk_score\tmacro_regime\tsector\tsector_strength\tconflict\tfinal_action\tfinal_allocation\tagent_opinions\tarbitration_reason\taudit_trail")
    for decision in v11_decisions:
        sector_payload = decision["sector_context"]
        print(
            f"{decision['symbol']}\t"
            f"{decision['alpha_score']:.2f}\t"
            f"{decision['risk_score']:.2f}\t"
            f"{decision['macro_regime']}\t"
            f"{sector_payload['sector']}\t"
            f"{sector_payload['sector_strength']:.2f}\t"
            f"{decision['conflict_detected']}\t"
            f"{decision['final_action']}\t"
            f"{decision['final_allocation']:.4f}\t"
            f"{decision['agent_opinions']}\t"
            f"{decision['arbitration_reason']}\t"
            f"{decision['audit_trail']['event_type']}@{decision['audit_trail']['timestamp']}"
        )

    print("")
    print("Human-in-the-Loop Learning Proposals:")
    print(f"pending_proposals\t{len(proposals)}")
    print(f"approved_proposals\t{execution_result['applied_count']}")
    print(f"state_changed\t{execution_result['state_changed']}")
    print(f"model_bias\t{execution_result['model_bias_detection']}")
    print(f"governance_valid\t{len(governance_result.valid_proposals)}")
    print(f"governance_rejected\t{len(governance_result.rejected_proposals)}")
    print(f"pre_snapshot\t{pre_snapshot['version_id']}")
    print(f"post_snapshot\t{post_snapshot['version_id']}")
    print(f"audit_events\t{audit_summary['total_recent_events']}")
    print(f"risk_events\t{len(audit_summary['risk_events'])}")
    print("proposal_preview")
    for proposal in proposals[:10]:
        print(
            {
                "proposal_id": proposal.proposal_id,
                "type": proposal.proposal_type,
                "target": proposal.target,
                "current": proposal.current_value,
                "proposed": proposal.proposed_value,
                "status": proposal.status,
                "reason": proposal.reason,
            }
        )


if __name__ == "__main__":
    main()
