from __future__ import annotations

import unittest

from src.position.position_explainer import PositionExplainer


class PositionExplainerTest(unittest.TestCase):
    def test_explanations(self) -> None:
        explainer = PositionExplainer()
        text = explainer.explain("NVDA", "CORE", 0.092, 90, 0.92, 0.20)
        self.assertIn("NVDA", text)
        self.assertIn("推荐", text)
        self.assertIn("Confidence 高", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
