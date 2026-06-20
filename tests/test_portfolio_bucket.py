from __future__ import annotations

import unittest

from src.portfolio.portfolio_bucket import PortfolioBucket


class PortfolioBucketTest(unittest.TestCase):
    def test_bucket_rules(self) -> None:
        bucket = PortfolioBucket()
        self.assertEqual(bucket.classify(final_decision="BUY", total_score=90, confidence_score=0.8), "CORE")
        self.assertEqual(bucket.classify(final_decision="WATCH", total_score=72, confidence_score=0.7), "SATELLITE")
        self.assertEqual(bucket.classify(final_decision="REVIEW", total_score=58, confidence_score=0.6), "WATCHLIST")
        self.assertEqual(bucket.classify(final_decision="AVOID", total_score=95, confidence_score=0.9), "EXCLUDED")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
