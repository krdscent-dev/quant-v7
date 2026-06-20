from __future__ import annotations

import unittest

from core.provider_router import ProviderRouter


class ProviderRouterTrustTest(unittest.TestCase):
    def test_best_provider_mode_prefers_high_trust(self) -> None:
        router = ProviderRouter()
        router._config = dict(router._config)
        router._config.setdefault("conflict_resolution", {})
        router._config["conflict_resolution"] = dict(router._config["conflict_resolution"])
        router._config["conflict_resolution"]["mode"] = "best_provider"
        provider = router.get_provider_for_field("financial_summary")
        self.assertEqual(provider.__class__.__name__, "TushareDataProvider")

