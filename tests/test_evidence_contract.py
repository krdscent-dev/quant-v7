from __future__ import annotations

import unittest

from src.evidence.evidence_chain_builder import EvidenceChainBuilder
from src.evidence.evidence_contract import EvidenceChain, EvidenceNode


class EvidenceContractTest(unittest.TestCase):
    def test_dataclasses_expose_expected_fields(self) -> None:
        node = EvidenceNode(
            node_id="n1",
            node_type="RAW_DATA",
            symbol="000001.SZ",
            period="TTM",
            name="company_basic_info",
            value={"code": "000001.SZ"},
            source="RAW_DATA",
            provider="MockDataProvider",
            validation_status="PASS",
            confidence_score=1.0,
            warnings=["none"],
            parent_ids=[],
        )
        chain = EvidenceChain(
            symbol="000001.SZ",
            period="TTM",
            nodes=[node],
            root_node_id="n1",
            overall_confidence=1.0,
            warnings=[],
        )
        self.assertEqual(chain.root_node_id, "n1")
        self.assertEqual(chain.nodes[0].confidence_score, 1.0)

