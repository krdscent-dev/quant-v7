"""Deterministic market cycle engine for the V12 system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CycleResult:
    liquidity_cycle: str
    sentiment_cycle: str
    industry_cycle: str
    unified_cycle_state: str


class CycleEngine:
    """Classify liquidity, sentiment, industry, and combined cycle state."""

    def build_cycle_state(self, market_data: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(market_data, Mapping):
            return self._fallback()

        flow_strength = self._to_float(
            market_data.get("flow_strength", market_data.get("capital_flow_strength", 0.5)),
            default=0.5,
        )
        volatility = self._to_float(market_data.get("volatility"), default=0.5)
        narrative_strength = self._to_float(market_data.get("narrative_strength"), default=0.5)

        if market_data.get("flow_strength") is None and market_data.get("capital_flow_strength") is None and market_data.get("narrative_strength") is None and market_data.get("volatility") is None:
            return self._fallback()

        liquidity_cycle = self.detect_liquidity_cycle(flow_strength)
        sentiment_cycle = self.detect_sentiment_cycle(volatility)
        industry_cycle = self.detect_industry_cycle(narrative_strength, flow_strength)
        unified_cycle_state = self._unified_cycle_state(liquidity_cycle, sentiment_cycle)

        return {
            "liquidity_cycle": liquidity_cycle,
            "sentiment_cycle": sentiment_cycle,
            "industry_cycle": industry_cycle,
            "unified_cycle_state": unified_cycle_state,
        }

    def detect_liquidity_cycle(self, flow_strength: float) -> str:
        return "EXPANSION" if self._to_float(flow_strength, default=0.0) > 0.6 else "CONTRACTION"

    def detect_sentiment_cycle(self, volatility: float) -> str:
        value = self._to_float(volatility, default=0.5)
        if value > 0.7:
            return "PANIC"
        if value < 0.3:
            return "GREED"
        return "NEUTRAL"

    def detect_industry_cycle(self, narrative_strength: float, flow_strength: float) -> str:
        narrative = self._to_float(narrative_strength, default=0.5)
        flow = self._to_float(flow_strength, default=0.5)
        if narrative > 0.7 and flow > 0.6:
            return "EARLY_GROWTH"
        if narrative > 0.7:
            return "EXPANSION"
        if narrative < 0.4:
            return "DECLINE"
        return "MATURITY"

    def _unified_cycle_state(self, liquidity_cycle: str, sentiment_cycle: str) -> str:
        if liquidity_cycle == "EXPANSION" and sentiment_cycle == "GREED":
            return "RISK_ON"
        if liquidity_cycle == "CONTRACTION" and sentiment_cycle == "PANIC":
            return "RISK_OFF"
        return "TRANSITION"

    def _fallback(self) -> dict[str, Any]:
        return {
            "liquidity_cycle": "UNKNOWN",
            "sentiment_cycle": "NEUTRAL",
            "industry_cycle": "MATURITY",
            "unified_cycle_state": "TRANSITION",
        }

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default


def build_cycle_state(market_data: Mapping[str, Any]) -> dict[str, Any]:
    return CycleEngine().build_cycle_state(market_data)

