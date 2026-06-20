"""Mock data provider.

This provider returns deterministic placeholder data so the research
engine can run without external APIs.
"""

from __future__ import annotations

from typing import Any, Mapping

from data_sources.base import DataProvider


class MockDataProvider(DataProvider):
    """Mock implementation of the unified data provider."""

    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "name": "Mock Company",
            "industry": "Mock Industry",
            "listing_status": "listed",
            "source": "mock",
        }

    def get_financial_summary(self, code: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "revenue_growth": 0.12,
            "gross_margin": 0.35,
            "rd_expense_ratio": 0.08,
            "source": "mock",
        }

    def get_order_signals(self, code: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "order_landing_score": 0.6,
            "revenue_confirmation_score": 0.55,
            "customer_validation_score": 0.62,
            "story_to_earnings_score": 0.50,
            "source": "mock",
        }

    def get_news_signals(self, code: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "headline_count": 3,
            "positive_news_ratio": 0.67,
            "negative_news_ratio": 0.33,
            "source": "mock",
        }

    def get_theme_signals(self, code: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "ai_compute_exposure": 0.75,
            "ascend_ecosystem_exposure": 0.60,
            "domestic_substitution_exposure": 0.58,
            "advanced_packaging_exposure": 0.40,
            "source": "mock",
        }
