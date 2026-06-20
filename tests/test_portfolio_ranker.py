from __future__ import annotations

import unittest

from src.portfolio.portfolio_contract import PortfolioScore
from src.portfolio.portfolio_ranker import PortfolioRanker


class PortfolioRankerTest(unittest.TestCase):
    def test_rank_order(self) -> None:
        ranker = PortfolioRanker()
        ranked = ranker.rank(
            [
                PortfolioScore("A", 80, 70, 0.8, 50, 0, "CORE"),
                PortfolioScore("B", 90, 80, 0.9, 60, 0, "CORE"),
            ]
        )
        self.assertEqual(ranked[0].symbol, "B")
        self.assertEqual(ranked[0].rank, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
