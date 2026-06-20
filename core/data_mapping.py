"""Data mapping layer.

This module maps DataProvider outputs into factor-ready dictionaries for
research-side scoring. It intentionally uses MockDataProvider only for now
and is designed for future AkShare / Tushare adapters.
"""

from __future__ import annotations

from typing import Any

from core.factor_registry import DEFAULT_FACTOR_REGISTRY
from data_sources.base import DataProvider


class DataMappingError(RuntimeError):
    pass


class DataMappingLayer:
    """Map provider data into standardized factor inputs."""

    def __init__(self, provider: DataProvider) -> None:
        self.provider = provider

    def build_factor_inputs(self, code: str, name: str | None = None, theme: str | None = None) -> dict[str, Any]:
        basic = dict(self.provider.get_company_basic_info(code))
        financial = dict(self.provider.get_financial_summary(code))
        order = dict(self.provider.get_order_signals(code))
        news = dict(self.provider.get_news_signals(code))
        theme_signals = dict(self.provider.get_theme_signals(code))

        standardized = {
            "code": code,
            "name": name or str(basic.get("name", "UNKNOWN")),
            "theme": theme or str(theme_signals.get("theme", basic.get("industry", "UNKNOWN"))),
            "tau_factor_score": theme_signals.get("tau_factor_score", 0.0),
            "supernode_score": theme_signals.get("ascend_ecosystem_exposure", 0.0),
            "domestic_substitution_score": theme_signals.get("domestic_substitution_exposure", 0.0),
            "advanced_packaging_score": theme_signals.get("advanced_packaging_exposure", 0.0),
            "advanced_material_score": theme_signals.get("advanced_material_exposure", 0.0),
            "new_orders": order.get("order_landing_score", 0.0),
            "capacity_expansion": financial.get("capex_signal", 0.0),
            "management_guidance": news.get("guidance_signal", 0.0),
            "customer_verification": order.get("customer_validation_score", 0.0),
            "revenue_acceleration": financial.get("revenue_growth", 0.0),
            "news_signal_strength": news.get("positive_news_ratio", 0.0),
            "financial_summary": financial,
            "basic_info": basic,
            "news_signals": news,
            "theme_signals": theme_signals,
        }
        return standardized

    def build_strategic_score_payload(self, code: str, name: str | None = None, theme: str | None = None) -> dict[str, Any]:
        """Return a payload ready for StrategicScoreEngine."""

        return self.build_factor_inputs(code=code, name=name, theme=theme)


def get_factor_registry():
    return DEFAULT_FACTOR_REGISTRY
