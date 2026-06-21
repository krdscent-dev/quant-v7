from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.v12_paper_trading_engine import PaperSymbolSnapshot, PaperTradingEngine


def _snapshot(symbol: str, sector: str, close: float, volatility: float, trend: float, rank_seed: float) -> PaperSymbolSnapshot:
    return PaperSymbolSnapshot(
        symbol=symbol,
        name=symbol,
        sector=sector,
        close=close,
        high=close * (1.0 + volatility * 0.02),
        low=close * (1.0 - volatility * 0.02),
        volume=1_000_000.0 + rank_seed * 100_000.0,
        historical_close_series=[close * (0.96 + 0.01 * i) for i in range(20)],
        trend=trend,
        volatility=volatility,
        momentum=0.55,
        breadth=0.60,
        liquidity=0.58,
        volume_pressure=0.62,
        data_source="LIVE",
        data_status="LIVE",
        timestamp="2026-06-21T15:00:00+08:00",
    )


def test_paper_trading_engine_runs_with_mock_feed():
    class MockFeed:
        def fetch_symbols(self, symbols):
            return [
                _snapshot("000001", "AI Computing", 12.5, 0.20, 0.76, 1.0),
                _snapshot("000002", "Domestic Substitution", 8.8, 0.15, 0.64, 2.0),
                _snapshot("300750", "AI Computing", 120.0, 0.12, 0.82, 3.0),
            ]

    with TemporaryDirectory() as temp_dir:
        report_dir = Path(temp_dir) / "reports"
        log_path = Path(temp_dir) / "paper_trades.jsonl"
        engine = PaperTradingEngine(
            symbols=("000001", "000002", "300750"),
            initial_capital=100_000.0,
            feed=MockFeed(),
            report_dir=report_dir,
            log_path=log_path,
        )
        result = engine.run_once()

        assert result.source_status == "LIVE"
        assert result.decisions
        assert result.trade_records
        assert result.portfolio_snapshot["portfolio_value"] > 0
        assert Path(result.report_path).exists()
        assert log_path.exists()
        assert result.market_state["structure"]["regime"] in {"BULL", "BEAR", "RANGE", "TRANSITION"}
