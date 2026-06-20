from __future__ import annotations

import unittest

from src.evidence.evidence_chain_builder import EvidenceChainBuilder
from src.explainability.decision_explainer import DecisionExplainer
from src.explainability.score_explainer import ScoreExplainer


class DecisionExplainerTest(unittest.TestCase):
    def _payload(self, confidence_score: float, validation_status: str = "PASS") -> dict:
        return {
            "company_code": "000001.SZ",
            "period": "TTM",
            "company_basic_info": {"data": {"name": "Mock Company"}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "financial_summary": {"data": {"营业收入": 1.0}, "provider_used": "MockDataProvider", "validation_status": validation_status, "confidence_score": confidence_score, "cross_validation_result": {"field_results": {}}},
            "order_signals": {"data": {"order_landing_score": 20}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "news_signals": {"data": {"guidance_signal": 10}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "theme_signals": {"data": {"theme": "AI算力", "tau_factor_score": 30}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "tau_factor_score": 30,
            "supernode_score": 20,
            "domestic_substitution_score": 10,
            "advanced_packaging_score": 5,
            "advanced_material_score": 2,
            "order_confirmation_score": 12,
            "confidence_score": confidence_score,
            "validation_status": validation_status,
        }

    def test_buy_explanation(self) -> None:
        payload = self._payload(0.95)
        chain = EvidenceChainBuilder().from_factor_input(payload)
        score_exp = ScoreExplainer().explain(payload, 82.0, "000001.SZ", "TTM")
        decision = DecisionExplainer().explain(
            symbol="000001.SZ",
            period="TTM",
            strategic_score=82.0,
            research_decision={"decision_action": "BUY", "overall_confidence": 0.95},
            evidence_chain=chain,
            score_explanation=score_exp,
        )
        self.assertEqual(decision.final_decision, "BUY")
        self.assertTrue(decision.decision_reasons)

    def test_watch_explanation(self) -> None:
        payload = self._payload(0.4)
        chain = EvidenceChainBuilder().from_factor_input(payload)
        score_exp = ScoreExplainer().explain(payload, 55.0, "000001.SZ", "TTM")
        decision = DecisionExplainer().explain(
            symbol="000001.SZ",
            period="TTM",
            strategic_score=55.0,
            research_decision={"decision_action": "WATCH", "overall_confidence": 0.4},
            evidence_chain=chain,
            score_explanation=score_exp,
        )
        self.assertEqual(decision.final_decision, "WATCH")

    def test_review_explanation(self) -> None:
        payload = self._payload(0.8, validation_status="MINOR_DIFF")
        chain = EvidenceChainBuilder().from_factor_input(payload)
        score_exp = ScoreExplainer().explain(payload, 66.0, "000001.SZ", "TTM")
        decision = DecisionExplainer().explain(
            symbol="000001.SZ",
            period="TTM",
            strategic_score=66.0,
            research_decision={"decision_action": "REVIEW", "overall_confidence": 0.8},
            evidence_chain=chain,
            score_explanation=score_exp,
        )
        self.assertEqual(decision.final_decision, "REVIEW")

    def test_avoid_explanation(self) -> None:
        payload = self._payload(0.2, validation_status="INVALID")
        chain = EvidenceChainBuilder().from_factor_input(payload)
        score_exp = ScoreExplainer().explain(payload, 30.0, "000001.SZ", "TTM")
        decision = DecisionExplainer().explain(
            symbol="000001.SZ",
            period="TTM",
            strategic_score=30.0,
            research_decision={"decision_action": "AVOID", "overall_confidence": 0.2},
            evidence_chain=chain,
            score_explanation=score_exp,
        )
        self.assertEqual(decision.final_decision, "AVOID")

