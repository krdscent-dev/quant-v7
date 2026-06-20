from __future__ import annotations

import unittest

from src.knowledge_base.kb_store import KBStore
from src.knowledge_base.kb_query import KBQuery


class KBQueryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = KBStore()
        self.store.add_record({"record_id": "1", "symbol": "000001.SZ", "period": "2026Q1", "strategic_score": 88, "final_decision": "BUY", "confidence_score": 0.55, "risk_level": "HIGH"})
        self.store.add_record({"record_id": "2", "symbol": "000001.SZ", "period": "2026Q2", "strategic_score": 92, "final_decision": "WATCH", "confidence_score": 0.40, "risk_level": "CRITICAL"})
        self.store.add_record({"record_id": "3", "symbol": "000002.SZ", "period": "2026Q2", "strategic_score": 70, "final_decision": "REVIEW", "confidence_score": 0.80, "risk_level": "LOW"})
        self.query = KBQuery(self.store)

    def test_score_and_decision_history(self) -> None:
        self.assertEqual(len(self.query.score_history("000001.SZ")), 2)
        self.assertEqual(len(self.query.decision_history("000001.SZ")), 2)

    def test_records_by_period(self) -> None:
        self.assertEqual(len(self.query.records_by_period("2026Q2")), 2)

    def test_high_score_low_confidence(self) -> None:
        records = self.query.high_score_low_confidence()
        self.assertEqual(len(records), 2)

    def test_high_risk_records(self) -> None:
        records = self.query.high_risk_records()
        self.assertEqual(len(records), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
