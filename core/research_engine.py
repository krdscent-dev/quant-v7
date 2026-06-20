"""Strategic Research Engine.

This module converts FactorInput into a ResearchDecision.
It depends on the factor registry and strategic score engine,
but not on any provider layer.
"""

from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any, Mapping

from core.factor_registry import DEFAULT_FACTOR_REGISTRY
from core.data_mapping import DataMappingLayer
from src.explainability.decision_explainer import DecisionExplainer
from src.explainability.score_explainer import ScoreExplainer
from src.factor_confidence.confidence_engine import ConfidenceEngine
from src.knowledge_base.kb_store import DEFAULT_KB_STORE
from strategy.strategic_score_engine import calculate_strategic_score
from src.evidence.evidence_chain_builder import EvidenceChainBuilder


@dataclass(frozen=True)
class ResearchDecision:
    """Standard research decision output."""

    theme_exposure: Mapping[str, float] = field(default_factory=dict)
    catalyst_strength: float = 0.0
    order_confirmation_level: float = 0.0
    strategic_score: float = 0.0
    research_conclusion: str = ""
    risk_summary: str = ""
    decision_action: str = "WATCH"
    overall_confidence: float = 1.0
    evidence_refs: Mapping[str, Any] = field(default_factory=dict)
    score_explanation: Mapping[str, Any] = field(default_factory=dict)
    decision_explanation: Mapping[str, Any] = field(default_factory=dict)
    factor_confidences: Mapping[str, Any] = field(default_factory=dict)


class ResearchEngine:
    """Generate research decisions from FactorInput."""

    def __init__(self) -> None:
        self.registry = DEFAULT_FACTOR_REGISTRY
        self.confidence_engine = ConfidenceEngine()

    def _clamp_0_100(self, value: float) -> float:
        return max(0.0, min(100.0, value))

    def _theme_exposure(self, factor_input: Mapping[str, Any]) -> dict[str, float]:
        return {
            "tau_factor_score": self._clamp_0_100(float(factor_input.get("tau_factor_score", 0.0))),
            "supernode_score": self._clamp_0_100(float(factor_input.get("supernode_score", 0.0))),
            "domestic_substitution_score": self._clamp_0_100(float(factor_input.get("domestic_substitution_score", 0.0))),
            "advanced_packaging_score": self._clamp_0_100(float(factor_input.get("advanced_packaging_score", 0.0))),
            "advanced_material_score": self._clamp_0_100(float(factor_input.get("advanced_material_score", 0.0))),
        }

    def _calculate_factor_scores(self, factor_input: Mapping[str, Any]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for factor_name in self.registry.list_factor_names():
            if factor_name == "order_confirmation_score":
                scores[factor_name] = self._clamp_0_100(
                    float(factor_input.get("new_orders", 0.0)) * 0.28
                    + float(factor_input.get("capacity_expansion", 0.0)) * 0.15
                    + float(factor_input.get("management_guidance", 0.0)) * 0.17
                    + float(factor_input.get("customer_verification", 0.0)) * 0.20
                    + float(factor_input.get("revenue_acceleration", 0.0)) * 0.20
                )
                continue

            source_field = factor_name
            scores[factor_name] = self._clamp_0_100(float(factor_input.get(source_field, 0.0)))
        return scores

    def _catalyst_strength(self, factor_input: Mapping[str, Any]) -> float:
        news_signal = float(factor_input.get("news_signal_strength", 0.0))
        order_level = float(factor_input.get("new_orders", 0.0))
        guidance = float(factor_input.get("management_guidance", 0.0))
        base = (news_signal * 0.3) + (order_level * 0.4) + (guidance * 0.3)
        return self._clamp_0_100(base)

    def _order_confirmation_level(self, factor_input: Mapping[str, Any], factor_scores: Mapping[str, float]) -> float:
        if "order_confirmation_score" in factor_scores:
            return self._clamp_0_100(float(factor_scores["order_confirmation_score"]))
        order_level = float(factor_input.get("new_orders", 0.0))
        customer_verification = float(factor_input.get("customer_verification", 0.0))
        revenue_acceleration = float(factor_input.get("revenue_acceleration", 0.0))
        capacity_expansion = float(factor_input.get("capacity_expansion", 0.0))
        base = (
            order_level * 0.3
            + customer_verification * 0.3
            + revenue_acceleration * 0.2
            + capacity_expansion * 0.2
        )
        return self._clamp_0_100(base)

    def _research_conclusion(self, strategic_score: float, catalyst_strength: float, order_level: float) -> str:
        if strategic_score >= 80 and order_level >= 60:
            return "主题强度高，订单验证较明确，适合继续作为重点研究对象。"
        if strategic_score >= 65 and catalyst_strength >= 50:
            return "主题处于中高强度区间，具备持续跟踪价值。"
        if strategic_score >= 50:
            return "主题仍在观察区间，需要继续验证催化剂和订单兑现。"
        return "主题强度偏弱，当前以基础观察为主。"

    def _risk_summary(self, factor_input: Mapping[str, Any], factor_scores: Mapping[str, float]) -> str:
        risks: list[str] = []
        if float(factor_input.get("domestic_substitution_score", 0.0)) < 40:
            risks.append("国产替代强度不足")
        if float(factor_input.get("advanced_packaging_score", 0.0)) < 40:
            risks.append("先进封装暴露较弱")
        if float(factor_scores.get("order_confirmation_score", 0.0)) < 40:
            risks.append("订单验证仍需跟踪")
        if float(factor_input.get("news_signal_strength", 0.0)) < 35:
            risks.append("新闻催化偏弱")
        if not risks:
            return "当前未见明显结构性风险，但仍需持续跟踪外部验证。"
        return "；".join(risks)

    def _overall_confidence(self, factor_input: Mapping[str, Any]) -> float:
        factor_confidences = factor_input.get("factor_confidences", {})
        if isinstance(factor_confidences, Mapping):
            scores = [
                float(item.get("final_confidence", 0.0))
                for item in factor_confidences.values()
                if isinstance(item, Mapping)
            ]
            if scores:
                return self._clamp_0_100(sum(scores) / len(scores)) / 100.0
        financial = factor_input.get("financial_summary", {})
        if isinstance(financial, Mapping):
            if "confidence_score" in financial:
                return self._clamp_0_100(float(financial.get("confidence_score", 0.0))) / 100.0
            confidence_level = str(financial.get("confidence_level", "")).lower()
            return {
                "high": 1.0,
                "medium": 0.75,
                "low": 0.35,
            }.get(confidence_level, 0.0)
        return 0.0

    def _core_financial_invalid(self, factor_input: Mapping[str, Any]) -> bool:
        financial = factor_input.get("financial_summary", {})
        if not isinstance(financial, Mapping):
            return True
        cross_validation = financial.get("cross_validation_result", {})
        field_results = cross_validation.get("field_results", {}) if isinstance(cross_validation, Mapping) else {}
        if not field_results:
            return False
        for item in field_results.values():
            if isinstance(item, Mapping) and "INVALID" in str(item.get("validation_status", "")):
                return True
        return all(
            isinstance(item, Mapping) and "both_sources_missing" in item.get("conflict_flags", [])
            for item in field_results.values()
        )

    def _decision_action(self, strategic_score: float, overall_confidence: float, core_invalid: bool) -> str:
        if core_invalid:
            return "AVOID" if strategic_score < 50 else "REVIEW"
        if overall_confidence < 0.65:
            return "WATCH"
        if strategic_score >= 75:
            return "BUY"
        if strategic_score >= 60:
            return "REVIEW"
        return "WATCH"

    def analyze(self, factor_input: Mapping[str, Any]) -> ResearchDecision:
        """Convert FactorInput into a standardized research decision."""

        factor_scores = self._calculate_factor_scores(factor_input)
        factor_confidences: dict[str, Any] = {}
        for factor_name in self.registry.list_factor_names():
            factor_conf = self.confidence_engine.evaluate({**factor_input, **factor_scores}, factor_name)
            factor_confidences[factor_name] = {
                "symbol": factor_conf.symbol,
                "period": factor_conf.period,
                "factor_name": factor_conf.factor_name,
                "validation_confidence": factor_conf.validation_confidence,
                "provider_confidence": factor_conf.provider_confidence,
                "completeness_confidence": factor_conf.completeness_confidence,
                "stability_confidence": factor_conf.stability_confidence,
                "final_confidence": factor_conf.final_confidence,
                "warnings": list(factor_conf.warnings),
                "confidence_breakdown": factor_conf.confidence_breakdown,
            }
        strategic_result = calculate_strategic_score({**factor_input, **factor_scores, "factor_confidences": factor_confidences})
        evidence_chain = EvidenceChainBuilder().from_factor_input({**factor_input, **factor_scores, "factor_confidences": factor_confidences})
        score_explanation = ScoreExplainer().explain(
            {**factor_input, **factor_scores, "factor_confidences": factor_confidences},
            strategic_result.strategic_score,
            symbol=str(factor_input.get("company_code", factor_input.get("code", "UNKNOWN"))),
            period=str(factor_input.get("period", "TTM")),
        )
        theme_exposure = self._theme_exposure(factor_input)
        catalyst_strength = self._catalyst_strength(factor_input)
        order_confirmation_level = self._order_confirmation_level(factor_input, factor_scores)
        strategic_score = float(strategic_result.strategic_score)
        overall_confidence = self._overall_confidence(factor_input)
        core_invalid = self._core_financial_invalid(factor_input)
        decision_action = self._decision_action(strategic_score, overall_confidence, core_invalid)
        if overall_confidence < 0.65 and decision_action == "BUY":
            decision_action = "WATCH"
        if core_invalid and decision_action == "BUY":
            decision_action = "REVIEW" if strategic_score >= 50 else "AVOID"
        research_conclusion = self._research_conclusion(
            strategic_score=strategic_score,
            catalyst_strength=catalyst_strength,
            order_level=order_confirmation_level,
        )
        if decision_action == "WATCH" and overall_confidence < 0.65:
            research_conclusion = f"{research_conclusion} 由于置信度偏低，决策上限收敛为 WATCH。"
        if core_invalid:
            research_conclusion = f"{research_conclusion} 核心财务因子存在无效或缺失信号，建议降级处理。"
        risk_summary = self._risk_summary(factor_input, factor_scores)
        decision_explanation = DecisionExplainer().explain(
            symbol=str(factor_input.get("company_code", factor_input.get("code", "UNKNOWN"))),
            period=str(factor_input.get("period", "TTM")),
            strategic_score=strategic_result.strategic_score,
            research_decision={
                "decision_action": decision_action,
                "overall_confidence": round(overall_confidence, 2),
            },
            evidence_chain=evidence_chain,
            score_explanation=score_explanation,
        )
        return ResearchDecision(
            theme_exposure=theme_exposure,
            catalyst_strength=round(catalyst_strength, 2),
            order_confirmation_level=round(order_confirmation_level, 2),
            strategic_score=round(strategic_score, 2),
            research_conclusion=research_conclusion,
            risk_summary=risk_summary,
            decision_action=decision_action,
            overall_confidence=round(overall_confidence, 2),
            evidence_refs={"evidence_chain": evidence_chain},
            score_explanation={"score_explanation": score_explanation},
            decision_explanation={"decision_explanation": decision_explanation},
            factor_confidences=factor_confidences,
        )


@lru_cache(maxsize=None)
def run_research_pipeline(company_code: str) -> dict[str, Any]:
    """Run the end-to-end research pipeline for one company code."""

    mapping = DataMappingLayer()
    factor_input = mapping.build_factor_input(company_code)
    engine = ResearchEngine()
    factor_scores = engine._calculate_factor_scores(factor_input)
    strategic_result = calculate_strategic_score({**factor_input, **factor_scores})
    decision = engine.analyze({**factor_input, **factor_scores})
    evidence_chain = decision.evidence_refs.get("evidence_chain") if isinstance(decision.evidence_refs, Mapping) else None
    DEFAULT_KB_STORE.add_record(
        {
            "symbol": company_code,
            "period": str(factor_input.get("period", "TTM")),
            "strategic_score": decision.strategic_score,
            "final_decision": decision.decision_action,
            "confidence_score": decision.overall_confidence,
            "evidence_refs": decision.evidence_refs,
            "explanation_summary": decision.research_conclusion,
            "portfolio_bucket": "",
            "recommended_weight": 0.0,
            "risk_level": "",
            "rebalance_action": "",
            "backtest_metrics": {},
        }
    )

    return {
        "company_code": company_code,
        "factor_input_summary": {
            "name": factor_input.get("name", "UNKNOWN"),
            "theme": factor_input.get("theme", "UNKNOWN"),
            "provider_summary": {
                field_name: {
                    "provider_used": factor_input[field_name]["provider_used"],
                    "fallback_used": factor_input[field_name]["fallback_used"],
                    "timestamp": factor_input[field_name]["timestamp"],
                }
                for field_name in (
                    "company_basic_info",
                    "financial_summary",
                    "order_signals",
                    "news_signals",
                    "theme_signals",
                )
            },
        },
        "factor_scores": factor_scores,
        "strategic_score": strategic_result.strategic_score,
        "theme_exposure": dict(decision.theme_exposure),
        "catalyst_strength": decision.catalyst_strength,
        "order_confirmation_level": decision.order_confirmation_level,
        "risk_summary": decision.risk_summary,
        "research_conclusion": decision.research_conclusion,
        "evidence_refs": decision.evidence_refs,
        "evidence_summary": EvidenceChainBuilder().to_dict(evidence_chain) if evidence_chain is not None else {},
        "score_explanation": decision.score_explanation,
        "decision_explanation": decision.decision_explanation,
        "factor_confidences": decision.factor_confidences,
    }


def analyze_research_decision(factor_input: Mapping[str, Any]) -> ResearchDecision:
    """Convenience wrapper for one-off research analysis."""

    return ResearchEngine().analyze(factor_input)
