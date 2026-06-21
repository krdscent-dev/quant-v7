"""System-level performance attribution for V12.6 backtests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class V126AttributionResult:
    total_pnl: float
    total_return: float
    market_contribution: float
    capital_contribution: float
    execution_contribution: float
    trade_count: int
    win_rate: float
    layer_breakdown: dict[str, float]
    warnings: list[str]


class V126AttributionEngine:
    """Aggregate trade logs into layer contribution metrics."""

    def analyze(self, trades: list[Mapping[str, Any]], starting_equity: float) -> V126AttributionResult:
        total_pnl = 0.0
        positive_trades = 0
        layer_totals = {
            "market_structure": 0.0,
            "capital_control": 0.0,
            "execution": 0.0,
        }
        warnings: list[str] = []

        for trade in trades:
            pnl = float(trade.get("pnl", 0.0) or 0.0)
            total_pnl += pnl
            if pnl > 0:
                positive_trades += 1
            contributions = trade.get("layer_contributions", {}) or {}
            for layer in layer_totals:
                layer_totals[layer] += float(contributions.get(layer, 0.0) or 0.0)

        trade_count = len(trades)
        if trade_count == 0:
            warnings.append("no_trade_logs")
        win_rate = positive_trades / trade_count if trade_count else 0.0
        total_return = total_pnl / starting_equity if starting_equity else 0.0

        return V126AttributionResult(
            total_pnl=round(total_pnl, 6),
            total_return=round(total_return, 6),
            market_contribution=round(layer_totals["market_structure"], 6),
            capital_contribution=round(layer_totals["capital_control"], 6),
            execution_contribution=round(layer_totals["execution"], 6),
            trade_count=trade_count,
            win_rate=round(win_rate, 4),
            layer_breakdown={key: round(value, 6) for key, value in layer_totals.items()},
            warnings=warnings,
        )

