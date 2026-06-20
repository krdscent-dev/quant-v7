from __future__ import annotations

import unittest

from src.rebalancing.rebalance_contract import RebalanceAction, RebalancePlan
from src.rebalancing.rebalance_explainer import RebalanceExplainer


class RebalanceExplainerTest(unittest.TestCase):
    def test_explanation_text(self) -> None:
        explainer = RebalanceExplainer()
        action = RebalanceAction(
            symbol="NVDA",
            current_weight=0.00,
            target_weight=0.092,
            delta_weight=0.092,
            action="BUY",
            reason="Strategic Score 高",
            priority=4,
        )
        self.assertIn("买入", explainer.explain_action(action))
        plan = RebalancePlan(
            period="TTM",
            actions=[action],
            total_buy_weight=0.092,
            total_sell_weight=0.0,
            turnover=0.046,
            summary="",
        )
        self.assertIn("调仓建议共 1 项", explainer.explain_plan(plan))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
