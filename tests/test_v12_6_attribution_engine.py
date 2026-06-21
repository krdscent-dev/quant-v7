from __future__ import annotations

from analytics.v12_6_attribution_engine import V126AttributionEngine


def test_v126_attribution_engine_aggregates_layers() -> None:
    engine = V126AttributionEngine()
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
    assert result.market_contribution == 0.003
    assert result.capital_contribution == 0.003
    assert result.execution_contribution == 0.004
    assert 0.0 <= result.win_rate <= 1.0

