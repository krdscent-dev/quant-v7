from __future__ import annotations

import unittest

from src.provider_trust.trust_registry import TrustProfile, TrustRegistry


class TrustRegistryTest(unittest.TestCase):
    def test_registry_store_and_rank(self) -> None:
        registry = TrustRegistry()
        registry.register_profile(TrustProfile("akshare", 100, 8, 0.91, 2, 96, 100, 4))
        registry.register_profile(TrustProfile("tushare", 100, 5, 0.97, 1, 98, 100, 2))
        scores = registry.list_scores()
        self.assertEqual(scores[0].provider_name, "tushare")
        self.assertGreater(scores[0].overall_score, scores[1].overall_score)

