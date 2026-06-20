from __future__ import annotations

import unittest

from src.knowledge_base.kb_query import KBQuery
from src.knowledge_base.kb_store import KBStore
from src.knowledge_base.kb_summary import KBSummary


class KBSummaryTest(unittest.TestCase):
    def test_summary_trends(self) -> None:
        store = KBStore()
        store.add_record({"record_id": "1", "symbol": "000001.SZ", "period": "2026Q1", "strategic_score": 80, "final_decision": "WATCH", "confidence_score": 0.60, "risk_level": "MEDIUM", "rebalance_action": "HOLD"})
        store.add_record({"record_id": "2", "symbol": "000001.SZ", "period": "2026Q2", "strategic_score": 90, "final_decision": "BUY", "confidence_score": 0.75, "risk_level": "LOW", "rebalance_action": "ADD"})
        summary = KBSummary(KBQuery(store)).render_summary("000001.SZ")
        self.assertEqual(len(summary["score_trend"]), 2)
        self.assertEqual(summary["decision_history"], ["WATCH", "BUY"])
        self.assertEqual(len(summary["confidence_trend"]), 2)
        self.assertEqual(len(summary["risk_history"]), 2)
        self.assertEqual(len(summary["rebalance_history"]), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
