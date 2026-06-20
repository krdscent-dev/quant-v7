from __future__ import annotations

import unittest

from src.risk.risk_management_engine import RiskManagementEngine


class RiskManagementEngineTest(unittest.TestCase):
    def test_report(self) -> None:
        engine = RiskManagementEngine()
        position_snapshot = {
            "recommendations": [
                {"symbol": "A", "bucket": "CORE", "recommended_weight": 0.13, "confidence_score": 0.8, "risk_score": 0.2},
                {"symbol": "B", "bucket": "SATELLITE", "recommended_weight": 0.05, "confidence_score": 0.55, "risk_score": 0.2},
                {"symbol": "C", "bucket": "CORE", "recommended_weight": 0.02, "confidence_score": 0.95, "risk_score": 0.9},
            ]
        }
        portfolio_snapshot = {
            "ranked_candidates": [
                {"symbol": "A", "bucket": "CORE", "theme": "AI Computing", "strategic_score": 90, "confidence_score": 0.8, "total_score": 90},
                {"symbol": "B", "bucket": "SATELLITE", "theme": "AI Computing", "strategic_score": 80, "confidence_score": 0.55, "total_score": 80},
            ]
        }
        report = engine.evaluate(position_snapshot, portfolio_snapshot)
        self.assertIn(report.risk_level, {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
        self.assertGreaterEqual(report.total_risk_score, 0.0)
        self.assertTrue(report.checks)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
