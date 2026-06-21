from __future__ import annotations

import unittest

from core.decision_engine import DecisionEngine
from core.ial import normalize_action


class V102ConsistencyTest(unittest.TestCase):
    def test_unknown_action_falls_back_to_observe(self) -> None:
        self.assertEqual(normalize_action(None), "OBSERVE")
        self.assertEqual(normalize_action("unknown"), "OBSERVE")

    def test_low_confidence_does_not_invalidate(self) -> None:
        decision = DecisionEngine().decide(
            symbol="TEST",
            score=16.0,
            regime="BEAR",
            confidence=0.10,
            context={},
        )
        self.assertIn(decision["action"], {"OBSERVE", "HOLD", "REDUCE", "SMALL_ADD", "ADD"})
        self.assertNotEqual(decision["action"], "INVALIDATE")

    def test_no_alpha_defaults_to_observe_not_invalidate(self) -> None:
        decision = DecisionEngine().decide(
            symbol="TEST",
            score=20.0,
            regime="BEAR",
            confidence=0.30,
            context={"theme": "unrelated"},
        )
        self.assertEqual(decision["action"], "OBSERVE")

    def test_bear_regime_allows_small_add_for_alpha(self) -> None:
        decision = DecisionEngine().decide(
            symbol="TEST",
            score=82.0,
            regime="BEAR",
            confidence=0.60,
            context={"theme_tags": ["ai", "compute"]},
        )
        self.assertEqual(decision["action"], "SMALL_ADD")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
