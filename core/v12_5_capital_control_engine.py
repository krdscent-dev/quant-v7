"""Deterministic capital control engine for V12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CapitalControlResult:
    position_multiplier: float
    risk_budget: float
    exposure_limit: float
    leverage_adjustment: float
    risk_mode: str


class CapitalControlEngine:
    """Adjust capital controls from market state only."""

    def build_capital_control(self, market_state: Mapping[str, Any], portfolio_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(market_state, Mapping):
            return self._fallback()

        regime = str(market_state.get("regime", "RANGE") or "RANGE").upper()
        flow_strength = self._to_float(market_state.get("flow_strength", 0.5), default=0.5)
        narrative_strength = self._to_float(market_state.get("narrative_strength", 0.5), default=0.5)
        cycle_state = str(market_state.get("cycle_state", market_state.get("unified_cycle_state", "TRANSITION")) or "TRANSITION").upper()
        current_exposure = self._to_float((portfolio_state or {}).get("current_exposure", 0.0), default=0.0)
        max_drawdown = self._to_float((portfolio_state or {}).get("max_drawdown", 0.0), default=0.0)

        if not self._has_meaningful_data(market_state):
            return self._fallback()

        risk_mode = self._risk_mode(regime, cycle_state)
        position_multiplier = self._position_multiplier(risk_mode, flow_strength, narrative_strength, current_exposure)
        risk_budget = self._risk_budget(flow_strength)
        exposure_limit = self._exposure_limit(max_drawdown)
        leverage_adjustment = self._leverage_adjustment(cycle_state, narrative_strength)

        return {
            "position_multiplier": round(position_multiplier, 4),
            "risk_budget": round(risk_budget, 4),
            "exposure_limit": round(exposure_limit, 4),
            "leverage_adjustment": round(leverage_adjustment, 4),
            "risk_mode": risk_mode,
        }

    def _risk_mode(self, regime: str, cycle_state: str) -> str:
        if cycle_state == "RISK_ON" and regime == "BULL":
            return "AGGRESSIVE"
        if cycle_state == "RISK_OFF" or regime == "BEAR":
            return "DEFENSIVE"
        return "NEUTRAL"

    def _position_multiplier(self, risk_mode: str, flow_strength: float, narrative_strength: float, current_exposure: float) -> float:
        flow = self._clamp(flow_strength)
        narrative = self._clamp(narrative_strength)
        exposure_penalty = max(0.0, min(0.15, current_exposure * 0.2))
        if risk_mode == "AGGRESSIVE":
            base = 1.20 + 0.20 * flow + 0.10 * narrative - exposure_penalty
        elif risk_mode == "DEFENSIVE":
            base = 0.52 + 0.15 * flow + 0.05 * narrative - exposure_penalty
        else:
            base = 0.80 + 0.10 * flow + 0.05 * narrative - exposure_penalty
        return self._clamp_range(base, 0.0, 1.5)

    def _risk_budget(self, flow_strength: float) -> float:
        volatility_proxy = 1.0 - self._clamp(flow_strength)
        return self._clamp_range(1.0 / (1.0 + volatility_proxy), 0.0, 1.0)

    def _exposure_limit(self, max_drawdown: float) -> float:
        drawdown = max(0.0, max_drawdown)
        if drawdown > 0.25:
            return 0.3
        if drawdown > 0.15:
            return 0.5
        return 1.0

    def _leverage_adjustment(self, cycle_state: str, narrative_strength: float) -> float:
        narrative = self._clamp(narrative_strength)
        if cycle_state == "RISK_OFF":
            return 0.5
        if narrative > 0.7 and cycle_state == "RISK_ON":
            return 1.2
        return 1.0

    def _fallback(self) -> dict[str, Any]:
        return {
            "position_multiplier": 1.0,
            "risk_budget": 0.5,
            "exposure_limit": 1.0,
            "leverage_adjustment": 1.0,
            "risk_mode": "NEUTRAL",
        }

    @staticmethod
    def _has_meaningful_data(market_state: Mapping[str, Any]) -> bool:
        keys = {"regime", "flow_strength", "narrative_strength", "cycle_state", "unified_cycle_state"}
        return any(key in market_state for key in keys)

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

    @staticmethod
    def _clamp_range(value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))


def build_capital_control(market_state: Mapping[str, Any], portfolio_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return CapitalControlEngine().build_capital_control(market_state, portfolio_state)
