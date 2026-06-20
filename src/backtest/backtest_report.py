"""Backtest report helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .backtest_contract import BacktestConfig, BacktestResult


@dataclass(frozen=True)
class BacktestReport:
    """Render research backtest outputs."""

    def to_dict(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        rebalance_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "period": result.period,
            "config": {
                "start_date": config.start_date,
                "end_date": config.end_date,
                "initial_cash": config.initial_cash,
                "rebalance_frequency": config.rebalance_frequency,
                "transaction_cost": config.transaction_cost,
                "slippage": config.slippage,
            },
            "metrics": {
                "total_return": result.total_return,
                "annualized_return": result.annualized_return,
                "max_drawdown": result.max_drawdown,
                "volatility": result.volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "turnover": result.turnover,
                "win_rate": result.win_rate,
            },
            "equity_curve": list(result.equity_curve),
            "rebalance_count": rebalance_count,
            "warnings": list(result.warnings),
        }

    def render_markdown(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        rebalance_count: int = 0,
    ) -> str:
        summary = self.to_dict(result, config, rebalance_count)
        lines: list[str] = []
        lines.append("## 36. Backtest Result")
        lines.append(f"- period: {summary['period']}")
        lines.append(f"- rebalance_count: {summary['rebalance_count']}")
        lines.append("")
        lines.append("## 37. Backtest Summary")
        lines.append(f"- total_return: {summary['metrics']['total_return']:.4f}")
        lines.append(f"- annualized_return: {summary['metrics']['annualized_return']:.4f}")
        lines.append(f"- max_drawdown: {summary['metrics']['max_drawdown']:.4f}")
        lines.append("")
        lines.append("## 38. Backtest Metrics")
        lines.append(f"- volatility: {summary['metrics']['volatility']:.4f}")
        lines.append(f"- sharpe_ratio: {summary['metrics']['sharpe_ratio']:.4f}")
        lines.append(f"- turnover: {summary['metrics']['turnover']:.4f}")
        lines.append(f"- win_rate: {summary['metrics']['win_rate']:.4f}")
        lines.append("")
        lines.append("## 39. Equity Curve")
        for item in summary["equity_curve"][:10]:
            lines.append(f"- {item['date']}: {float(item['equity']):.2f}")
        if not summary["equity_curve"]:
            lines.append("- none")
        lines.append("")
        lines.append("## 40. Backtest Warnings")
        if summary["warnings"]:
            for item in summary["warnings"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        return "\n".join(lines)
