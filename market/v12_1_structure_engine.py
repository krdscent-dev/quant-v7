"""V12.1 deterministic market structure engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketStructureV121:
    """Structured regime object for downstream V12 agents."""

    regime: str
    trend_score: float
    trend: float
    volatility: float
    volatility_state: str
    price_momentum: float
    structure_strength: float
    confidence: float
    reason: str


def analyze_market_structure(
    trend_score: float,
    volatility: float,
    price_momentum: float,
) -> MarketStructureV121:
    """Classify market structure using deterministic V12.1 rules."""

    trend = _clamp(trend_score)
    vol = _clamp(volatility)
    momentum = _clamp(price_momentum, -1.0, 1.0)
    vol_state = _volatility_state(vol)
    momentum_gap = abs(momentum - trend)

    if momentum_gap >= 0.35:
        regime = "TRANSITION"
        strength = 1.0 - min(momentum_gap, 1.0)
        reason = "Trend and price momentum are diverging rapidly."
    elif trend >= 0.65 and vol <= 0.45 and momentum >= 0.45:
        regime = "BULL"
        strength = 0.55 * trend + 0.25 * (1.0 - vol) + 0.20 * max(momentum, 0.0)
        reason = "High trend, positive momentum, and low volatility."
    elif trend <= 0.35 and vol >= 0.55:
        regime = "BEAR"
        strength = 0.45 * (1.0 - trend) + 0.35 * vol + 0.20 * max(-momentum, 0.0)
        reason = "Low trend and high volatility."
    elif 0.30 <= trend <= 0.65 and vol <= 0.60:
        regime = "RANGE"
        strength = 0.50 * (1.0 - abs(trend - 0.50)) + 0.30 * (1.0 - vol) + 0.20 * (1.0 - abs(momentum))
        reason = "Mid trend with stable volatility."
    else:
        regime = "TRANSITION"
        strength = 0.50
        reason = "Market inputs do not confirm a stable bull, bear, or range structure."

    strength = round(_clamp(strength), 4)
    confidence = round(0.55 + 0.40 * strength, 4)
    return MarketStructureV121(
        regime=regime,
        trend_score=round(trend, 4),
        trend=round(trend, 4),
        volatility=round(vol, 4),
        volatility_state=vol_state,
        price_momentum=round(momentum, 4),
        structure_strength=strength,
        confidence=confidence,
        reason=reason,
    )


class V121MarketStructureEngine:
    """Class wrapper for V12.1 market structure analysis."""

    def analyze_market_structure(
        self,
        trend_score: float,
        volatility: float,
        price_momentum: float,
    ) -> MarketStructureV121:
        return analyze_market_structure(trend_score, volatility, price_momentum)


def _volatility_state(volatility: float) -> str:
    if volatility <= 0.35:
        return "LOW"
    if volatility <= 0.60:
        return "STABLE"
    return "HIGH"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))
