"""V10 entry point.

This script keeps the V9 strategic scoring pipeline intact and adds a thin
decision layer on top to emit ACTION-based outputs.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from core.decision_engine import DecisionEngine
from core.regime_engine import RegimeEngine
from strategy.strategic_score_engine import build_rankings


def _confidence_from_result(result: Any) -> float:
    breakdown = getattr(result, "factor_breakdown", {}) or {}
    value = breakdown.get("final_confidence", breakdown.get("confidence_score", 0.0))
    try:
        confidence = float(value)
    except Exception:
        confidence = 0.0
    if confidence > 1.0:
        confidence /= 100.0
    return max(0.0, min(1.0, confidence))


def _market_snapshot(results: list[Any]) -> dict[str, float]:
    scores = [float(getattr(item, "strategic_score", 0.0)) for item in results]
    confidences = [_confidence_from_result(item) for item in results]
    if not scores:
        return {"trend": 0.0, "volatility": 1.0}
    top_score = max(scores)
    score_spread = max(scores) - min(scores)
    avg_conf = mean(confidences) if confidences else 0.0
    trend = max(0.0, min(1.0, top_score / 100.0))
    volatility = max(0.0, min(1.0, score_spread / 100.0 + (1.0 - avg_conf) * 0.35))
    return {"trend": trend, "volatility": volatility}


def main() -> None:
    ranked = build_rankings()
    regime_engine = RegimeEngine()
    decision_engine = DecisionEngine()
    market_data = _market_snapshot(ranked)
    regime_result = regime_engine.classify(market_data)

    print(f"Market Regime: {regime_result.regime} (trend={regime_result.trend:.2f}, volatility={regime_result.volatility:.2f})")
    print(f"Regime Reason: {regime_result.reason}")
    print("")
    print("symbol\tscore\tconfidence\taction\thorizon\treason")
    for item in ranked[:10]:
        confidence = _confidence_from_result(item)
        decision = decision_engine.decide(
            symbol=getattr(item, "code", "UNKNOWN"),
            score=float(getattr(item, "strategic_score", 0.0)),
            regime=regime_result,
            confidence=confidence,
            context={
                "price_zone": "UNKNOWN",
                "momentum": "UNKNOWN",
                "stage": "UNKNOWN",
            },
        )
        print(
            f"{decision['symbol']}\t"
            f"{float(getattr(item, 'strategic_score', 0.0)):.2f}\t"
            f"{decision['confidence']:.2f}\t"
            f"{decision['action']}\t"
            f"{decision['horizon']}\t"
            f"{decision['reason']}"
        )


if __name__ == "__main__":
    main()
