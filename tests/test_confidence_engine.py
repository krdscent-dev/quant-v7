from __future__ import annotations

import unittest

from src.factor_confidence.confidence_engine import ConfidenceEngine


class ConfidenceEngineTest(unittest.TestCase):
    def test_evaluate_returns_factor_confidence(self) -> None:
        engine = ConfidenceEngine()
        result = engine.evaluate(
            {
                "company_code": "000977.SZ",
                "period": "TTM",
                "validation_status": "PASS",
                "financial_summary": {
                    "provider_trust_score": 0.95,
                    "mapped_financial_summary": {"营业收入": 1, "净利润": 1},
                    "missing_fields": [],
                },
            },
            "tau_factor_score",
        )
        self.assertEqual(result.factor_name, "tau_factor_score")
        self.assertGreater(result.final_confidence, 0.0)
        self.assertIsNotNone(result.confidence_breakdown)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
