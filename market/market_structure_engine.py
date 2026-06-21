"""Detect external market structure before agent decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class MarketStructure:
    regime: str
    trend: float
    volatility: float
    confidence: float
    reason: str


class MarketStructureEngine:
    """Classify market structure as BULL / BEAR / RANGE."""

    def classify(self, market_data: Mapping[str, Any] | None) -> MarketStructure:
        data = market_data or {}
        trend = self._clamp(float(data.get("trend", 0.0) or 0.0))
        volatility = self._clamp(float(data.get("volatility", 0.0) or 0.0))

        if trend >= 0.65 and volatility <= 0.45:
            regime = "BULL"
            confidence = 0.88
            reason = "Trend is strong and volatility is controlled."
        elif trend <= 0.30 or volatility >= 0.75:
            regime = "BEAR"
            confidence = 0.86
            reason = "Trend is weak or volatility is elevated."
        else:
            regime = "RANGE"
            confidence = 0.78
            reason = "Market is range-bound; sector rotation matters more than broad beta."

        return MarketStructure(regime, round(trend, 4), round(volatility, 4), confidence, reason)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

