"""AkShare data provider adapter.

This module provides a thin adapter around AkShare for future A-share
data integration. It intentionally does not depend on AkShare being
installed at runtime. When the package is unavailable, the provider
returns structured placeholder payloads with a clear status field.
"""

from __future__ import annotations

from typing import Any, Mapping

from data_sources.base import DataProvider

try:  # pragma: no cover - optional dependency
    import akshare as ak
except ImportError:  # pragma: no cover - optional dependency
    ak = None


class AkShareDataProvider(DataProvider):
    """AkShare-backed data provider adapter."""

    def __init__(self) -> None:
        self.akshare_available = ak is not None

    def _unavailable_payload(self, code: str, method: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "source": "akshare",
            "available": False,
            "status": "akshare_not_installed",
            "method": method,
            "message": "akshare is not installed; returning adapter placeholder data.",
        }

    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_company_basic_info")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "name": "",
            "industry": "",
            "listing_status": "unknown",
            "message": "AkShare adapter is ready for future field mapping.",
        }

    def get_financial_summary(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_financial_summary")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "revenue_growth": 0.0,
            "gross_margin": 0.0,
            "rd_expense_ratio": 0.0,
            "capex_signal": 0.0,
            "message": "Field mapping placeholder for future AkShare financial endpoints.",
        }

    def get_order_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_order_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "order_landing_score": 0.0,
            "revenue_confirmation_score": 0.0,
            "customer_validation_score": 0.0,
            "story_to_earnings_score": 0.0,
            "message": "Order signal mapping placeholder for future data sources.",
        }

    def get_news_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_news_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "headline_count": 0,
            "positive_news_ratio": 0.0,
            "negative_news_ratio": 0.0,
            "guidance_signal": 0.0,
            "message": "News signal mapping placeholder for future AkShare integration.",
        }

    def get_theme_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_theme_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "tau_factor_score": 0.0,
            "ascend_ecosystem_exposure": 0.0,
            "domestic_substitution_exposure": 0.0,
            "advanced_packaging_exposure": 0.0,
            "advanced_material_exposure": 0.0,
            "message": "Theme mapping placeholder for future factor contract alignment.",
        }

