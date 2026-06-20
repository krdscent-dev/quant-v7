from __future__ import annotations

import unittest

from src.position.sizing_rules import SizingRules


class SizingRulesTest(unittest.TestCase):
    def test_core_weight(self) -> None:
        rules = SizingRules()
        weight = rules.recommended_weight("CORE", 0.9, 0.2)
        self.assertGreater(weight, 0.08)

    def test_satellite_weight(self) -> None:
        rules = SizingRules()
        weight = rules.recommended_weight("SATELLITE", 0.8, 0.2)
        self.assertGreater(weight, 0.04)

    def test_watch_and_excluded_zero(self) -> None:
        rules = SizingRules()
        self.assertEqual(rules.recommended_weight("WATCHLIST", 0.9, 0.2), 0.0)
        self.assertEqual(rules.recommended_weight("EXCLUDED", 0.9, 0.2), 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
