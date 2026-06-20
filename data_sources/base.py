"""Data provider base layer.

This module defines a unified provider interface for all future data
adapters, including Mock, AkShare, and Tushare implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class DataProvider(ABC):
    """Unified data provider interface."""

    @abstractmethod
    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        """Return company basic info."""

    @abstractmethod
    def get_financial_summary(self, code: str) -> Mapping[str, Any]:
        """Return financial summary."""

    @abstractmethod
    def get_order_signals(self, code: str) -> Mapping[str, Any]:
        """Return order confirmation related signals."""

    @abstractmethod
    def get_news_signals(self, code: str) -> Mapping[str, Any]:
        """Return news/event related signals."""

    @abstractmethod
    def get_theme_signals(self, code: str) -> Mapping[str, Any]:
        """Return theme exposure signals."""
