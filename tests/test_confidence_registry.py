from __future__ import annotations

import unittest

from src.factor_confidence.confidence_contract import FactorConfidence
from src.factor_confidence.confidence_registry import ConfidenceRegistry


class ConfidenceRegistryTest(unittest.TestCase):
    def test_registry_history(self) -> None:
        registry = ConfidenceRegistry()
        item = FactorConfidence(
            symbol="000977.SZ",
            period="TTM",
            factor_name="tau_factor_score",
            validation_confidence=1.0,
            provider_confidence=0.9,
            completeness_confidence=0.8,
            stability_confidence=0.7,
            final_confidence=0.83,
        )
        registry.add(item)
        self.assertEqual(len(registry.get_history("tau_factor_score")), 1)
        self.assertEqual(registry.latest("tau_factor_score"), item)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
