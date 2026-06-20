"""Rebalance contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class CurrentHolding:
    symbol: str
    current_weight: float
    market_value: float
    cost_basis: float
    unrealized_return: float


@dataclass(frozen=True)
class RebalanceAction:
    symbol: str
    current_weight: float
    target_weight: float
    delta_weight: float
    action: str
    reason: str
    priority: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RebalancePlan:
    period: str
    actions: list[RebalanceAction]
    total_buy_weight: float
    total_sell_weight: float
    turnover: float
    summary: str
    warnings: list[str] = field(default_factory=list)

