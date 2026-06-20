"""In-memory research knowledge base store."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable
import uuid

from .kb_contract import ResearchKnowledgeBase, ResearchRecord


class KBStore:
    def __init__(self) -> None:
        self._kb = ResearchKnowledgeBase()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _touch(self) -> None:
        self._kb.version += 1

    def add_record(self, record: ResearchRecord | dict[str, Any]) -> ResearchRecord:
        if isinstance(record, ResearchRecord):
            item = record
        else:
            item = ResearchRecord(
                record_id=str(record.get("record_id", uuid.uuid4().hex)),
                symbol=str(record.get("symbol", "UNKNOWN")),
                period=str(record.get("period", "TTM")),
                strategic_score=float(record.get("strategic_score", 0.0)),
                final_decision=str(record.get("final_decision", "WATCH")),
                confidence_score=float(record.get("confidence_score", 0.0)),
                evidence_refs=dict(record.get("evidence_refs", {})),
                explanation_summary=str(record.get("explanation_summary", "")),
                portfolio_bucket=str(record.get("portfolio_bucket", "")),
                recommended_weight=float(record.get("recommended_weight", 0.0)),
                risk_level=str(record.get("risk_level", "")),
                rebalance_action=str(record.get("rebalance_action", "")),
                backtest_metrics=dict(record.get("backtest_metrics", {})),
                created_at=str(record.get("created_at", self._now())),
            )
        self._kb.records.append(item)
        self._kb.index_by_symbol.setdefault(item.symbol, []).append(item.record_id)
        self._kb.index_by_period.setdefault(item.period, []).append(item.record_id)
        self._touch()
        return item

    def _match(self, record_ids: Iterable[str]) -> list[ResearchRecord]:
        wanted = set(record_ids)
        return [record for record in self._kb.records if record.record_id in wanted]

    def get_by_symbol(self, symbol: str) -> list[ResearchRecord]:
        return [record for record in self._kb.records if record.symbol == symbol]

    def get_by_period(self, period: str) -> list[ResearchRecord]:
        return [record for record in self._kb.records if record.period == period]

    def get_latest_by_symbol(self, symbol: str) -> ResearchRecord | None:
        records = self.get_by_symbol(symbol)
        if not records:
            return None
        return sorted(records, key=lambda item: (item.created_at, item.record_id))[-1]

    def list_records(self) -> list[ResearchRecord]:
        return list(self._kb.records)

    @property
    def kb(self) -> ResearchKnowledgeBase:
        return self._kb

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [asdict(item) for item in self._kb.records],
            "index_by_symbol": dict(self._kb.index_by_symbol),
            "index_by_period": dict(self._kb.index_by_period),
            "version": self._kb.version,
        }


DEFAULT_KB_STORE = KBStore()

