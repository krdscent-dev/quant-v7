"""Backtest engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from .backtest_contract import BacktestConfig, BacktestResult
from .backtest_metrics import BacktestMetrics


class BacktestEngine:
    def __init__(self) -> None:
        self.metrics = BacktestMetrics()

    def _to_mapping(self, value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            return value
        if hasattr(value, "__dict__"):
            return value.__dict__
        return {}

    def _parse_date(self, value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _normalize_price_series(self, historical_price_data: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[list[str], dict[str, dict[str, float]]]:
        symbol_map: dict[str, dict[str, float]] = {}
        common_dates: list[str] | None = None
        for symbol, records in historical_price_data.items():
            series: dict[str, float] = {}
            for record in records:
                data = self._to_mapping(record)
                date = str(data.get("date", ""))
                price = float(data.get("close", data.get("price", 0.0)))
                if date:
                    series[date] = price
            ordered_dates = sorted(series)
            symbol_map[symbol] = {date: series[date] for date in ordered_dates}
            if common_dates is None:
                common_dates = ordered_dates
            else:
                common_dates = [date for date in common_dates if date in series]
        return (common_dates or []), symbol_map

    def _normalize_rebalance_plans(self, historical_rebalance_plans: Sequence[Any]) -> list[dict[str, Any]]:
        plans: list[dict[str, Any]] = []
        for item in historical_rebalance_plans:
            data = self._to_mapping(item)
            actions = []
            for action in list(data.get("actions", [])):
                action_data = self._to_mapping(action)
                actions.append(
                    {
                        "symbol": str(action_data.get("symbol", "UNKNOWN")),
                        "target_weight": float(action_data.get("target_weight", 0.0)),
                        "delta_weight": float(action_data.get("delta_weight", 0.0)),
                    }
                )
            plans.append({"date": str(data.get("date", "")), "actions": actions})
        plans.sort(key=lambda item: item["date"])
        return plans

    def _weights_from_plan(self, plan: Mapping[str, Any]) -> dict[str, float]:
        weights: dict[str, float] = {}
        for action in plan.get("actions", []):
            if not isinstance(action, Mapping):
                continue
            weights[str(action.get("symbol", "UNKNOWN"))] = max(0.0, float(action.get("target_weight", 0.0)))
        return weights

    def run(
        self,
        historical_price_data: Mapping[str, Sequence[Mapping[str, Any]]],
        historical_rebalance_plans: Sequence[Any],
        config: BacktestConfig,
    ) -> BacktestResult:
        dates, series_map = self._normalize_price_series(historical_price_data)
        plans = self._normalize_rebalance_plans(historical_rebalance_plans)
        if not dates:
            return BacktestResult(
                period=f"{config.start_date}->{config.end_date}",
                equity_curve=[],
                total_return=0.0,
                annualized_return=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                turnover=0.0,
                win_rate=0.0,
                warnings=["no_price_data"],
            )

        plan_index = 0
        current_weights: dict[str, float] = {symbol: 0.0 for symbol in series_map}
        equity = float(config.initial_cash)
        equity_curve: list[dict[str, Any]] = [{"date": dates[0], "equity": equity, "return": 0.0}]
        returns: list[float] = []
        trade_weights: list[float] = []
        warnings: list[str] = []

        for date in dates[1:]:
            while plan_index < len(plans) and plans[plan_index]["date"] <= date:
                new_weights = self._weights_from_plan(plans[plan_index])
                symbols = set(current_weights) | set(new_weights)
                turnover = sum(abs(new_weights.get(symbol, 0.0) - current_weights.get(symbol, 0.0)) for symbol in symbols) / 2.0
                if turnover > 0:
                    cost_rate = float(config.transaction_cost) + float(config.slippage)
                    equity -= equity * turnover * cost_rate
                    trade_weights.append(turnover)
                for symbol in symbols:
                    current_weights[symbol] = new_weights.get(symbol, 0.0)
                plan_index += 1

            portfolio_return = 0.0
            valid_symbol_count = 0
            for symbol, series in series_map.items():
                if date not in series:
                    continue
                prev_dates = [d for d in dates if d < date and d in series]
                if not prev_dates:
                    continue
                prev_date = prev_dates[-1]
                prev_price = series[prev_date]
                current_price = series[date]
                if prev_price <= 0:
                    continue
                symbol_return = (current_price / prev_price) - 1.0
                portfolio_return += current_weights.get(symbol, 0.0) * symbol_return
                valid_symbol_count += 1
            if valid_symbol_count == 0:
                warnings.append(f"no_valid_prices_on_{date}")
                portfolio_return = 0.0
            equity *= (1.0 + portfolio_return)
            returns.append(portfolio_return)
            equity_curve.append({"date": date, "equity": round(equity, 6), "return": round(portfolio_return, 6)})

        curve_values = [float(item["equity"]) for item in equity_curve]
        total_return = self.metrics.total_return(curve_values)
        annualized_return = self.metrics.annualized_return(curve_values)
        max_drawdown = self.metrics.max_drawdown(curve_values)
        volatility = self.metrics.volatility(returns)
        sharpe_ratio = self.metrics.sharpe_ratio(returns)
        turnover = self.metrics.turnover(trade_weights)
        win_rate = self.metrics.win_rate(returns)

        return BacktestResult(
            period=f"{config.start_date}->{config.end_date}",
            equity_curve=equity_curve,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            turnover=turnover,
            win_rate=win_rate,
            warnings=warnings,
        )

