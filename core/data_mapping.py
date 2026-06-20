"""Data mapping layer.

This module maps provider outputs into factor-ready dictionaries for
research-side scoring.

Primary entry point:
- `build_factor_input(company_code: str)`

The layer is source-agnostic and uses ProviderRouter to select the best
available provider per field. If a preferred provider is unavailable, it
falls back to `MockDataProvider`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.factor_registry import DEFAULT_FACTOR_REGISTRY
from core.financial_cross_validator import FinancialCrossValidator
from core.provider_router import ProviderRouter
from data_sources.base import DataProvider
from data_sources.akshare_provider import AkShareDataProvider
from data_sources.mock_provider import MockDataProvider
from data_sources.tushare_provider import TushareDataProvider


class DataMappingError(RuntimeError):
    pass


class DataMappingLayer:
    """Map provider data into standardized factor inputs."""

    def __init__(self, provider: DataProvider | None = None, router: ProviderRouter | None = None) -> None:
        self.provider = provider or MockDataProvider()
        self.router = router or ProviderRouter()
        self.cross_validator = FinancialCrossValidator()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _confidence_score_from_level(self, level: str) -> float:
        mapping = {
            "high": 1.00,
            "medium": 0.75,
            "low": 0.35,
        }
        return mapping.get(str(level).lower(), 0.0)

    def _validation_status_from_level(self, level: str) -> str:
        mapping = {
            "high": "PASS",
            "medium": "MINOR_DIFF",
            "low": "MAJOR_DIFF",
        }
        return mapping.get(str(level).lower(), "INVALID")

    def _provider_name(self, provider: DataProvider) -> str:
        return provider.__class__.__name__

    def _fetch_field(self, field_name: str, company_code: str) -> dict[str, Any]:
        provider = self.router.get_provider_for_field(field_name)
        provider_used = self._provider_name(provider)
        fallback_used = False
        method_name = f"get_{field_name}"

        try:
            data = getattr(provider, method_name)(company_code)
            data_dict = dict(data)
        except Exception:
            fallback_used = True
            provider = self.provider
            provider_used = self._provider_name(provider)
            data_dict = dict(getattr(provider, method_name)(company_code))

        if data_dict.get("available") is False or str(data_dict.get("status", "")).endswith("not_installed"):
            if provider_used != "MockDataProvider":
                fallback_used = True
                provider = self.provider
                provider_used = self._provider_name(provider)
                data_dict = dict(getattr(provider, method_name)(company_code))

        return {
            "data": data_dict,
            "provider_used": provider_used,
            "fallback_used": fallback_used,
            "timestamp": self._now(),
        }

    def _fetch_financial_summary_bundle(self, company_code: str) -> dict[str, Any]:
        akshare_provider = AkShareDataProvider()
        tushare_provider = TushareDataProvider()

        provider = self.router.get_provider_for_field("financial_summary")
        provider_used = self._provider_name(provider)
        fallback_used = False

        try:
            primary_data = dict(getattr(provider, "get_financial_summary")(company_code))
        except Exception:
            fallback_used = True
            provider = self.provider
            provider_used = self._provider_name(provider)
            primary_data = dict(getattr(provider, "get_financial_summary")(company_code))

        if primary_data.get("available") is False and provider_used != "MockDataProvider":
            fallback_used = True
            provider = self.provider
            provider_used = self._provider_name(provider)
            primary_data = dict(getattr(provider, "get_financial_summary")(company_code))

        akshare_data = dict(akshare_provider.get_financial_summary(company_code))
        tushare_data = dict(tushare_provider.get_financial_summary(company_code))
        cross_validation_result = self.cross_validator.compare_financial_summary(
            akshare_summary=akshare_data,
            tushare_summary=tushare_data,
        )

        return {
            "data": primary_data,
            "provider_used": provider_used,
            "fallback_used": fallback_used,
            "confidence_level": cross_validation_result.get("overall_confidence_level", "low"),
            "confidence_score": self._confidence_score_from_level(cross_validation_result.get("overall_confidence_level", "low")),
            "validation_status": self._validation_status_from_level(cross_validation_result.get("overall_confidence_level", "low")),
            "cross_validation_result": cross_validation_result,
            "timestamp": self._now(),
            "akshare_summary": akshare_data,
            "tushare_summary": tushare_data,
        }

    def build_factor_input(self, company_code: str) -> dict[str, Any]:
        """Build a standardized factor input bundle for one company."""

        company_basic_info = self._fetch_field("company_basic_info", company_code)
        financial_summary = self._fetch_financial_summary_bundle(company_code)
        order_signals = self._fetch_field("order_signals", company_code)
        news_signals = self._fetch_field("news_signals", company_code)
        theme_signals = self._fetch_field("theme_signals", company_code)

        basic = dict(company_basic_info["data"])
        financial = dict(financial_summary["data"])
        order = dict(order_signals["data"])
        news = dict(news_signals["data"])
        theme = dict(theme_signals["data"])

        return {
            "company_code": company_code,
            "company_basic_info": company_basic_info,
            "financial_summary": financial_summary,
            "order_signals": order_signals,
            "news_signals": news_signals,
            "theme_signals": theme_signals,
            "confidence_score": financial_summary.get("confidence_score", 0.0),
            "validation_status": financial_summary.get("validation_status", "INVALID"),
            "name": str(basic.get("name", "UNKNOWN")),
            "theme": str(theme.get("theme", basic.get("industry", "UNKNOWN"))),
            "tau_factor_score": theme.get("tau_factor_score", 0.0),
            "supernode_score": theme.get("ascend_ecosystem_exposure", 0.0),
            "domestic_substitution_score": theme.get("domestic_substitution_exposure", 0.0),
            "advanced_packaging_score": theme.get("advanced_packaging_exposure", 0.0),
            "advanced_material_score": theme.get("advanced_material_exposure", 0.0),
            "new_orders": order.get("order_landing_score", 0.0),
            "capacity_expansion": financial.get("capex_signal", 0.0),
            "management_guidance": news.get("guidance_signal", 0.0),
            "customer_verification": order.get("customer_validation_score", 0.0),
            "revenue_acceleration": financial.get("revenue_growth", 0.0),
            "news_signal_strength": news.get("positive_news_ratio", 0.0),
        }

    def build_factor_inputs(self, code: str, name: str | None = None, theme: str | None = None) -> dict[str, Any]:
        payload = self.build_factor_input(company_code=code)
        if name is not None:
            payload["name"] = name
        if theme is not None:
            payload["theme"] = theme
        return payload

    def build_strategic_score_payload(self, code: str, name: str | None = None, theme: str | None = None) -> dict[str, Any]:
        """Return a payload ready for StrategicScoreEngine."""

        return self.build_factor_inputs(code=code, name=name, theme=theme)


def get_factor_registry():
    return DEFAULT_FACTOR_REGISTRY
