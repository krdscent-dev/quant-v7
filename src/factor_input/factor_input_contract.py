"""FactorInput contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class FactorInputContract:
    """Schema for one factor input record."""

    symbol: str
    period: str
    factor_name: str
    value: float
    source_field: str
    provider: str
    validation_status: str
    confidence_score: float
    warnings: Sequence[str] = field(default_factory=tuple)


FactorInput = dict[str, Any]


def normalize_factor_input(payload: Mapping[str, Any]) -> FactorInput:
    """Return a dict-shaped factor input for backward compatibility."""

    return dict(payload)

