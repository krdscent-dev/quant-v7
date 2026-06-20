from __future__ import annotations

import unittest

from src.factor_confidence.confidence_calculator import ConfidenceCalculator


class ConfidenceCalculatorTest(unittest.TestCase):
    def test_validation_mapping(self) -> None:
        calc = ConfidenceCalculator()
        self.assertAlmostEqual(calc.validation_score("PASS"), 1.0, places=2)
        self.assertAlmostEqual(calc.validation_score("MINOR_DIFF"), 0.85, places=2)
        self.assertAlmostEqual(calc.validation_score("MISSING"), 0.60, places=2)
        self.assertAlmostEqual(calc.validation_score("MAJOR_DIFF"), 0.35, places=2)
        self.assertAlmostEqual(calc.validation_score("INVALID"), 0.0, places=2)

    def test_final_confidence_formula(self) -> None:
        calc = ConfidenceCalculator()
        confidence = calc.calculate_final_confidence(
            validation_confidence=1.0,
            provider_confidence=0.9,
            completeness_confidence=0.8,
            stability_confidence=0.7,
        )
        self.assertAlmostEqual(confidence, 0.90, places=2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
