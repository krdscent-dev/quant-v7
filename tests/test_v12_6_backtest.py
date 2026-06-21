from __future__ import annotations

from tempfile import TemporaryDirectory
from types import SimpleNamespace

from analytics.attribution_engine import AttributionEngine
from backtest.v12_6_backtest_engine import V126BacktestEngine
from logs.trade_logger import TradeLogger


def _sample_v11_decisions() -> list[dict[str, object]]:
    return [
        {
            "symbol": "000977.SZ",
            "final_weighted_decision": "SMALL_ADD",
            "alpha_score": 0.95,
            "risk_score": 0.18,
            "sector_context": {"sector": "AI Computing", "sector_strength": 0.96},
            "market_intelligence": {"capital_flow_score": 0.91},
        },
        {
            "symbol": "688041.SH",
            "final_weighted_decision": "HOLD",
            "alpha_score": 0.74,
            "risk_score": 0.22,
            "sector_context": {"sector": "Huawei Ascend Ecosystem", "sector_strength": 0.91},
            "market_intelligence": {"capital_flow_score": 0.87},
        },
    ]


def test_v126_backtest_simulation():
    with TemporaryDirectory() as temp_dir:
        logger = TradeLogger(f"{temp_dir}/trade_log.jsonl")
        engine = V126BacktestEngine(trade_logger=logger, attribution_engine=AttributionEngine())
        result = engine.simulate(
            market_state={
                "regime": "TRANSITION",
                "structure": SimpleNamespace(structure_strength=0.6),
            },
            capital_state={"capital_bias": "BALANCED", "allocation_ceiling": 0.1, "risk_score": 0.2},
            decisions=[],
            v11_decisions=_sample_v11_decisions(),
            periods=3,
        )

        assert result.trade_count == 6
        assert result.equity_curve
        assert set(result.layer_attribution) == {"market_structure", "capital_control", "execution"}
        assert logger.path.exists()
        assert logger.read_trades()
        assert result.total_return != 0.0


def test_attribution_engine_aggregates_layers():
    engine = AttributionEngine()
    result = engine.analyze(
        [
            {
                "pnl": 0.02,
                "layer_contributions": {"market_structure": 0.006, "capital_control": 0.005, "execution": 0.009},
            },
            {
                "pnl": -0.01,
                "layer_contributions": {"market_structure": -0.003, "capital_control": -0.002, "execution": -0.005},
            },
        ],
        starting_equity=100.0,
    )

    assert result.trade_count == 2
    assert result.market_structure_contribution == 0.003
    assert result.capital_control_contribution == 0.003
    assert result.execution_contribution == 0.004
