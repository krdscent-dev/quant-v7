from __future__ import annotations

import unittest

from core.research_engine import ResearchEngine
from strategy.strategic_score_engine import calculate_strategic_score


class ScoreConfidenceIntegrationTest(unittest.TestCase):
    def test_strategic_score_uses_final_confidence(self) -> None:
        result = calculate_strategic_score(
            {
                "code": "000977.SZ",
                "name": "示例公司",
                "theme": "AI算力",
                "tau_factor_score": 80,
                "supernode_score": 80,
                "domestic_substitution_score": 80,
                "advanced_packaging_score": 80,
                "advanced_material_score": 80,
                "new_orders": 80,
                "capacity_expansion": 80,
                "management_guidance": 80,
                "customer_verification": 80,
                "revenue_acceleration": 80,
                "factor_confidences": {
                    "tau_factor_score": {"final_confidence": 0.5},
                    "supernode_score": {"final_confidence": 0.5},
                    "domestic_substitution_score": {"final_confidence": 0.5},
                    "advanced_packaging_score": {"final_confidence": 0.5},
                    "order_confirmation_score": {"final_confidence": 0.5},
                    "advanced_material_score": {"final_confidence": 0.5},
                },
            }
        )
        self.assertLess(result.strategic_score, 80)

    def test_research_decision_confidence_guard(self) -> None:
        engine = ResearchEngine()
        decision = engine.analyze(
            {
                "company_code": "000977.SZ",
                "period": "TTM",
                "name": "示例公司",
                "theme": "AI算力",
                "tau_factor_score": 80,
                "supernode_score": 80,
                "domestic_substitution_score": 80,
                "advanced_packaging_score": 80,
                "advanced_material_score": 80,
                "new_orders": 80,
                "capacity_expansion": 80,
                "management_guidance": 80,
                "customer_verification": 80,
                "revenue_acceleration": 80,
                "financial_summary": {
                    "confidence_score": 0.4,
                    "provider_trust_score": 0.5,
                    "cross_validation_result": {
                        "field_results": {
                            "营业收入": {"validation_status": "INVALID", "conflict_flags": ["both_sources_missing"]}
                        }
                    },
                },
            }
        )
        self.assertIn(decision.decision_action, {"WATCH", "REVIEW", "AVOID"})
        self.assertLessEqual(decision.overall_confidence, 0.65)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
