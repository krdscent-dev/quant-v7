"""Evidence contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceNode:
    node_id: str
    node_type: str
    symbol: str
    period: str
    name: str
    value: Any
    source: str
    provider: str
    validation_status: str
    confidence_score: float
    warnings: list[str] = field(default_factory=list)
    parent_ids: list[str] = field(default_factory=list)
    source_field: str = ""
    mapped_field: str = ""
    confidence_breakdown: dict[str, Any] | None = None


@dataclass(frozen=True)
class EvidenceChain:
    symbol: str
    period: str
    nodes: list[EvidenceNode]
    root_node_id: str
    overall_confidence: float
    warnings: list[str] = field(default_factory=list)

