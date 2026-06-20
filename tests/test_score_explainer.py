from __future__ import annotations

import unittest

from src.explainability.score_explainer import ScoreExplainer


class ScoreExplainerTest(unittest.TestCase):
    def test_top_positive_and_negative_factors(self) -> None:
        payload = {
            "tau_factor_score": 90,
            "supernode_score": 80,
            "domestic_substitution_score": 70,
            "advanced_packaging_score": 60,
            "order_confirmation_score": 50,
            "advanced_material_score": 40,
            "confidence_score": 1.0,
        }
        explanation = ScoreExplainer().explain(payload, 72.5, "000001.SZ", "TTM")
        self.assertEqual(explanation.top_positive_factors[0].factor_name, "tau_factor_score")
        self.assertTrue(len(explanation.top_negative_factors) > 0)
        self.assertIn("000001.SZ", explanation.summary)

