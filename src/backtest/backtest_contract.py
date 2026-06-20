"""Backtest contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BacktestConfig:
    start_date: str
    end_date: str
    initial_cash: float
    rebalance_frequency: str
    transaction_cost: float
    slippage: float


@dataclass(frozen=True)
class BacktestPosition:
    symbol: str
    weight: float
    shares: float
    market_value: float
    cost_basis: float


@dataclass(frozen=True)
class BacktestResult:
    period: str
    equity_curve: list[dict[str, Any]]
    total_return: float
    annualized_return: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    turnover: float
    win_rate: float
    warnings: list[str] = field(default_factory=list)

