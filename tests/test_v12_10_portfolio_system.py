from __future__ import annotations

from portfolio.alpha_ranker import AlphaRanker
from portfolio.multi_symbol_data_engine import SymbolSnapshot
from portfolio.portfolio_allocator import PortfolioAllocator


def _snapshot(symbol: str, trend: float, volatility: float, momentum: float, breadth: float, liquidity: float, volume_pressure: float) -> SymbolSnapshot:
    return SymbolSnapshot(
        symbol=symbol,
        trend=trend,
        volatility=volatility,
        momentum=momentum,
        breadth=breadth,
        liquidity=liquidity,
        volume_pressure=volume_pressure,
        close=10.0,
        data_source="AKSHARE",
        data_status="LIVE",
        timestamp="2026-06-21T00:00:00+00:00",
    )


def test_alpha_ranker_orders_symbols_cross_sectionally() -> None:
    ranker = AlphaRanker()
    snapshots = [
        _snapshot("AAA", 0.90, 0.10, 0.85, 0.90, 0.85, 0.80),
        _snapshot("BBB", 0.60, 0.40, 0.55, 0.60, 0.50, 0.50),
        _snapshot("CCC", 0.30, 0.70, 0.20, 0.30, 0.25, 0.20),
    ]

    ranked = ranker.rank(snapshots)

    assert [item.symbol for item in ranked] == ["AAA", "BBB", "CCC"]
    assert ranked[0].alpha_score > ranked[1].alpha_score > ranked[2].alpha_score


def test_portfolio_allocator_weights_sum_to_one() -> None:
    ranker = AlphaRanker()
    allocator = PortfolioAllocator()
    snapshots = [
        _snapshot("AAA", 0.90, 0.10, 0.85, 0.90, 0.85, 0.80),
        _snapshot("BBB", 0.60, 0.40, 0.55, 0.60, 0.50, 0.50),
        _snapshot("CCC", 0.30, 0.70, 0.20, 0.30, 0.25, 0.20),
    ]

    ranked = ranker.rank(snapshots)
    weights = allocator.allocate(ranked)

    assert abs(sum(item.weight for item in weights) - 1.0) < 1e-9
    assert weights[0].weight >= weights[1].weight >= weights[2].weight


def test_portfolio_allocator_keeps_rank_and_data_status() -> None:
    ranker = AlphaRanker()
    allocator = PortfolioAllocator()
    snapshots = [
        _snapshot("AAA", 0.80, 0.20, 0.75, 0.70, 0.80, 0.70),
        _snapshot("BBB", 0.50, 0.50, 0.50, 0.50, 0.50, 0.50),
    ]

    ranked = ranker.rank(snapshots)
    weights = allocator.allocate(ranked)

    assert [item.symbol for item in weights] == ["AAA", "BBB"]
    assert all(item.data_status == "LIVE" for item in weights)

