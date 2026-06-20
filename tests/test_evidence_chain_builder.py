from __future__ import annotations

import unittest

from src.evidence.evidence_chain_builder import EvidenceChainBuilder


class EvidenceChainBuilderTest(unittest.TestCase):
    def test_build_chain_from_factor_input(self) -> None:
        payload = {
            "company_code": "000001.SZ",
            "period": "TTM",
            "company_basic_info": {
                "data": {"name": "Mock Company"},
                "provider_used": "MockDataProvider",
                "validation_status": "PASS",
                "confidence_score": 1.0,
            },
            "financial_summary": {
                "data": {"营业收入": 1.0},
                "provider_used": "MockDataProvider",
                "validation_status": "MINOR_DIFF",
                "confidence_score": 0.75,
                "cross_validation_result": {
                    "field_results": {
                        "营业收入": {
                            "validation_status": "MINOR_DIFF",
                            "confidence_level": "medium",
                            "conflict_flags": ["tushare_missing"],
                        }
                    }
                },
            },
            "order_signals": {
                "data": {"order_landing_score": 20},
                "provider_used": "MockDataProvider",
                "validation_status": "PASS",
                "confidence_score": 1.0,
            },
            "news_signals": {
                "data": {"guidance_signal": 10},
                "provider_used": "MockDataProvider",
                "validation_status": "PASS",
                "confidence_score": 1.0,
            },
            "theme_signals": {
                "data": {"theme": "AI算力", "tau_factor_score": 30},
                "provider_used": "MockDataProvider",
                "validation_status": "PASS",
                "confidence_score": 1.0,
            },
            "tau_factor_score": 30,
            "supernode_score": 20,
            "domestic_substitution_score": 10,
            "advanced_packaging_score": 5,
            "advanced_material_score": 2,
            "order_confirmation_score": 12,
            "confidence_score": 0.75,
            "validation_status": "MINOR_DIFF",
        }
        chain = EvidenceChainBuilder().from_factor_input(payload)
        self.assertEqual(chain.symbol, "000001.SZ")
        self.assertGreater(len(chain.nodes), 0)
        self.assertGreater(chain.overall_confidence, 0.0)
        self.assertTrue(any(node.node_type == "VALIDATION_RESULT" for node in chain.nodes))

    def test_overall_confidence_aggregates(self) -> None:
        payload = {
            "company_code": "000001.SZ",
            "company_basic_info": {"data": {}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "financial_summary": {"data": {}, "provider_used": "MockDataProvider", "validation_status": "INVALID", "confidence_score": 0.0, "cross_validation_result": {"field_results": {}}},
            "order_signals": {"data": {}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "news_signals": {"data": {}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "theme_signals": {"data": {}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
        }
        chain = EvidenceChainBuilder().from_factor_input(payload)
        self.assertLess(chain.overall_confidence, 1.0)
        self.assertTrue(chain.warnings)

