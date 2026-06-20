"""Backtest metrics helpers."""

from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev
from typing import Any, Sequence


class BacktestMetrics:
    def total_return(self, equity_curve: Sequence[float]) -> float:
        if len(equity_curve) < 2 or equity_curve[0] == 0:
            return 0.0
        return round((equity_curve[-1] / equity_curve[0]) - 1.0, 6)

    def annualized_return(self, equity_curve: Sequence[float], periods_per_year: int = 252) -> float:
        if len(equity_curve) < 2 or equity_curve[0] <= 0:
            return 0.0
        total = equity_curve[-1] / equity_curve[0]
        years = max((len(equity_curve) - 1) / periods_per_year, 1e-9)
        return round(total ** (1.0 / years) - 1.0, 6)

    def max_drawdown(self, equity_curve: Sequence[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            if peak > 0:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        return round(max_dd, 6)

    def volatility(self, returns: Sequence[float], periods_per_year: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        return round(pstdev(returns) * sqrt(periods_per_year), 6)

    def sharpe_ratio(self, returns: Sequence[float], periods_per_year: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        std = pstdev(returns)
        if std == 0:
            return 0.0
        return round((mean(returns) / std) * sqrt(periods_per_year), 6)

    def turnover(self, trade_weights: Sequence[float]) -> float:
        return round(sum(abs(weight) for weight in trade_weights) / 2.0, 6)

    def win_rate(self, returns: Sequence[float]) -> float:
        if not returns:
            return 0.0
        wins = sum(1 for item in returns if item > 0)
        return round(wins / len(returns), 6)

