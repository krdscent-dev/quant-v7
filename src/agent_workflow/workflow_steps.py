"""Default research workflow step adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, TYPE_CHECKING

from core.provider_router import ProviderRouter
from src.knowledge_base.kb_store import DEFAULT_KB_STORE


WorkflowStepHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]
if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .workflow_engine import WorkflowEngine


def _summary_dict(**payload: Any) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def provider_fetch_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    symbols = list(context.get("symbols", []))
    provider_router = ProviderRouter()
    providers = provider_router.describe_routing()
    return _summary_dict(
        provider_count=len(providers.get("providers", [])),
        symbols=symbols,
        sample_provider=providers.get("providers", [{}])[0].get("name", "mock") if providers.get("providers") else "mock",
    )


def provider_trust_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    router = ProviderRouter()
    scores = router.get_provider_trust_scores()
    return _summary_dict(trust_top=scores[:3], trust_count=len(scores))


def data_mapping_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(mapped=False)
    return _summary_dict(
        mapped=True,
        company_code=rows[0].get("company_code", ""),
        provider_summary=rows[0].get("factor_input_summary", {}).get("provider_summary", {}),
    )


def financial_cross_validation_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(validation_status="SKIPPED")
    financial = rows[0].get("factor_input_summary", {}).get("provider_summary", {}).get("financial_summary", {})
    return _summary_dict(
        validation_status=financial.get("validation_status", "UNKNOWN"),
        provider_trust_score=financial.get("provider_trust_score", 0.0),
    )


def factor_confidence_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(factor_count=0)
    return _summary_dict(
        factor_count=len(rows[0].get("factor_confidences", {})),
        confidence_score=float(rows[0].get("confidence_score", 0.0)),
    )


def factor_input_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(factor_input_count=0)
    return _summary_dict(
        factor_input_count=len(rows[0].get("factor_input_summary", {})),
        company_code=rows[0].get("company_code", ""),
        theme=str(rows[0].get("theme", "")),
    )


def evidence_chain_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(nodes=0)
    evidence_summary = rows[0].get("evidence_summary", {})
    return _summary_dict(
        nodes=len(evidence_summary.get("nodes", [])),
        overall_confidence=evidence_summary.get("overall_confidence", 0.0),
    )


def strategic_score_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(strategic_score=0.0)
    return _summary_dict(strategic_score=float(rows[0].get("strategic_score", 0.0)))


def research_explainability_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(explanation=False)
    return _summary_dict(
        score_explanation=bool(rows[0].get("score_explanation")),
        decision_explanation=bool(rows[0].get("decision_explanation")),
    )


def research_decision_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = list(context.get("rows", []))
    if not rows:
        return _summary_dict(decision_action="WATCH")
    return _summary_dict(
        decision_action=rows[0].get("research_conclusion", "WATCH"),
        final_decision=rows[0].get("final_decision", "WATCH"),
    )


def portfolio_scoring_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    snapshot = context.get("portfolio_snapshot", {})
    if not snapshot:
        return _summary_dict(portfolio_candidates=0)
    return _summary_dict(
        portfolio_candidates=len(snapshot.get("candidates", [])),
        core_candidates=len(snapshot.get("core_candidates", [])),
    )


def position_sizing_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    snapshot = context.get("position_snapshot", {})
    if not snapshot:
        return _summary_dict(position_recommendations=0)
    return _summary_dict(position_recommendations=len(snapshot.get("recommendations", [])))


def risk_management_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    report = context.get("risk_report", {})
    if not report:
        return _summary_dict(risk_level="LOW")
    return _summary_dict(risk_level=report.get("risk_level", "LOW"), risk_checks=len(report.get("checks", [])))


def rebalancing_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    plan = context.get("rebalance_plan", {})
    if not plan:
        return _summary_dict(rebalance_actions=0)
    return _summary_dict(rebalance_actions=len(plan.get("actions", [])), turnover=plan.get("turnover", 0.0))


def backtest_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    result = context.get("backtest_result", {})
    if not result:
        return _summary_dict(backtest_result=False)
    return _summary_dict(
        backtest_result=True,
        total_return=float(result.get("backtest_summary", {}).get("total_return", 0.0)),
    )


def knowledge_base_update_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    return _summary_dict(records=len(DEFAULT_KB_STORE.list_records()))


def weekly_report_step(context: Mapping[str, Any]) -> Mapping[str, Any]:
    return _summary_dict(report_generated=True)


def build_default_workflow_steps() -> dict[str, WorkflowStepHandler]:
    return {
        "Provider Fetch": provider_fetch_step,
        "Provider Trust": provider_trust_step,
        "Data Mapping": data_mapping_step,
        "Financial Cross Validation": financial_cross_validation_step,
        "Factor Confidence": factor_confidence_step,
        "Factor Input": factor_input_step,
        "Evidence Chain": evidence_chain_step,
        "Strategic Score": strategic_score_step,
        "Research Explainability": research_explainability_step,
        "Research Decision": research_decision_step,
        "Portfolio Scoring": portfolio_scoring_step,
        "Position Sizing": position_sizing_step,
        "Risk Management": risk_management_step,
        "Rebalancing": rebalancing_step,
        "Backtest": backtest_step,
        "Knowledge Base Update": knowledge_base_update_step,
        "Weekly Report": weekly_report_step,
    }


def build_default_workflow_engine() -> WorkflowEngine:
    from .workflow_engine import WorkflowEngine

    engine = WorkflowEngine()
    for name, handler in build_default_workflow_steps().items():
        engine.register_step(name, handler)
    return engine
