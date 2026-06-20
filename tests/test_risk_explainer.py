from __future__ import annotations

import unittest

from src.risk.risk_contract import PortfolioRiskReport, RiskCheckResult
from src.risk.risk_explainer import RiskExplainer


class RiskExplainerTest(unittest.TestCase):
    def test_explainer(self) -> None:
        report = PortfolioRiskReport(
            period="TTM",
            total_risk_score=0.8,
            risk_level="CRITICAL",
            checks=[
                RiskCheckResult("industry_concentration", False, "HIGH", "集中度过高", ["A"], "reduce"),
            ],
            warnings=["行业集中度偏高"],
            suggested_actions=["降低行业集中度"],
        )
        explainer = RiskExplainer()
        messages = explainer.explain(report, {}, {})
        self.assertTrue(any("行业集中度" in item for item in messages))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
