"""Knowledge base query helpers."""

from __future__ import annotations

from typing import Any

from .kb_contract import ResearchRecord
from .kb_store import KBStore, DEFAULT_KB_STORE


class KBQuery:
    def __init__(self, store: KBStore | None = None) -> None:
        self.store = store or DEFAULT_KB_STORE

    def score_history(self, symbol: str) -> list[dict[str, Any]]:
        return [
            {
                "period": record.period,
                "strategic_score": record.strategic_score,
                "confidence_score": record.confidence_score,
                "created_at": record.created_at,
            }
            for record in self.store.get_by_symbol(symbol)
        ]

    def decision_history(self, symbol: str) -> list[dict[str, Any]]:
        return [
            {
                "period": record.period,
                "final_decision": record.final_decision,
                "rebalance_action": record.rebalance_action,
                "created_at": record.created_at,
            }
            for record in self.store.get_by_symbol(symbol)
        ]

    def records_by_period(self, period: str) -> list[ResearchRecord]:
        return self.store.get_by_period(period)

    def high_score_low_confidence(self, min_score: float = 75.0, max_confidence: float = 0.65) -> list[ResearchRecord]:
        return [
            record
            for record in self.store.list_records()
            if record.strategic_score >= min_score and record.confidence_score < max_confidence
        ]

    def high_risk_records(self) -> list[ResearchRecord]:
        return [
            record
            for record in self.store.list_records()
            if str(record.risk_level).upper() in {"HIGH", "CRITICAL"}
        ]

