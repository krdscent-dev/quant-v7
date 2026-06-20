from __future__ import annotations

import unittest

from src.evidence.evidence_chain_builder import EvidenceChainBuilder
from src.evidence.evidence_formatter import format_evidence_summary


class EvidenceFormatterTest(unittest.TestCase):
    def test_format_summary_contains_key_sections(self) -> None:
        payload = {
            "company_code": "000001.SZ",
            "company_basic_info": {"data": {"name": "Mock Company"}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "financial_summary": {"data": {"营业收入": 1.0}, "provider_used": "MockDataProvider", "validation_status": "MINOR_DIFF", "confidence_score": 0.75, "cross_validation_result": {"field_results": {}}},
            "order_signals": {"data": {"order_landing_score": 20}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "news_signals": {"data": {"guidance_signal": 10}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
            "theme_signals": {"data": {"theme": "AI算力", "tau_factor_score": 30}, "provider_used": "MockDataProvider", "validation_status": "PASS", "confidence_score": 1.0},
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
        summary = format_evidence_summary(chain)
        self.assertIn("symbol:", summary)
        self.assertIn("key_evidence:", summary)
        self.assertIn("warnings:", summary)

