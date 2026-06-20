from __future__ import annotations

import unittest

from src.explainability.contribution_analyzer import ContributionAnalyzer


class ContributionAnalyzerTest(unittest.TestCase):
    def test_contribution_score_calculation(self) -> None:
        payload = {
            "tau_factor_score": 80,
            "supernode_score": 70,
            "domestic_substitution_score": 60,
            "advanced_packaging_score": 50,
            "order_confirmation_score": 40,
            "advanced_material_score": 30,
            "confidence_score": 0.5,
        }
        contributions = ContributionAnalyzer().analyze(payload)
        tau = next(item for item in contributions if item.factor_name == "tau_factor_score")
        self.assertAlmostEqual(tau.contribution_score, 8.0, places=2)

    def test_contribution_sorting(self) -> None:
        payload = {
            "tau_factor_score": 10,
            "supernode_score": 90,
            "domestic_substitution_score": 60,
            "advanced_packaging_score": 50,
            "order_confirmation_score": 40,
            "advanced_material_score": 30,
            "confidence_score": 1.0,
        }
        contributions = ContributionAnalyzer().analyze(payload)
        self.assertEqual(contributions[0].factor_name, "supernode_score")

