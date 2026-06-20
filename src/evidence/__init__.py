"""Evidence chain helpers.

This package exposes optional evidence tracing objects that can be attached
to factor inputs, scores, and research decisions without changing the
primary research pipeline contracts.
"""

from .evidence_contract import EvidenceChain, EvidenceNode
from .evidence_chain_builder import EvidenceChainBuilder
from .evidence_formatter import format_evidence_summary

__all__ = [
    "EvidenceChain",
    "EvidenceChainBuilder",
    "EvidenceNode",
    "format_evidence_summary",
]
