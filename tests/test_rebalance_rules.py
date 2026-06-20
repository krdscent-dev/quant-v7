from __future__ import annotations

import unittest

from src.rebalancing.rebalance_rules import RebalanceRules


class RebalanceRulesTest(unittest.TestCase):
    def test_action_rules(self) -> None:
        rules = RebalanceRules()
        self.assertEqual(
            rules.adjusted_target_weight(bucket="CORE", target_weight=0.08, confidence_score=0.95, risk_score=0.20)[0],
            0.08,
        )
        self.assertEqual(
            rules.adjusted_target_weight(bucket="WATCHLIST", target_weight=0.08, confidence_score=0.95, risk_score=0.20)[0],
            0.0,
        )
        self.assertEqual(
            rules.adjusted_target_weight(bucket="CORE", target_weight=0.08, confidence_score=0.55, risk_score=0.20)[0],
            0.0,
        )
        self.assertEqual(
            rules.adjusted_target_weight(bucket="CORE", target_weight=0.08, confidence_score=0.95, risk_score=0.90)[0],
            0.0,
        )
        self.assertEqual(
            rules.adjusted_target_weight(bucket="CORE", target_weight=0.08, confidence_score=0.65, risk_score=0.80)[0],
            0.03,
        )

    def test_determine_action(self) -> None:
        rules = RebalanceRules()
        self.assertEqual(rules.determine_action(current_weight=0.0, target_weight=0.04, bucket="CORE", confidence_score=0.9, risk_score=0.2), "BUY")
        self.assertEqual(rules.determine_action(current_weight=0.02, target_weight=0.05, bucket="CORE", confidence_score=0.9, risk_score=0.2), "ADD")
        self.assertEqual(rules.determine_action(current_weight=0.06, target_weight=0.04, bucket="CORE", confidence_score=0.9, risk_score=0.2), "REDUCE")
        self.assertEqual(rules.determine_action(current_weight=0.04, target_weight=0.0, bucket="CORE", confidence_score=0.9, risk_score=0.2), "SELL")
        self.assertEqual(rules.determine_action(current_weight=0.040, target_weight=0.045, bucket="CORE", confidence_score=0.9, risk_score=0.2), "HOLD")
        self.assertEqual(rules.determine_action(current_weight=0.02, target_weight=0.0, bucket="WATCHLIST", confidence_score=0.9, risk_score=0.2), "SELL")
        self.assertEqual(rules.priority("SELL", critical_risk=True, critical_affected=True), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
