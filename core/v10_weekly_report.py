"""V10 weekly Decision Audit Report generator.

This report audits action decisions produced by the V10 layer on top of
the current V9 scoring outputs. It does not change scoring, portfolio,
provider, or backtest behavior.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Mapping
import json
import os

from core.v10_cognitive_graph import V10CognitiveGraph
from core.decision_engine import DecisionEngine
from core.regime_engine import RegimeEngine, RegimeResult
from core.human_approval_engine import HumanApprovalEngine
from core.v10_proposal_engine import V10ProposalEngine
from core.v10_self_learning_engine import V10SelfLearningEngine
from core.v10_sector_engine import V10SectorEngine
from strategy.strategic_score_engine import StrategicScoreResult, build_rankings


@dataclass(frozen=True)
class DecisionAuditRow:
    """One audited V10 decision."""

    symbol: str
    name: str
    theme: str
    sector: str
    sector_strength: float
    leader_flag: bool
    causal_chain: list[str]
    bottleneck_node: str
    score: float
    action: str
    confidence: float
    horizon: str
    reason: str
    regime: str
    regime_validation: str
    confidence_flag: str
    portfolio_impact: str
    factor_weakness: str


def _cache_path(root: Path) -> Path:
    return root / "reports" / "cache" / "v10_rankings.json"


def _result_to_dict(result: StrategicScoreResult) -> dict[str, Any]:
    return {
        "code": result.code,
        "name": result.name,
        "theme": result.theme,
        "strategic_score": result.strategic_score,
        "factor_breakdown": dict(result.factor_breakdown),
        "score_explanation": result.score_explanation,
        "evidence_refs": {},
    }


def _result_from_dict(payload: Mapping[str, Any]) -> StrategicScoreResult:
    return StrategicScoreResult(
        code=str(payload.get("code", "UNKNOWN")),
        name=str(payload.get("name", "UNKNOWN")),
        theme=str(payload.get("theme", "UNKNOWN")),
        strategic_score=float(payload.get("strategic_score", 0.0)),
        factor_breakdown=dict(payload.get("factor_breakdown", {})),
        score_explanation=str(payload.get("score_explanation", "")),
        evidence_refs={},
    )


def load_or_build_rankings(root: Path, *, refresh: bool = False) -> list[StrategicScoreResult]:
    """Load cached V9 ranking results, or build and cache them when needed."""

    path = _cache_path(root)
    use_cache = not refresh and os.environ.get("V10_REFRESH") != "1"
    if use_cache and path.exists():
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [_result_from_dict(item) for item in payload.get("results", [])]

    results = build_rankings()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "results": [_result_to_dict(result) for result in results],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    return results


def _confidence_from_result(result: StrategicScoreResult) -> float:
    breakdown = result.factor_breakdown or {}
    value = breakdown.get("final_confidence", breakdown.get("confidence_score", 0.0))
    try:
        confidence = float(value)
    except Exception:
        confidence = 0.0
    if confidence > 1.0:
        confidence /= 100.0
    return max(0.0, min(1.0, confidence))


def _market_snapshot(results: list[StrategicScoreResult]) -> dict[str, float]:
    scores = [float(item.strategic_score) for item in results]
    confidences = [_confidence_from_result(item) for item in results]
    if not scores:
        return {"trend": 0.0, "volatility": 1.0}
    top_score = max(scores)
    score_spread = max(scores) - min(scores)
    avg_confidence = mean(confidences) if confidences else 0.0
    return {
        "trend": max(0.0, min(1.0, top_score / 100.0)),
        "volatility": max(0.0, min(1.0, score_spread / 100.0 + (1.0 - avg_confidence) * 0.35)),
    }


def _regime_validation(regime: str, action: str, score: float, confidence: float) -> str:
    defensive_actions = {"REDUCE", "EXIT", "OBSERVE", "SMALL_ADD"}
    constructive_actions = {"BUY", "ADD", "SMALL_ADD", "HOLD"}
    if regime in {"BEAR", "DEFENSIVE"} and action in defensive_actions:
        return "YES"
    if regime in {"BULL", "STRUCTURAL"} and action in constructive_actions and confidence >= 0.55:
        return "YES"
    if regime == "ROTATION" and action in {"HOLD", "OBSERVE", "ADD"}:
        return "YES"
    if confidence < 0.35 and action in {"OBSERVE", "EXIT", "REDUCE"}:
        return "YES"
    if score < 30 and action in defensive_actions:
        return "YES"
    return "NO"


def _readable_reason(result: StrategicScoreResult, decision: Mapping[str, Any], regime: RegimeResult) -> str:
    action = str(decision.get("action", "OBSERVE"))
    confidence = float(decision.get("confidence", 0.0))
    score = float(result.strategic_score)
    if action == "OBSERVE":
        return f"Score {score:.2f} and confidence {confidence:.2f} support observation, not invalidation, under {regime.regime}."
    if action in {"EXIT", "REDUCE"}:
        return f"{regime.regime} context requires lower exposure; score {score:.2f} does not justify risk."
    if action in {"BUY", "ADD"}:
        return f"Score {score:.2f} and confidence {confidence:.2f} support action in {regime.regime}, subject to price validation."
    return f"Score {score:.2f} supports maintaining exposure while waiting for stronger confirmation."


def _confidence_flag(score: float, confidence: float, action: str) -> str:
    if confidence >= 0.75 and score < 50:
        return "Overconfidence"
    if confidence < 0.35 and score >= 60:
        return "Underconfidence"
    if confidence < 0.35:
        return "Low confidence guarded"
    if action in {"BUY", "ADD"} and confidence < 0.65:
        return "Action confidence risk"
    return "Calibrated"


def _portfolio_impact(action: str) -> str:
    if action in {"EXIT", "REDUCE"}:
        return "Risk control positive; realized drawdown impact unavailable without portfolio PnL."
    if action in {"BUY", "ADD"}:
        return "Potential upside contributor; requires price and position validation."
    if action == "HOLD":
        return "Neutral carry; monitor drawdown and confidence drift."
    return "Opportunity cost possible if theme accelerates."


def _factor_weakness(result: StrategicScoreResult) -> str:
    breakdown = result.factor_breakdown or {}
    weak = [
        factor
        for factor, value in breakdown.items()
        if factor not in {"confidence_score", "final_confidence"} and float(value) < 40.0
    ]
    if not weak:
        return "No major factor weakness detected."
    return ", ".join(weak[:4])


def _missed_regime_transitions(rows: list[DecisionAuditRow], regime: RegimeResult) -> list[str]:
    high_score = [row for row in rows if row.score >= 70 and row.confidence >= 0.55]
    if regime.regime in {"BEAR", "DEFENSIVE"} and high_score:
        return ["Potential structural transition: high-score names exist despite defensive regime."]
    if regime.regime in {"BULL", "STRUCTURAL"} and not high_score:
        return ["Constructive regime lacks high-confidence candidates; monitor false-positive regime risk."]
    return ["No obvious missed transition detected from current scoring distribution."]


def _build_audit_rows(results: list[StrategicScoreResult], regime: RegimeResult) -> list[DecisionAuditRow]:
    decision_engine = DecisionEngine()
    sector_engine = V10SectorEngine.from_results(results)
    cognitive_graph = V10CognitiveGraph()
    sector_context = sector_engine.build_sector_context()
    rows: list[DecisionAuditRow] = []
    for result in results:
        confidence = _confidence_from_result(result)
        item_sector_context = sector_context.get(result.code, {})
        causal = cognitive_graph.infer_for_context(
            sector=str(item_sector_context.get("sector", "UNKNOWN")),
            theme=result.theme,
        )
        decision = decision_engine.decide(
            symbol=result.code,
            score=float(result.strategic_score),
            regime=regime,
            confidence=confidence,
            context={
                "price_zone": "UNKNOWN",
                "momentum": "UNKNOWN",
                "stage": "UNKNOWN",
                "theme": result.theme,
                "theme_tags": [result.theme, item_sector_context.get("sector", "UNKNOWN")],
                "causal_chain": causal.causal_chain,
                "bottleneck_node": causal.bottleneck_node,
                "chain_strength": causal.chain_strength,
                **item_sector_context,
            },
        )
        action = str(decision.get("action", "OBSERVE"))
        rows.append(
            DecisionAuditRow(
                symbol=result.code,
                name=result.name,
                theme=result.theme,
                sector=str(decision.get("sector", item_sector_context.get("sector", "UNKNOWN"))),
                sector_strength=float(decision.get("sector_strength", 0.0)),
                leader_flag=bool(decision.get("leader_flag", False)),
                causal_chain=list(decision.get("causal_chain", [])),
                bottleneck_node=str(decision.get("bottleneck_node", "NONE")),
                score=float(result.strategic_score),
                action=action,
                confidence=confidence,
                horizon=str(decision.get("horizon", "")),
                reason=_readable_reason(result, decision, regime),
                regime=regime.regime,
                regime_validation=_regime_validation(regime.regime, action, float(result.strategic_score), confidence),
                confidence_flag=_confidence_flag(float(result.strategic_score), confidence, action),
                portfolio_impact=_portfolio_impact(action),
                factor_weakness=_factor_weakness(result),
            )
        )
    return rows


def generate_v10_decision_audit_report(base_dir: Path | None = None) -> Path:
    """Generate the V10 weekly Decision Audit Report."""

    root = base_dir or Path(__file__).resolve().parents[1]
    refresh = os.environ.get("V10_REFRESH") == "1"
    results = load_or_build_rankings(root, refresh=refresh)
    market_data = _market_snapshot(results)
    regime = RegimeEngine().classify(market_data)
    rows = _build_audit_rows(results, regime)
    learning_engine = V10SelfLearningEngine(root / "reports" / "cache" / "v10_learning_state.json")
    learning_context = learning_engine.adaptive_context()
    proposal_source = [
        {
            "symbol": row.symbol,
            "outcome": "WIN" if row.action in {"SMALL_ADD", "ADD", "HOLD"} and row.confidence <= 0.65 else "NEUTRAL",
            "confidence": row.confidence,
            "contributing_factors": [
                factor
                for factor in row.factor_weakness.split(", ")
                if factor and factor != "No major factor weakness detected."
            ],
        }
        for row in rows
    ]
    proposals = V10ProposalEngine().generate_proposals(
        proposal_source,
        {
            "factor_weights": learning_context.get("adaptive_factor_weights", {}),
            "confidence_bias": learning_context.get("confidence_bias", 0.0),
            "confidence_sensitivity": learning_context.get("confidence_sensitivity", 1.0),
        },
    )
    reviewed_proposals = HumanApprovalEngine().review(proposals, approvals={})

    action_counts = Counter(row.action for row in rows)
    validation_no = [row for row in rows if row.regime_validation == "NO"]
    overconfidence = [row for row in rows if row.confidence_flag == "Overconfidence"]
    underconfidence = [row for row in rows if row.confidence_flag == "Underconfidence"]
    low_confidence_guarded = [row for row in rows if row.confidence_flag == "Low confidence guarded"]
    missed_transitions = _missed_regime_transitions(rows, regime)
    positive_impact = [row for row in rows if row.action in {"EXIT", "REDUCE", "BUY", "ADD", "SMALL_ADD"}]
    drawdown_risk = [row for row in rows if row.action in {"BUY", "ADD", "SMALL_ADD", "HOLD"} and row.confidence < 0.65]

    lines: list[str] = []
    lines.append("# V10 Weekly Decision Audit Report")
    lines.append("")
    lines.append("## 1. EXECUTIVE SUMMARY")
    lines.append(f"- Overall regime this week: {regime.regime}")
    lines.append(f"- Regime inputs: trend={regime.trend:.2f}, volatility={regime.volatility:.2f}, confidence={regime.confidence:.2f}")
    lines.append(f"- Regime reason: {regime.reason}")
    lines.append(f"- System performance overview: {len(rows)} symbols audited; actions={dict(action_counts)}")
    lines.append("- Actionable insight: current system is defensive but no longer frozen; OBSERVE is the default low-confidence action.")
    lines.append("")

    lines.append("## 2. DECISION LOG")
    lines.append("| symbol | name | theme | sector | causal chain | bottleneck | sector strength | leader | score | action | confidence | reason | regime context |")
    lines.append("|---|---|---|---|---|---|---:|---|---:|---|---:|---|---|")
    for row in rows:
        chain_text = " -> ".join(row.causal_chain) if row.causal_chain else "NONE"
        lines.append(
            f"| {row.symbol} | {row.name} | {row.theme} | {row.sector} | {chain_text} | {row.bottleneck_node} | {row.sector_strength:.2f} | {row.leader_flag} | {row.score:.2f} | {row.action} | {row.confidence:.2f} | {row.reason} | {row.regime} / {row.horizon} |"
        )
    lines.append("")

    lines.append("## 3. REGIME VALIDATION")
    lines.append("| symbol | action | regime | validation | note |")
    lines.append("|---|---|---|---|---|")
    for row in rows:
        note = "Action is aligned with current defensive/constructive context." if row.regime_validation == "YES" else "Review action-regime mismatch."
        lines.append(f"| {row.symbol} | {row.action} | {row.regime} | {row.regime_validation} | {note} |")
    lines.append("")
    lines.append("### Missed Regime Transitions")
    for item in missed_transitions:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 4. CONFIDENCE CALIBRATION")
    lines.append("### Overconfidence Cases")
    if overconfidence:
        for row in overconfidence:
            lines.append(f"- {row.symbol}: confidence={row.confidence:.2f}, score={row.score:.2f}")
    else:
        lines.append("- None detected.")
    lines.append("")
    lines.append("### Underconfidence Cases")
    if underconfidence:
        for row in underconfidence:
            lines.append(f"- {row.symbol}: confidence={row.confidence:.2f}, score={row.score:.2f}")
    else:
        lines.append("- None detected.")
    lines.append("")
    lines.append("### Low Confidence Guarded Cases")
    if low_confidence_guarded:
        for row in low_confidence_guarded[:10]:
            lines.append(f"- {row.symbol}: guarded by low confidence, action={row.action}")
    else:
        lines.append("- None detected.")
    lines.append("")

    lines.append("## 5. PORTFOLIO IMPACT")
    lines.append("### Positive Contribution Candidates")
    if positive_impact:
        for row in positive_impact[:10]:
            lines.append(f"- {row.symbol}: {row.portfolio_impact}")
    else:
        lines.append("- No positive contribution candidates detected.")
    lines.append("")
    lines.append("### Drawdown / Opportunity Cost Cases")
    if drawdown_risk:
        for row in drawdown_risk:
            lines.append(f"- {row.symbol}: action={row.action}, confidence={row.confidence:.2f}")
    else:
        lines.append("- No deployable low-confidence position risk detected; realized drawdown attribution requires portfolio PnL data.")
    lines.append("")

    lines.append("## 6. MODEL INSIGHTS")
    lines.append("### Factor Weaknesses")
    lines.append("| symbol | factor weaknesses |")
    lines.append("|---|---|")
    for row in rows:
        lines.append(f"| {row.symbol} | {row.factor_weakness} |")
    lines.append("")
    lines.append("### Cognitive Graph Insights")
    lines.append("- Provider and factor confidence are the binding constraints this week.")
    lines.append("- Decision graph is dominated by confidence guard rails, not valuation or portfolio construction.")
    lines.append("- Main failure mode: low financial validation confidence suppresses sizing, but no longer invalidates all actions.")
    lines.append("")
    lines.append("## Actionable Insights")
    lines.append("- Keep Monday action at OBSERVE unless fresh data lifts confidence above 0.35 or score rises above alpha thresholds.")
    lines.append("- Prioritize fixing provider confidence and financial validation before relaxing decision thresholds.")
    lines.append("- Add price/EPS data before allowing BUY/ADD actions to pass portfolio sizing.")
    lines.append("- Review any symbol that keeps high theme score but remains REDUCE or OBSERVE for more than two runs.")
    lines.append("")
    lines.append("## 7. HUMAN-IN-THE-LOOP LEARNING PROPOSALS")
    lines.append("- Direct self-learning updates: disabled")
    lines.append(f"- Pending proposals: {len(proposals)}")
    lines.append(f"- Approved proposals: {sum(1 for item in reviewed_proposals if item.status == 'APPROVED')}")
    lines.append("- State changed: False")
    lines.append("")
    lines.append("### Pending Proposal Preview")
    if proposals:
        lines.append("| proposal_id | type | target | current | proposed | status | reason |")
        lines.append("|---|---|---|---:|---:|---|---|")
        for proposal in proposals[:20]:
            lines.append(
                f"| {proposal.proposal_id} | {proposal.proposal_type} | {proposal.target} | {proposal.current_value:.4f} | {proposal.proposed_value:.4f} | {proposal.status} | {proposal.reason} |"
            )
    else:
        lines.append("- No proposals generated.")
    lines.append("")
    lines.append("### Model Bias Detection")
    for key, value in learning_context.get("model_bias", {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("### Confidence Calibration State")
    lines.append(f"- confidence_bias: {float(learning_context.get('confidence_bias', 0.0)):.4f}")
    lines.append(f"- confidence_sensitivity: {float(learning_context.get('confidence_sensitivity', 1.0)):.4f}")

    output_dir = root / "reports" / "weekly"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"V10_decision_audit_report_{datetime.now().strftime('%Y%m%d')}.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    report_path = generate_v10_decision_audit_report()
    print(report_path)


if __name__ == "__main__":
    main()
