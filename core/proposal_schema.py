"""Proposal schema for V10 human-in-the-loop learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Proposal:
    """A proposed model adjustment that requires human approval."""

    proposal_id: str
    proposal_type: str
    target: str
    current_value: float
    proposed_value: float
    delta: float
    reason: str
    source_symbol: str = "UNKNOWN"
    outcome: str = "UNKNOWN"
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


def create_proposal(
    proposal_type: str,
    target: str,
    current_value: float,
    proposed_value: float,
    reason: str,
    source_symbol: str = "UNKNOWN",
    outcome: str = "UNKNOWN",
    metadata: dict[str, Any] | None = None,
) -> Proposal:
    """Create a pending proposal."""

    return Proposal(
        proposal_id=f"prop_{uuid4().hex}",
        proposal_type=proposal_type,
        target=target,
        current_value=round(float(current_value), 4),
        proposed_value=round(float(proposed_value), 4),
        delta=round(float(proposed_value) - float(current_value), 4),
        reason=reason,
        source_symbol=source_symbol,
        outcome=outcome,
        metadata=metadata or {},
    )
