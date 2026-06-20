from __future__ import annotations

import unittest

from src.position.position_sizing_engine import PositionSizingEngine


class PositionSizingEngineTest(unittest.TestCase):
    def test_recommendation_and_snapshot(self) -> None:
        engine = PositionSizingEngine()
        recommendation = engine.recommend(
            {
                "symbol": "000977.SZ",
                "bucket": "CORE",
                "strategic_score": 90,
                "confidence_score": 0.92,
                "risk_score": 0.20,
                "evidence_refs": {"evidence_chain": {"symbol": "000977.SZ"}},
            }
        )
        self.assertGreater(recommendation.recommended_weight, 0.08)
        self.assertLessEqual(recommendation.recommended_weight, recommendation.max_weight)

        snapshot = engine.build_snapshot(
            [
                {"symbol": "A", "bucket": "CORE", "strategic_score": 90, "confidence_score": 0.92, "risk_score": 0.20},
                {"symbol": "B", "bucket": "SATELLITE", "strategic_score": 75, "confidence_score": 0.82, "risk_score": 0.10},
                {"symbol": "C", "bucket": "WATCHLIST", "strategic_score": 60, "confidence_score": 0.7, "risk_score": 0.20},
                {"symbol": "D", "bucket": "EXCLUDED", "strategic_score": 80, "confidence_score": 0.8, "risk_score": 0.20},
            ]
        )
        self.assertGreater(snapshot.total_allocated, 0.0)
        self.assertLessEqual(snapshot.total_allocated, 1.0)
        self.assertIn("Cash", snapshot.allocation_summary)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
