"""简单回测模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class BacktestResult:
    """简单回测结果。"""

    total_return: float
    benchmark_return: float | None
    max_drawdown: float | None
    trades: int


def run_simple_backtest(
    signals: Sequence[float],
    prices: Sequence[float],
    benchmark_prices: Sequence[float] | None = None,
) -> BacktestResult:
    """运行一个最小化的回测流程。"""

    _ = signals
    _ = prices
    _ = benchmark_prices
    return BacktestResult(
        total_return=0.0,
        benchmark_return=None,
        max_drawdown=None,
        trades=0,
    )
