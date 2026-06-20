from __future__ import annotations

import unittest

from src.risk.risk_rules import RiskRules


class RiskRulesTest(unittest.TestCase):
    def test_position_limit(self) -> None:
        rules = RiskRules()
        self.assertEqual(rules.low_confidence_limit(0.59, 0.05), 0.0)
        self.assertLessEqual(rules.low_confidence_limit(0.69, 0.05), 0.03)
        self.assertEqual(rules.high_risk_limit(0.86, 0.05), 0.0)
        self.assertLessEqual(rules.high_risk_limit(0.75, 0.05), 0.03)

    def test_risk_score_and_level(self) -> None:
        rules = RiskRules()
        score = rules.total_risk_score(0.2, 0.3, 0.4, 0.5)
        self.assertGreater(score, 0.0)
        self.assertEqual(rules.risk_level(0.2), "LOW")
        self.assertEqual(rules.risk_level(0.4), "MEDIUM")
        self.assertEqual(rules.risk_level(0.6), "HIGH")
        self.assertEqual(rules.risk_level(0.9), "CRITICAL")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
