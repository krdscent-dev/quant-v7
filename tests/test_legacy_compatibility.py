from __future__ import annotations

import unittest

from core.data_mapping import DataMappingLayer
from core.provider_router import ProviderRouter
from core.research_engine import ResearchEngine
from strategy.strategic_score_engine import calculate_strategic_score


class LegacyCompatibilityTest(unittest.TestCase):
    def test_provider_router_still_resolves(self) -> None:
        router = ProviderRouter()
        provider = router.get_provider_for_field("financial_summary")
        self.assertIsNotNone(provider)

    def test_data_mapping_still_builds_factor_input(self) -> None:
        payload = DataMappingLayer().build_factor_input("000001.SZ")
        self.assertIn("financial_summary", payload)
        self.assertIn("confidence_score", payload)

    def test_strategic_score_accepts_confidence(self) -> None:
        result = calculate_strategic_score(
            {
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
                "confidence_score": 0.5,
            }
        )
        self.assertLess(result.strategic_score, 100)
        self.assertIn("confidence_score", result.factor_breakdown)

    def test_research_engine_returns_decision(self) -> None:
        decision = ResearchEngine().analyze(
            {
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
                "financial_summary": {"confidence_score": 0.9, "confidence_level": "high", "validation_status": "PASS", "cross_validation_result": {"field_results": {}}},
            }
        )
        self.assertTrue(hasattr(decision, "decision_action"))
        self.assertTrue(hasattr(decision, "evidence_refs"))

