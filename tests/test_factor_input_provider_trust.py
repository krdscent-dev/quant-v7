from __future__ import annotations

import unittest

from core.data_mapping import DataMappingLayer


class FactorInputProviderTrustTest(unittest.TestCase):
    def test_factor_input_applies_provider_trust(self) -> None:
        mapping = DataMappingLayer()
        payload = mapping.build_factor_input("000001.SZ")
        financial = payload["financial_summary"]
        self.assertIn("provider_trust_score", financial)
        self.assertLessEqual(financial["confidence_score"], 1.0)

