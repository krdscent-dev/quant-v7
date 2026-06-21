from __future__ import annotations

from portfolio.paper_portfolio import PaperPortfolio


def test_paper_portfolio_buy_sell_and_snapshot():
    portfolio = PaperPortfolio(initial_capital=100_000.0)

    buy_trade = portfolio.apply_trade(
        timestamp="2026-06-21T09:30:00+08:00",
        symbol="000001",
        action="BUY",
        requested_notional=10_000.0,
        execution_price=10.0,
        fill_ratio=1.0,
        fill_probability=0.9,
        slippage=0.001,
        reason="test buy",
        status="FILLED",
    )
    assert buy_trade.quantity == 1000.0
    assert portfolio.position_quantity("000001") == 1000.0
    assert portfolio.cash == 90_000.0

    snapshot = portfolio.mark_to_market({"000001": 11.0}, "2026-06-21T15:00:00+08:00")
    assert snapshot.portfolio_value == 101_000.0
    assert snapshot.total_pnl == 1_000.0
    assert snapshot.drawdown == 0.0

    sell_trade = portfolio.apply_trade(
        timestamp="2026-06-21T15:10:00+08:00",
        symbol="000001",
        action="REDUCE",
        requested_notional=5_500.0,
        execution_price=11.0,
        fill_ratio=1.0,
        fill_probability=0.8,
        slippage=0.001,
        reason="test reduce",
        status="FILLED",
    )
    assert sell_trade.quantity > 0
    assert portfolio.position_quantity("000001") < 1000.0
