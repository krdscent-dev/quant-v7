from __future__ import annotations

import unittest

from core.research_engine import ResearchEngine


class ResearchDecisionEvidenceTest(unittest.TestCase):
    def test_research_decision_retains_evidence_refs(self) -> None:
        payload = {
            "code": "000001.SZ",
            "name": "Mock Company",
            "theme": "AI算力",
            "tau_factor_score": 80,
            "supernode_score": 70,
            "domestic_substitution_score": 60,
            "advanced_packaging_score": 50,
            "advanced_material_score": 40,
            "new_orders": 60,
            "capacity_expansion": 50,
            "management_guidance": 55,
            "customer_verification": 60,
            "revenue_acceleration": 58,
            "news_signal_strength": 50,
            "financial_summary": {
                "confidence_score": 0.9,
                "confidence_level": "high",
                "validation_status": "PASS",
                "cross_validation_result": {"field_results": {}},
            },
        }
        decision = ResearchEngine().analyze(payload)
        self.assertIn("evidence_chain", decision.evidence_refs)
        self.assertGreaterEqual(decision.overall_confidence, 0.0)

    def test_low_confidence_blocks_buy(self) -> None:
        payload = {
            "code": "000001.SZ",
            "name": "Mock Company",
            "theme": "AI算力",
            "tau_factor_score": 80,
            "supernode_score": 70,
            "domestic_substitution_score": 60,
            "advanced_packaging_score": 50,
            "advanced_material_score": 40,
            "new_orders": 60,
            "capacity_expansion": 50,
            "management_guidance": 55,
            "customer_verification": 60,
            "revenue_acceleration": 58,
            "news_signal_strength": 50,
            "financial_summary": {
                "confidence_score": 0.2,
                "confidence_level": "low",
                "validation_status": "INVALID",
                "cross_validation_result": {"field_results": {}},
            },
        }
        decision = ResearchEngine().analyze(payload)
        self.assertIn(decision.decision_action, {"WATCH", "REVIEW", "AVOID"})
        self.assertNotEqual(decision.decision_action, "BUY")

