from __future__ import annotations

import unittest

from src.portfolio.portfolio_scoring_engine import PortfolioScoringEngine


class PortfolioScoringEngineTest(unittest.TestCase):
    def test_score_candidate(self) -> None:
        engine = PortfolioScoringEngine()
        score = engine.score_candidate(
            {
                "symbol": "000977.SZ",
                "strategic_score": 90,
                "confidence_score": 0.8,
                "risk_score": 0.2,
                "final_decision": "BUY",
            }
        )
        self.assertAlmostEqual(score.risk_adjusted_score, 57.6, places=2)
        self.assertGreater(score.total_score, 0)

    def test_snapshot_classification(self) -> None:
        engine = PortfolioScoringEngine()
        snapshot = engine.build_snapshot(
            [
                {"symbol": "A", "strategic_score": 92, "confidence_score": 0.8, "risk_score": 0.1, "final_decision": "BUY"},
                {"symbol": "B", "strategic_score": 75, "confidence_score": 0.7, "risk_score": 0.2, "final_decision": "WATCH"},
                {"symbol": "C", "strategic_score": 60, "confidence_score": 0.6, "risk_score": 0.2, "final_decision": "REVIEW"},
                {"symbol": "D", "strategic_score": 85, "confidence_score": 0.4, "risk_score": 0.1, "final_decision": "BUY"},
                {"symbol": "E", "strategic_score": 50, "confidence_score": 0.9, "risk_score": 0.2, "final_decision": "AVOID"},
            ]
        )
        self.assertTrue(any(item.bucket == "CORE" for item in snapshot.core_candidates))
        self.assertTrue(any(item.bucket == "SATELLITE" for item in snapshot.satellite_candidates))
        self.assertTrue(any(item.bucket == "WATCHLIST" for item in snapshot.watchlist_candidates))
        self.assertTrue(any(item.bucket == "EXCLUDED" for item in snapshot.excluded_candidates))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
