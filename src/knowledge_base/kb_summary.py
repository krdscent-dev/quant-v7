"""Knowledge base summary helpers."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .kb_query import KBQuery


class KBSummary:
    def __init__(self, query: KBQuery | None = None) -> None:
        self.query = query or KBQuery()

    def score_trend(self, symbol: str) -> list[dict[str, Any]]:
        history = self.query.score_history(symbol)
        return [
            {
                "period": item["period"],
                "strategic_score": item["strategic_score"],
            }
            for item in history
        ]

    def decision_history(self, symbol: str) -> list[str]:
        return [item["final_decision"] for item in self.query.decision_history(symbol)]

    def confidence_trend(self, symbol: str) -> list[dict[str, Any]]:
        history = self.query.score_history(symbol)
        return [
            {
                "period": item["period"],
                "confidence_score": item["confidence_score"],
            }
            for item in history
        ]

    def risk_history(self, symbol: str) -> list[dict[str, Any]]:
        return [
            {
                "period": record.period,
                "risk_level": record.risk_level,
            }
            for record in self.query.store.get_by_symbol(symbol)
        ]

    def rebalance_history(self, symbol: str) -> list[dict[str, Any]]:
        return [
            {
                "period": record.period,
                "rebalance_action": record.rebalance_action,
            }
            for record in self.query.store.get_by_symbol(symbol)
        ]

    def render_summary(self, symbol: str) -> dict[str, Any]:
        score_trend = self.score_trend(symbol)
        confidence_trend = self.confidence_trend(symbol)
        return {
            "symbol": symbol,
            "score_trend": score_trend,
            "decision_history": self.decision_history(symbol),
            "confidence_trend": confidence_trend,
            "risk_history": self.risk_history(symbol),
            "rebalance_history": self.rebalance_history(symbol),
            "avg_score": mean([item["strategic_score"] for item in score_trend]) if score_trend else 0.0,
            "avg_confidence": mean([item["confidence_score"] for item in confidence_trend]) if confidence_trend else 0.0,
        }

