"""V12.4 multi-dimensional cycle engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CycleSignal:
    cycle: str
    score: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class CycleStateV124:
    liquidity_cycle: str
    sentiment_cycle: str
    industry_cycle: str
    combined_cycle_state: str
    macro_cycle: str
    risk_appetite: str
    aggressiveness: float
    liquidity_score: float
    fear_index: float
    industry_growth: float
    valuation_score: float
    reason: str


class V124CycleEngine:
    """Detect liquidity, sentiment, and industry cycles."""

    def detect_liquidity_cycle(self, liquidity_score: float) -> CycleSignal:
        score = self._clamp(liquidity_score)
        if score >= 0.62:
            cycle = "EXPANSION"
            reason = "Liquidity is expanding and can support risk taking."
        else:
            cycle = "CONTRACTION"
            reason = "Liquidity is contracting and should limit sizing."
        confidence = 0.55 + 0.40 * score if cycle == "EXPANSION" else 0.55 + 0.40 * (1.0 - score)
        return CycleSignal(cycle=cycle, score=round(score, 4), confidence=round(confidence, 4), reason=reason)

    def detect_sentiment_cycle(self, fear_index: float) -> CycleSignal:
        fear = max(0.0, min(100.0, float(fear_index)))
        if fear >= 70.0:
            cycle = "PANIC"
            confidence = min(0.95, 0.60 + fear / 250.0)
            reason = "Fear is elevated; sentiment is in panic mode."
        elif fear <= 35.0:
            cycle = "GREED"
            confidence = min(0.95, 0.65 + (35.0 - fear) / 120.0)
            reason = "Fear is low; sentiment is in greed mode."
        else:
            cycle = "NEUTRAL"
            confidence = 0.70
            reason = "Fear is contained; sentiment is balanced."
        score = 1.0 - abs((fear - 50.0) / 50.0)
        return CycleSignal(cycle=cycle, score=round(max(0.0, min(1.0, score)), 4), confidence=round(confidence, 4), reason=reason)

    def detect_industry_cycle(self, industry_growth: float, valuation_score: float) -> CycleSignal:
        growth = self._clamp(industry_growth)
        valuation = self._clamp(valuation_score)
        if growth >= 0.70 and valuation <= 0.45:
            cycle = "EARLY_GROWTH"
            reason = "Growth is strong while valuation remains manageable."
        elif growth >= 0.65 and valuation <= 0.70:
            cycle = "EXPANSION"
            reason = "Growth is strong and valuation is acceptable."
        elif growth >= 0.45 and valuation > 0.60:
            cycle = "MATURITY"
            reason = "Growth is slowing and valuation is starting to look stretched."
        else:
            cycle = "DECLINE"
            reason = "Growth is weak or valuation is too demanding."
        score = 0.60 * growth + 0.40 * (1.0 - valuation)
        confidence = 0.55 + 0.35 * max(0.0, min(1.0, score))
        return CycleSignal(cycle=cycle, score=round(score, 4), confidence=round(confidence, 4), reason=reason)

    def build_cycle_state(
        self,
        liquidity_indicators: Mapping[str, Any] | None,
        sentiment_indicators: Mapping[str, Any] | None,
        industry_data: Mapping[str, Any] | None,
    ) -> CycleStateV124:
        liquidity = liquidity_indicators or {}
        sentiment = sentiment_indicators or {}
        industry = industry_data or {}

        liquidity_score = self._clamp(float(liquidity.get("liquidity_score", liquidity.get("score", 0.0)) or 0.0))
        fear_index = float(sentiment.get("fear_index", sentiment.get("fear", 50.0)) or 50.0)
        industry_growth = self._clamp(float(industry.get("industry_growth", industry.get("growth", 0.5)) or 0.5))
        valuation_score = self._clamp(float(industry.get("valuation_score", industry.get("valuation", 0.5)) or 0.5))

        liquidity_signal = self.detect_liquidity_cycle(liquidity_score)
        sentiment_signal = self.detect_sentiment_cycle(fear_index)
        industry_signal = self.detect_industry_cycle(industry_growth, valuation_score)

        combined_cycle_state = self._combine_cycle_state(
            liquidity_signal.cycle,
            sentiment_signal.cycle,
            industry_signal.cycle,
        )
        risk_appetite, aggressiveness = self._risk_appetite_and_aggressiveness(combined_cycle_state)
        reason = (
            f"Liquidity={liquidity_signal.cycle}, sentiment={sentiment_signal.cycle}, "
            f"industry={industry_signal.cycle} -> {combined_cycle_state}."
        )
        return CycleStateV124(
            liquidity_cycle=liquidity_signal.cycle,
            sentiment_cycle=sentiment_signal.cycle,
            industry_cycle=industry_signal.cycle,
            combined_cycle_state=combined_cycle_state,
            macro_cycle=combined_cycle_state,
            risk_appetite=risk_appetite,
            aggressiveness=aggressiveness,
            liquidity_score=liquidity_signal.score,
            fear_index=round(max(0.0, min(100.0, fear_index)), 2),
            industry_growth=industry_growth,
            valuation_score=valuation_score,
            reason=reason,
        )

    def _combine_cycle_state(self, liquidity_cycle: str, sentiment_cycle: str, industry_cycle: str) -> str:
        if liquidity_cycle == "EXPANSION" and sentiment_cycle == "GREED" and industry_cycle in {"EARLY_GROWTH", "EXPANSION"}:
            return "RISK_ON"
        if liquidity_cycle == "CONTRACTION" and sentiment_cycle == "PANIC":
            return "STRESS"
        if liquidity_cycle == "EXPANSION" and industry_cycle in {"EARLY_GROWTH", "EXPANSION"}:
            return "SUPPORTIVE"
        if liquidity_cycle == "CONTRACTION":
            return "DEFENSIVE"
        return "ROTATION"

    def _risk_appetite_and_aggressiveness(self, combined_cycle_state: str) -> tuple[str, float]:
        mapping = {
            "RISK_ON": ("RISING", 1.15),
            "SUPPORTIVE": ("RISING", 1.05),
            "ROTATION": ("SELECTIVE", 0.95),
            "DEFENSIVE": ("FALLING", 0.80),
            "STRESS": ("FALLING", 0.65),
        }
        return mapping.get(combined_cycle_state, ("SELECTIVE", 0.90))

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
