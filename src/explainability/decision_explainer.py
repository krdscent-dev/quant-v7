"""Decision explanation builder."""

from __future__ import annotations

from typing import Any, Mapping

from .explanation_contract import DecisionExplanation, FactorContribution, ScoreExplanation


class DecisionExplainer:
    """Turn score and evidence objects into readable decision reasons."""

    def _evidence_summary(self, evidence_chain: Any) -> tuple[list[str], list[str], float]:
        if evidence_chain is None:
            return [], [], 0.0
        nodes = getattr(evidence_chain, "nodes", []) if not isinstance(evidence_chain, Mapping) else evidence_chain.get("nodes", [])
        warnings = list(getattr(evidence_chain, "warnings", []) if not isinstance(evidence_chain, Mapping) else evidence_chain.get("warnings", []))
        confidence = float(getattr(evidence_chain, "overall_confidence", 0.0) if not isinstance(evidence_chain, Mapping) else evidence_chain.get("overall_confidence", 0.0))
        supporting = []
        for node in nodes[:5]:
            name = node.get("name") if isinstance(node, Mapping) else getattr(node, "name", "UNKNOWN")
            confidence_score = node.get("confidence_score") if isinstance(node, Mapping) else getattr(node, "confidence_score", 0.0)
            supporting.append(f"{name}:{float(confidence_score):.2f}")
        return supporting, warnings, confidence

    def explain(
        self,
        *,
        symbol: str,
        period: str,
        strategic_score: float,
        research_decision: Any,
        evidence_chain: Any = None,
        score_explanation: ScoreExplanation | None = None,
    ) -> DecisionExplanation:
        final_decision = str(getattr(research_decision, "decision_action", research_decision.get("decision_action", "WATCH")) if not isinstance(research_decision, str) else research_decision)
        overall_confidence = float(getattr(research_decision, "overall_confidence", 0.0) if not isinstance(research_decision, Mapping) else research_decision.get("overall_confidence", 0.0))
        supporting_factors: list[str] = []
        risk_factors: list[str] = []
        decision_reasons: list[str] = []

        if score_explanation is not None:
            supporting_factors.extend(item.factor_name for item in score_explanation.top_positive_factors[:3])
            risk_factors.extend(item.factor_name for item in score_explanation.top_negative_factors[:3])
            decision_reasons.append(score_explanation.summary)

        evidence_supporting, evidence_warnings, evidence_confidence = self._evidence_summary(evidence_chain)
        supporting_factors.extend(evidence_supporting)
        if evidence_warnings:
            risk_factors.extend(evidence_warnings)

        if final_decision == "BUY":
            decision_reasons.append("战略评分与证据链均显示强度较高，且验证风险可控。")
        elif final_decision == "WATCH":
            decision_reasons.append("当前仍处观察阶段，主要原因是置信度或验证强度不足。")
        elif final_decision == "REVIEW":
            decision_reasons.append("需要进一步核对财务验证与催化兑现情况。")
        elif final_decision == "AVOID":
            decision_reasons.append("核心验证不足或冲突过强，暂不纳入重点观察。")

        if overall_confidence < 0.65:
            risk_factors.append("overall_confidence_below_threshold")
            if final_decision == "BUY":
                final_decision = "WATCH"

        summary = (
            f"{symbol} / {period} 的最终决策为 {final_decision}。"
            f" 战略分 {strategic_score:.2f}，证据置信度 {evidence_confidence:.2f}，整体置信度 {overall_confidence:.2f}。"
        )

        return DecisionExplanation(
            symbol=symbol,
            period=period,
            final_decision=final_decision,
            decision_reasons=decision_reasons,
            supporting_factors=supporting_factors[:8],
            risk_factors=risk_factors[:8],
            confidence_score=round(max(overall_confidence, evidence_confidence), 2),
            summary=summary,
        )
