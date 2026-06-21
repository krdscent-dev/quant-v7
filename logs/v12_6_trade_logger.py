"""System-level trade logger for V12.6 backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import json


@dataclass(frozen=True)
class V126TradeLogEntry:
    timestamp: str
    symbol: str
    action: str
    future_return: float
    volatility: float
    size: float
    slippage: float
    fill_probability: float
    fill_factor: float
    pnl: float
    market_state: dict[str, Any]
    capital_state: dict[str, Any]
    decision: dict[str, Any]
    layer_contributions: dict[str, float]
    context: dict[str, Any]


class V126TradeLogger:
    """Append-only JSONL logger for system-level backtests."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_trade(self, trade: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(trade)
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return payload

    def read_trades(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

