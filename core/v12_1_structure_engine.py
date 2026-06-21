"""Deterministic market structure classification for the V12 system.

This module classifies a market snapshot into regime, trend score, volatility
state, and structure strength without any trading logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class MarketStructureResult:
    regime: str
    trend_score: float
    volatility_state: str
    structure_strength: float


class MarketStructureEngine:
    """Classify market structure from a single snapshot or a short history."""

    def analyze_market_structure(self, market_data: Mapping[str, Any]) -> dict[str, Any]:
        close = self._to_float(market_data.get("close"), default=0.0)
        high = self._to_float(market_data.get("high"), default=close)
        low = self._to_float(market_data.get("low"), default=close)
        historical_close_series = market_data.get("historical_close_series")

        trend_score = self._trend_score(close, historical_close_series)
        volatility = self._volatility(close, high, low)
        volatility_state = self._volatility_state(volatility)
        price_momentum = self._price_momentum(close, historical_close_series)
        regime = self._regime(trend_score, volatility, price_momentum)
        structure_strength = self._structure_strength(trend_score)

        return {
            "regime": regime,
            "trend_score": round(trend_score, 4),
            "volatility_state": volatility_state,
            "structure_strength": round(structure_strength, 4),
        }

    def _trend_score(self, close: float, historical_close_series: Any) -> float:
        series = self._normalize_series(historical_close_series)
        if not series:
            return 0.5
        moving_average = mean(series[-20:]) if len(series) >= 20 else mean(series)
        if moving_average <= 0:
            return 0.5
        ratio = close / moving_average
        return self._clamp((ratio - 0.90) / 0.20)

    def _price_momentum(self, close: float, historical_close_series: Any) -> float:
        series = self._normalize_series(historical_close_series)
        if len(series) < 2:
            return 0.0
        previous = series[-2]
        if previous <= 0:
            return 0.0
        momentum = close / previous - 1.0
        return max(-1.0, min(1.0, momentum * 10.0))

    def _volatility(self, close: float, high: float, low: float) -> float:
        if close <= 0:
            return 0.0
        return max(0.0, (high - low) / close)

    def _volatility_state(self, volatility: float) -> str:
        if volatility < 0.02:
            return "LOW"
        if volatility <= 0.05:
            return "MEDIUM"
        return "HIGH"

    def _regime(self, trend_score: float, volatility: float, price_momentum: float) -> str:
        if volatility > 0.05 and price_momentum >= 0.20:
            return "TRANSITION"
        if trend_score > 0.7 and volatility < 0.02:
            return "BULL"
        if trend_score < 0.3 and volatility > 0.05:
            return "BEAR"
        return "RANGE"

    def _structure_strength(self, trend_score: float) -> float:
        return self._clamp(abs(trend_score - 0.5) * 2.0)

    def _normalize_series(self, historical_close_series: Any) -> list[float]:
        if historical_close_series is None:
            return []
        if isinstance(historical_close_series, Mapping):
            historical_close_series = historical_close_series.values()
        if not isinstance(historical_close_series, Sequence) or isinstance(historical_close_series, (str, bytes)):
            return []
        values: list[float] = []
        for item in historical_close_series:
            try:
                values.append(float(item))
            except Exception:
                continue
        return values

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

