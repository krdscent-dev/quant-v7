from __future__ import annotations

import unittest

from src.rebalancing.rebalance_engine import RebalanceEngine


class RebalanceEngineTest(unittest.TestCase):
    def test_plan_generation(self) -> None:
        engine = RebalanceEngine()
        position_snapshot = {
            "recommendations": [
                {"symbol": "A", "bucket": "CORE", "recommended_weight": 0.08, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "A"},
                {"symbol": "B", "bucket": "CORE", "recommended_weight": 0.08, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "B"},
                {"symbol": "C", "bucket": "CORE", "recommended_weight": 0.08, "confidence_score": 0.55, "risk_score": 0.20, "explanation": "C"},
                {"symbol": "D", "bucket": "CORE", "recommended_weight": 0.08, "confidence_score": 0.95, "risk_score": 0.90, "explanation": "D"},
                {"symbol": "E", "bucket": "WATCHLIST", "recommended_weight": 0.0, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "E"},
                {"symbol": "F", "bucket": "EXCLUDED", "recommended_weight": 0.0, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "F"},
                {"symbol": "G", "bucket": "CORE", "recommended_weight": 0.04, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "G"},
                {"symbol": "H", "bucket": "CORE", "recommended_weight": 0.08, "confidence_score": 0.95, "risk_score": 0.20, "explanation": "H"},
            ]
        }
        portfolio_snapshot = {
            "ranked_candidates": [
                {"symbol": item["symbol"], "bucket": item["bucket"], "theme": "AI Computing", "strategic_score": 80, "confidence_score": item["confidence_score"], "total_score": 80}
                for item in position_snapshot["recommendations"]
            ]
        }
        risk_report = {
            "risk_level": "CRITICAL",
            "checks": [
                {"passed": False, "severity": "HIGH", "affected_symbols": ["D", "H"]},
            ],
            "warnings": ["行业集中度偏高"],
            "suggested_actions": ["降低集中度"],
        }
        current_holdings = [
            {"symbol": "A", "current_weight": 0.0, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "B", "current_weight": 0.05, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "C", "current_weight": 0.0, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "D", "current_weight": 0.05, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "E", "current_weight": 0.02, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "F", "current_weight": 0.0, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "G", "current_weight": 0.04, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
            {"symbol": "H", "current_weight": 0.10, "market_value": 0, "cost_basis": 0, "unrealized_return": 0},
        ]

        plan = engine.build_plan(position_snapshot, risk_report, portfolio_snapshot, current_holdings)
        actions = {item.symbol: item for item in plan.actions}

        self.assertEqual(actions["A"].action, "BUY")
        self.assertEqual(actions["B"].action, "ADD")
        self.assertEqual(actions["C"].action, "WATCH")
        self.assertEqual(actions["D"].action, "SELL")
        self.assertEqual(actions["E"].action, "SELL")
        self.assertEqual(actions["F"].action, "WATCH")
        self.assertEqual(actions["G"].action, "HOLD")
        self.assertEqual(actions["H"].action, "REDUCE")
        self.assertGreater(plan.total_buy_weight, 0.0)
        self.assertGreater(plan.total_sell_weight, 0.0)
        self.assertAlmostEqual(plan.turnover, 0.10, places=2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
