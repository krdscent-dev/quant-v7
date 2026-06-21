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
from core.main_orchestrator import MainOrchestrator
from core.v11_agents import V11AgentOrchestrator
from analytics.attribution_engine import AttributionEngine
from backtest.v12_6_backtest_engine import V126BacktestEngine
from diagnosis.bias_detector import BiasDetector
from diagnosis.repair_engine import RepairEngine
from diagnosis.v12_7_health_monitor import HealthMonitor
from logs.trade_logger import TradeLogger
from market.v12_1_structure_engine import analyze_market_structure
from market.v12_2_capital_flow_engine import V122CapitalFlowEngine
from market.v12_3_narrative_engine import V123NarrativeEngine
from market.v12_4_cycle_engine import V124CycleEngine


class _V12RegimeAdapter:
    """Expose V12 market structure through the legacy regime interface."""

    def __init__(self, market_structure: Any, fallback_regime: Any) -> None:
        self.regime = market_structure.regime
        self.trend = market_structure.trend
        self.volatility = market_structure.volatility
        self.confidence = market_structure.confidence
        self.reason = f"{market_structure.reason} Legacy reference: {getattr(fallback_regime, 'regime', 'UNKNOWN')}."


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
    momentum = max(0.0, min(1.0, (top_score - mean(scores)) / 100.0 + avg_conf * 0.30))
    return {"trend": trend, "volatility": volatility, "price_momentum": momentum}


def _agent_performance_from_decisions(decisions: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    """Create a lightweight agent-performance view without changing scoring."""

    records: list[dict[str, Any]] = []
    for decision in decisions:
        action = str(decision.get("action", "OBSERVE"))
        risk_score = float(decision.get("risk_score", 0.0) or 0.0)
        sector_strength = float(decision.get("sector_strength", 0.0) or 0.0)
        confidence = float(decision.get("confidence", 0.0) or 0.0)

        records.append(
            {
                "agent_name": "AlphaAgent",
                "outcome": "WIN" if action in {"ADD", "SMALL_ADD", "HOLD"} and confidence >= 0.5 else "LOSS",
                "pnl_contribution": 0.04 if action in {"ADD", "SMALL_ADD"} else 0.01,
            }
        )
        records.append(
            {
                "agent_name": "RiskAgent",
                "outcome": "WIN" if risk_score <= 0.7 or regime in {"BEAR", "DEFENSIVE"} else "LOSS",
                "pnl_contribution": 0.03 if regime in {"BEAR", "DEFENSIVE"} else 0.0,
            }
        )
        records.append(
            {
                "agent_name": "SectorAgent",
                "outcome": "WIN" if sector_strength >= 0.5 else "LOSS",
                "pnl_contribution": 0.02 if sector_strength >= 0.75 else 0.0,
            }
        )
        records.append(
            {
                "agent_name": "MacroAgent",
                "outcome": "WIN" if regime in {"BULL", "STRUCTURAL", "ROTATION", "BEAR"} else "LOSS",
                "pnl_contribution": 0.01,
            }
        )
        records.append(
            {
                "agent_name": "PortfolioAgent",
                "outcome": "WIN" if action in {"HOLD", "OBSERVE", "ADD", "SMALL_ADD"} else "LOSS",
                "pnl_contribution": 0.01,
            }
        )
    return records


def _sector_flow_inputs(sector_engine: V10SectorEngine) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """Build deterministic capital-flow proxies from the current sector dashboard."""

    volume: dict[str, float] = {}
    inflow: dict[str, float] = {}
    outflow: dict[str, float] = {}
    leader_volume: dict[str, float] = {}
    for row in sector_engine.sector_dashboard():
        sector = str(row["sector"])
        strength = float(row["sector_strength"])
        sector_volume = round(100.0 * max(strength, 0.05), 4)
        volume[sector] = sector_volume
        inflow[sector] = round(sector_volume * strength, 4)
        outflow[sector] = round(sector_volume * max(0.0, 1.0 - strength), 4)
        leader_volume[sector] = round(sector_volume * (0.35 + 0.40 * strength), 4)
    return volume, inflow, outflow, leader_volume


def _cycle_inputs(
    market_structure: Any,
    capital_flow_analysis: Any,
    narrative: Any,
    sector_engine: V10SectorEngine,
    ranked: list[Any],
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Build deterministic proxies for liquidity, sentiment, and industry cycles."""

    flow_strength_map = {"STRONG": 0.90, "MEDIUM": 0.65, "WEAK": 0.35}
    liquidity_score = max(
        0.0,
        min(
            1.0,
            0.45 * flow_strength_map.get(str(capital_flow_analysis.flow_strength), 0.35)
            + 0.35 * (1.0 - float(getattr(market_structure, "volatility", 0.0) or 0.0))
            + 0.20 * float(getattr(market_structure, "structure_strength", 0.5) or 0.5),
        ),
    )
    fear_index = max(
        0.0,
        min(
            100.0,
            100.0
            * (
                0.60 * float(getattr(market_structure, "volatility", 0.0) or 0.0)
                + 0.40 * (1.0 - float(getattr(narrative, "narrative_strength", 0.0) or 0.0))
            ),
        ),
    )
    avg_sector_strength = sum(float(value) for value in sector_engine.sector_scores.values()) / max(
        len(sector_engine.sector_scores), 1
    )
    avg_score = sum(float(getattr(item, "strategic_score", 0.0)) for item in ranked) / max(len(ranked), 1)
    industry_growth = max(
        0.0,
        min(1.0, 0.55 * avg_sector_strength + 0.45 * float(getattr(narrative, "narrative_strength", 0.0) or 0.0)),
    )
    valuation_score = max(0.0, min(1.0, 1.0 - (avg_score / 100.0)))
    return (
        {"liquidity_score": round(liquidity_score, 4)},
        {"fear_index": round(fear_index, 2)},
        {"industry_growth": round(industry_growth, 4), "valuation_score": round(valuation_score, 4)},
    )


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
    orchestrator = MainOrchestrator(ranked, decision_engine=decision_engine, audit_engine=audit_engine)
    orchestration = orchestrator.run(learning_context)
    sector_engine = orchestration.sector_engine
    market_structure = orchestration.market_state["structure"]
    capital_flow_analysis = orchestration.market_state["capital_flow"]
    narrative = orchestration.market_state["narrative"]
    cycle_state = orchestration.market_state["cycle"]
    regime_result = orchestration.regime_result
    capital_state = orchestration.capital_state
    sector_context = sector_engine.build_sector_context()
    capital_flows = capital_flow_analysis.ranked_flows
    flow_by_sector = {item.sector: item for item in capital_flows}
    raw_decisions = orchestration.decisions
    final_decisions = raw_decisions
    v11_decisions = orchestration.v11_decisions

    print("V12 Market Intelligence:")
    print(f"market_regime\t{market_structure.regime}\ttrend={market_structure.trend_score:.2f}\tvolatility={market_structure.volatility:.2f}\tmomentum={market_structure.price_momentum:.2f}\tvolatility_state={market_structure.volatility_state}\tstructure_strength={market_structure.structure_strength:.2f}\tconfidence={market_structure.confidence:.2f}")
    print(f"market_reason\t{market_structure.reason}")
    print(f"dominant_narrative\t{narrative.dominant_narrative}")
    print(f"narrative_strength\t{narrative.narrative_strength:.2f}")
    print(f"narrative_phase\t{narrative.narrative_phase}")
    print(f"narrative_consistency\t{narrative.consistency}")
    print(f"active_narratives\t{', '.join(item.narrative for item in narrative.active_narratives)}")
    print(
        "cycle_state\t"
        f"combined={cycle_state.combined_cycle_state}\t"
        f"liquidity={cycle_state.liquidity_cycle}\t"
        f"sentiment={cycle_state.sentiment_cycle}\t"
        f"industry={cycle_state.industry_cycle}\t"
        f"risk_appetite={cycle_state.risk_appetite}\taggressiveness={cycle_state.aggressiveness:.2f}"
    )
    print("capital_control")
    print(
        "capital_state\t"
        f"risk_score={capital_state['risk_score']:.2f}\t"
        f"capital_bias={capital_state['capital_bias']}\t"
        f"allocation_ceiling={capital_state['allocation_ceiling']:.2f}\t"
        f"exposure_breadth={capital_state['exposure_breadth']}"
    )
    print(f"capital_exposure\t{capital_state['exposure']}")
    print(f"capital_rebalance\t{capital_state['rebalance_signals']}")
    print(f"flow_strength\t{capital_flow_analysis.flow_strength}")
    print(f"leader_concentration\t{capital_flow_analysis.leader_concentration:.2f}")
    print(f"rotation_path\t{' -> '.join(capital_flow_analysis.rotation_path)}")
    print("capital_flow_ranking")
    print("rank\tsector\tflow_score\tdirection\tleader_concentration\tnet_inflow\tflow_strength")
    for flow in capital_flows:
        print(f"{flow.rank}\t{flow.sector}\t{flow.flow_score:.2f}\t{flow.direction}\t{flow.leader_concentration:.2f}\t{flow.net_inflow:.2f}\t{flow.flow_strength}")
    print("")
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
    performance_log = self_learning_engine.evaluate_decision(final_decisions)
    agent_performance_log = _agent_performance_from_decisions(final_decisions, regime_result.regime)
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

    print("symbol\talpha_score\trisk_score\tmarket_regime\tdominant_narrative\tnarrative_strength\tnarrative_phase\tcycle_state\tsector\tsector_strength\tcapital_flow_score\tflow_direction\tleader_concentration\tconflict\tfinal_weighted_decision\tfinal_allocation\tcurrent_agent_weights\tregime_adjusted_weights\tactive_agents\tremoved_agents\tnewly_created_agents\tpromoted_agents\tagent_performance_scores\tstructural_changes\tagent_performance_summary\tarbitration_reason\taudit_trail")
    for decision in v11_decisions:
        sector_payload = decision["sector_context"]
        market_payload = decision["market_intelligence"]
        print(
            f"{decision['symbol']}\t"
            f"{decision['alpha_score']:.2f}\t"
            f"{decision['risk_score']:.2f}\t"
            f"{decision['macro_regime']}\t"
            f"{market_payload['dominant_narrative']}\t"
            f"{float(market_payload['narrative_strength']):.2f}\t"
            f"{market_payload['narrative_phase']}\t"
            f"{market_payload['combined_cycle_state']}/{market_payload['liquidity_cycle']}/{market_payload['sentiment_cycle']}/{market_payload['industry_cycle']}/{market_payload['risk_appetite']}\t"
            f"{sector_payload['sector']}\t"
            f"{sector_payload['sector_strength']:.2f}\t"
            f"{float(market_payload['capital_flow_score']):.2f}\t"
            f"{market_payload['capital_flow_direction']}\t"
            f"{float(market_payload['leader_concentration']):.2f}\t"
            f"{decision['conflict_detected']}\t"
            f"{decision['final_weighted_decision']}\t"
            f"{decision['final_allocation']:.4f}\t"
            f"{decision['current_agent_weights']}\t"
            f"{decision['regime_adjusted_weights']}\t"
            f"{decision['active_agents']}\t"
            f"{decision['removed_agents']}\t"
            f"{decision['newly_created_agents']}\t"
            f"{decision['promoted_agents']}\t"
            f"{decision['agent_performance_scores']}\t"
            f"{decision['structural_changes']}\t"
            f"{decision['agent_performance_summary']}\t"
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

    trade_logger = TradeLogger(base_dir / "logs" / "trade_log_v12_6.jsonl")
    attribution_engine = AttributionEngine()
    v126_engine = V126BacktestEngine(
        trade_logger=trade_logger,
        attribution_engine=attribution_engine,
    )
    v126_result = v126_engine.simulate(
        market_state=orchestration.market_state,
        capital_state=capital_state,
        decisions=final_decisions,
        v11_decisions=v11_decisions,
    )

    print("")
    print("V12.6 Full System Backtest:")
    print(f"period\t{v126_result.period}")
    print(f"total_return\t{v126_result.total_return:.4f}")
    print(f"max_drawdown\t{v126_result.max_drawdown:.4f}")
    print(f"win_rate\t{v126_result.win_rate:.4f}")
    print(f"trade_count\t{v126_result.trade_count}")
    print("layer_attribution")
    for layer, value in v126_result.layer_attribution.items():
        print(f"{layer}\t{value:.6f}")
    print("equity_curve")
    for item in v126_result.equity_curve[:10]:
        print(
            f"{item['date']}\t"
            f"equity={float(item['equity']):.4f}\t"
            f"daily_return={float(item['daily_return']):.4f}\t"
            f"drawdown={float(item['drawdown']):.4f}"
        )
    print("trade_log_path")
    print(trade_logger.path)
    if v126_result.warnings:
        print("backtest_warnings")
        for warning in v126_result.warnings[:10]:
            print(f"- {warning}")

    trade_logs = trade_logger.read_trades()
    agent_weights = {}
    agent_accuracy = []
    if v11_decisions:
        agent_weights = dict(v11_decisions[0].get("current_agent_weights", {}) or {})
        for decision in v11_decisions:
            summary = decision.get("agent_performance_summary", {}) or {}
            if summary:
                agent_accuracy.extend(float(item.get("accuracy", 0.0) or 0.0) for item in summary.values())
    health_monitor = HealthMonitor()
    bias_detector = BiasDetector()
    repair_engine = RepairEngine()
    health_report = health_monitor.assess(
        {
            "total_return": v126_result.total_return,
            "max_drawdown": v126_result.max_drawdown,
            "win_rate": v126_result.win_rate,
        },
        trade_logs,
        {
            "agent_accuracy": sum(agent_accuracy) / len(agent_accuracy) if agent_accuracy else 0.0,
            "risk_events": len(v126_result.warnings),
            "volatility": float(v126_result.attribution.layer_breakdown.get("capital_control", 0.0) or 0.0),
            "confidence_bias": execution_result["model_bias_detection"].get("confidence_bias", "neutral"),
        },
    )
    bias_findings = bias_detector.detect(
        trade_logs,
        agent_weights=agent_weights,
        performance_metrics=execution_result["model_bias_detection"],
    )
    repair_suggestions = repair_engine.propose(
        health_report,
        bias_findings,
        {
            "total_return": v126_result.total_return,
            "max_drawdown": v126_result.max_drawdown,
            "win_rate": v126_result.win_rate,
        },
    )

    print("")
    print("V12.7 Self-Diagnosis:")
    print(f"system_health\t{health_report.status}")
    print(f"severity\t{health_report.severity}")
    print(f"health_score\t{health_report.score:.4f}")
    print(f"drawdown_risk\t{health_report.drawdown_risk}")
    print(f"accuracy_risk\t{health_report.accuracy_risk}")
    print(f"risk_level\t{health_report.risk_level}")
    if health_report.warnings:
        print("health_warnings")
        for item in health_report.warnings:
            print(f"- {item}")
    print("bias_detection")
    for finding in bias_findings:
        print(f"{finding.bias_name}\tseverity={finding.severity}\tmessage={finding.message}\tevidence={finding.evidence}")
    print("repair_suggestions")
    for suggestion in repair_suggestions:
        print(
            f"{suggestion.priority}\t"
            f"{suggestion.severity}\t"
            f"{suggestion.title}\t"
            f"{suggestion.action}\t"
            f"{suggestion.expected_effect}"
        )


if __name__ == "__main__":
    main()
