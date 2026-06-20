from __future__ import annotations

import unittest

from src.knowledge_base.kb_contract import ResearchRecord
from src.knowledge_base.kb_store import KBStore


class KBStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = KBStore()

    def test_record_creation_and_query(self) -> None:
        record = self.store.add_record(
            ResearchRecord(
                record_id="r1",
                symbol="000001.SZ",
                period="2026Q1",
                strategic_score=82.0,
                final_decision="BUY",
                confidence_score=0.82,
                evidence_refs={"evidence_chain": {"symbol": "000001.SZ"}},
                explanation_summary="sample",
                portfolio_bucket="CORE",
                recommended_weight=0.08,
                risk_level="LOW",
                rebalance_action="BUY",
                backtest_metrics={"sharpe_ratio": 1.2},
                created_at="2026-06-01T00:00:00+00:00",
            )
        )
        self.assertEqual(record.symbol, "000001.SZ")
        self.assertEqual(self.store.get_by_symbol("000001.SZ")[0].record_id, "r1")
        self.assertEqual(self.store.get_latest_by_symbol("000001.SZ").record_id, "r1")
        self.assertEqual(len(self.store.get_by_period("2026Q1")), 1)

    def test_list_records(self) -> None:
        self.store.add_record({"symbol": "000002.SZ", "period": "2026Q1", "strategic_score": 60, "final_decision": "WATCH", "confidence_score": 0.7})
        self.assertEqual(len(self.store.list_records()), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
