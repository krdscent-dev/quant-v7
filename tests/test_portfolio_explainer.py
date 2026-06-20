from __future__ import annotations

import unittest

from src.portfolio.portfolio_contract import PortfolioCandidate, PortfolioScore
from src.portfolio.portfolio_explainer import PortfolioExplainer


class PortfolioExplainerTest(unittest.TestCase):
    def test_explanations(self) -> None:
        explainer = PortfolioExplainer()
        candidate = PortfolioCandidate(
            symbol="000977.SZ",
            period="TTM",
            strategic_score=90,
            final_decision="BUY",
            confidence_score=0.8,
            risk_score=0.2,
            explanation="示例",
            bucket="CORE",
        )
        score = PortfolioScore("000977.SZ", 90, 90, 0.8, 57.6, 1, "CORE")
        text = explainer.explain_candidate(candidate, score)
        self.assertIn("CORE", text)
        self.assertIn("000977.SZ", explainer.explain_risk_drop("000977.SZ", 90, 0.5, 40))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
