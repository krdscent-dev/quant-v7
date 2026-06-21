from __future__ import annotations

from tempfile import TemporaryDirectory

from logs.v12_6_trade_logger import V126TradeLogger


def test_v126_trade_logger_round_trips_records() -> None:
    with TemporaryDirectory() as temp_dir:
        logger = V126TradeLogger(f"{temp_dir}/trade_log.jsonl")
        payload = logger.log_trade(
            {
                "symbol": "000977.SZ",
                "action": "ADD",
                "pnl": 0.012,
                "layer_contributions": {"market_structure": 0.004, "capital_control": 0.003, "execution": 0.005},
            }
        )

        records = logger.read_trades()

        assert payload["symbol"] == "000977.SZ"
        assert records and records[0]["action"] == "ADD"

