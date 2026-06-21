"""Virtual portfolio used by the V12 paper trading engine.

The portfolio keeps a paper cash ledger, open positions, realized fills,
mark-to-market valuation, and drawdown tracking without placing real orders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class VirtualPosition:
    symbol: str
    quantity: float
    average_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float


@dataclass(frozen=True)
class PaperTrade:
    timestamp: str
    symbol: str
    action: str
    requested_notional: float
    filled_notional: float
    fill_ratio: float
    fill_probability: float
    slippage: float
    fill_price: float
    quantity: float
    status: str
    reason: str


@dataclass(frozen=True)
class PortfolioSnapshot:
    timestamp: str
    initial_capital: float
    cash: float
    portfolio_value: float
    daily_pnl: float
    total_pnl: float
    drawdown: float
    status: str
    positions: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)


class PaperPortfolio:
    """Track a fully virtual portfolio for paper trading."""

    BUY_ACTIONS = {"BUY", "ADD", "SMALL_ADD"}
    SELL_ACTIONS = {"REDUCE", "SELL", "EXIT"}
    PASSIVE_ACTIONS = {"HOLD", "OBSERVE"}

    def __init__(self, initial_capital: float = 1_000_000.0) -> None:
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self._positions: dict[str, dict[str, float]] = {}
        self._last_prices: dict[str, float] = {}
        self._trade_history: list[PaperTrade] = []
        self._last_equity = float(initial_capital)
        self._peak_equity = float(initial_capital)
        self._status = "LIVE"

    @property
    def trade_history(self) -> list[dict[str, Any]]:
        return [asdict(trade) for trade in self._trade_history]

    def position_count(self) -> int:
        return len(self._positions)

    def current_exposure(self) -> float:
        portfolio_value = self.portfolio_value()
        if portfolio_value <= 0:
            return 0.0
        invested = sum(self._position_market_value(symbol) for symbol in self._positions)
        return _clamp(invested / portfolio_value, 0.0, 1.0)

    def position_value(self, symbol: str) -> float:
        return self._position_market_value(str(symbol))

    def position_quantity(self, symbol: str) -> float:
        position = self._positions.get(str(symbol))
        if not position:
            return 0.0
        return float(position.get("quantity", 0.0))

    def portfolio_value(self) -> float:
        invested = sum(self._position_market_value(symbol) for symbol in self._positions)
        return float(self.cash + invested)

    def drawdown(self) -> float:
        current_value = self.portfolio_value()
        if self._peak_equity <= 0:
            return 0.0
        return _clamp((self._peak_equity - current_value) / self._peak_equity, 0.0, 1.0)

    def positions_as_dicts(self) -> list[dict[str, Any]]:
        summary = []
        for symbol in sorted(self._positions):
            summary.append(self._position_summary(symbol))
        return summary

    def mark_to_market(self, price_map: Mapping[str, float], timestamp: str, status: str = "LIVE") -> PortfolioSnapshot:
        self._status = status
        for symbol, price in price_map.items():
            self._last_prices[str(symbol)] = max(0.0, float(price))
        portfolio_value = self.portfolio_value()
        daily_pnl = portfolio_value - self._last_equity
        self._last_equity = portfolio_value
        self._peak_equity = max(self._peak_equity, portfolio_value)
        total_pnl = portfolio_value - self.initial_capital
        drawdown = self.drawdown()
        return PortfolioSnapshot(
            timestamp=timestamp,
            initial_capital=round(self.initial_capital, 4),
            cash=round(self.cash, 4),
            portfolio_value=round(portfolio_value, 4),
            daily_pnl=round(daily_pnl, 4),
            total_pnl=round(total_pnl, 4),
            drawdown=round(drawdown, 4),
            status=status,
            positions=self.positions_as_dicts(),
            trades=self.trade_history,
        )

    def apply_trade(
        self,
        *,
        timestamp: str,
        symbol: str,
        action: str,
        requested_notional: float,
        execution_price: float,
        fill_ratio: float,
        fill_probability: float,
        slippage: float,
        reason: str,
        status: str,
    ) -> PaperTrade:
        symbol = str(symbol)
        action = str(action).upper()
        requested_notional = max(0.0, float(requested_notional))
        execution_price = max(0.0, float(execution_price))
        fill_ratio = _clamp(fill_ratio, 0.0, 1.0)
        fill_probability = _clamp(fill_probability, 0.0, 1.0)
        slippage = max(0.0, float(slippage))
        status = str(status).upper()

        if action in self.PASSIVE_ACTIONS or requested_notional <= 0.0 or execution_price <= 0.0:
            trade = PaperTrade(
                timestamp=timestamp,
                symbol=symbol,
                action=action,
                requested_notional=round(requested_notional, 4),
                filled_notional=0.0,
                fill_ratio=0.0,
                fill_probability=round(fill_probability, 4),
                slippage=round(slippage, 6),
                fill_price=round(execution_price, 4),
                quantity=0.0,
                status="NO_ACTION",
                reason=reason,
            )
            self._trade_history.append(trade)
            self._last_prices.setdefault(symbol, execution_price)
            return trade

        filled_notional = requested_notional * fill_ratio
        if action in self.BUY_ACTIONS:
            quantity = filled_notional / execution_price
            position = self._positions.get(symbol, {"quantity": 0.0, "average_cost": 0.0, "last_price": execution_price})
            current_quantity = float(position.get("quantity", 0.0))
            current_cost = float(position.get("average_cost", 0.0))
            total_cost = current_quantity * current_cost + filled_notional
            new_quantity = current_quantity + quantity
            average_cost = total_cost / new_quantity if new_quantity > 0 else 0.0
            self._positions[symbol] = {
                "quantity": new_quantity,
                "average_cost": average_cost,
                "last_price": execution_price,
            }
            self.cash -= filled_notional
        elif action in self.SELL_ACTIONS:
            position = self._positions.get(symbol)
            current_quantity = float(position.get("quantity", 0.0)) if position else 0.0
            quantity = min(current_quantity, filled_notional / execution_price)
            filled_notional = quantity * execution_price
            new_quantity = max(0.0, current_quantity - quantity)
            if position is not None:
                if new_quantity <= 0.0:
                    self._positions.pop(symbol, None)
                else:
                    position["quantity"] = new_quantity
                    position["last_price"] = execution_price
            self.cash += filled_notional
        else:
            quantity = 0.0

        self._last_prices[symbol] = execution_price
        trade = PaperTrade(
            timestamp=timestamp,
            symbol=symbol,
            action=action,
            requested_notional=round(requested_notional, 4),
            filled_notional=round(filled_notional, 4),
            fill_ratio=round(fill_ratio, 4),
            fill_probability=round(fill_probability, 4),
            slippage=round(slippage, 6),
            fill_price=round(execution_price, 4),
            quantity=round(quantity, 6),
            status=status if fill_ratio >= 1.0 else "PARTIAL_FILL",
            reason=reason,
        )
        self._trade_history.append(trade)
        return trade

    def _position_market_value(self, symbol: str) -> float:
        position = self._positions.get(symbol)
        if not position:
            return 0.0
        last_price = self._last_prices.get(symbol, float(position.get("last_price", 0.0) or 0.0))
        return float(position.get("quantity", 0.0)) * last_price

    def _position_summary(self, symbol: str) -> dict[str, Any]:
        position = self._positions.get(symbol, {"quantity": 0.0, "average_cost": 0.0, "last_price": 0.0})
        quantity = float(position.get("quantity", 0.0))
        average_cost = float(position.get("average_cost", 0.0))
        last_price = self._last_prices.get(symbol, float(position.get("last_price", 0.0) or 0.0))
        market_value = quantity * last_price
        unrealized_pnl = (last_price - average_cost) * quantity
        return {
            "symbol": symbol,
            "quantity": round(quantity, 6),
            "average_cost": round(average_cost, 4),
            "last_price": round(last_price, 4),
            "market_value": round(market_value, 4),
            "unrealized_pnl": round(unrealized_pnl, 4),
        }
