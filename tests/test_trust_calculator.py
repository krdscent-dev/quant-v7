from __future__ import annotations

import unittest

from src.provider_trust.trust_calculator import TrustCalculator


class TrustCalculatorTest(unittest.TestCase):
    def test_trust_score_calculation(self) -> None:
        calc = TrustCalculator()
        score = calc.calculate_provider_trust(
            "akshare",
            total_fields=100,
            missing_fields=5,
            agreement_ratio=0.95,
            days_since_update=1,
            success_count=98,
            total_count=100,
            anomaly_count=2,
        )
        self.assertAlmostEqual(score.overall_score, 0.97, places=2)

    def test_coverage_score(self) -> None:
        calc = TrustCalculator()
        self.assertAlmostEqual(calc.calculate_coverage_score(100, 5), 0.95, places=2)

    def test_consistency_score(self) -> None:
        calc = TrustCalculator()
        self.assertAlmostEqual(calc.calculate_consistency_score(0.95), 0.95, places=2)

    def test_freshness_score(self) -> None:
        calc = TrustCalculator()
        self.assertAlmostEqual(calc.calculate_freshness_score(1), 1.0, places=2)
        self.assertAlmostEqual(calc.calculate_freshness_score(3), 0.95, places=2)
        self.assertAlmostEqual(calc.calculate_freshness_score(7), 0.90, places=2)
        self.assertAlmostEqual(calc.calculate_freshness_score(30), 0.80, places=2)
        self.assertAlmostEqual(calc.calculate_freshness_score(31), 0.50, places=2)

    def test_stability_and_anomaly_score(self) -> None:
        calc = TrustCalculator()
        self.assertAlmostEqual(calc.calculate_stability_score(98, 100), 0.98, places=2)
        self.assertAlmostEqual(calc.calculate_anomaly_score(2, 100), 0.98, places=2)

