"""Multi-symbol A-share market data ingestion for V12."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Iterable

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ak = None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _column_name(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lowered = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


@dataclass(frozen=True)
class SymbolSnapshot:
    symbol: str
    trend: float
    volatility: float
    momentum: float
    breadth: float
    liquidity: float
    volume_pressure: float
    close: float
    data_source: str
    data_status: str
    timestamp: str


class MultiSymbolDataEngine:
    """Fetch and normalize multiple A-share symbols."""

    def __init__(
        self,
        *,
        lookback_days: int = 90,
        cache_dir: str | Path = Path("reports") / "cache" / "v12_symbols",
    ) -> None:
        self.lookback_days = max(30, lookback_days)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol}.json"

    @staticmethod
    def _akshare_symbol(symbol: str) -> str:
        code = str(symbol).strip()
        if code.startswith(("sh", "sz")):
            return code
        return ("sh" if code.startswith("6") else "sz") + code

    def _load_cache(self, symbol: str) -> SymbolSnapshot | None:
        path = self._cache_path(symbol)
        if not path.exists():
            return None
        try:
            return SymbolSnapshot(**json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def _save_cache(self, snapshot: SymbolSnapshot) -> None:
        try:
            self._cache_path(snapshot.symbol).write_text(
                json.dumps(asdict(snapshot), ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _fetch_history(self, symbol: str):
        if ak is None:
            raise RuntimeError("akshare is not installed.")
        return ak.stock_zh_a_daily(symbol=self._akshare_symbol(symbol))

    def _build_snapshot(self, symbol: str, frame, *, data_source: str, data_status: str) -> SymbolSnapshot:
        if frame is None or len(frame) == 0:
            raise ValueError(f"No historical data for {symbol}.")

        columns = list(frame.columns)
        close_col = _column_name(columns, ["close", "收盘", "收盘价"])
        high_col = _column_name(columns, ["high", "最高", "最高价"])
        low_col = _column_name(columns, ["low", "最低", "最低价"])
        volume_col = _column_name(columns, ["volume", "成交量", "vol"])
        date_col = _column_name(columns, ["date", "日期", "datetime", "时间"])
        if not close_col or not high_col or not low_col:
            raise ValueError(f"Missing OHLC columns for {symbol}.")

        rows = frame.tail(min(len(frame), self.lookback_days)).to_dict("records")
        latest = rows[-1]
        previous = rows[-2] if len(rows) >= 2 else latest
        close = float(latest[close_col])
        prev_close = float(previous[close_col]) if previous.get(close_col) is not None else close
        high = float(latest[high_col])
        low = float(latest[low_col])

        moving_average = mean(float(row[close_col]) for row in rows)
        trend_ratio = close / moving_average if moving_average else 1.0
        trend = _clamp((trend_ratio - 0.95) / 0.12, 0.0, 1.0)
        volatility = _clamp(((high - low) / close if close else 0.0) / 0.06, 0.0, 1.0)
        momentum = _clamp((close / prev_close - 0.99) / 0.03 if prev_close else 0.0, 0.0, 1.0)
        breadth = _clamp(0.40 + 0.30 * trend - 0.20 * volatility + 0.20 * momentum, 0.0, 1.0)
        if volume_col:
            volumes = [float(row[volume_col]) for row in rows if row.get(volume_col) is not None]
            volume_ratio = float(latest[volume_col]) / max(mean(volumes), 1.0) if volumes else 1.0
        else:
            volume_ratio = 1.0
        liquidity = _clamp(0.35 + 0.35 * (1.0 - volatility) + 0.20 * momentum + 0.10 * _clamp(volume_ratio, 0.0, 2.0) / 2.0, 0.0, 1.0)
        volume_pressure = _clamp(0.30 + 0.45 * trend - 0.25 * volatility + 0.10 * momentum, 0.0, 1.0)
        timestamp = str(latest[date_col]) if date_col and latest.get(date_col) is not None else _now_iso()

        return SymbolSnapshot(
            symbol=symbol,
            trend=round(trend, 4),
            volatility=round(volatility, 4),
            momentum=round(momentum, 4),
            breadth=round(breadth, 4),
            liquidity=round(liquidity, 4),
            volume_pressure=round(volume_pressure, 4),
            close=round(close, 4),
            data_source=data_source,
            data_status=data_status,
            timestamp=timestamp,
        )

    def _fetch_one(self, symbol: str) -> SymbolSnapshot:
        frame = self._fetch_history(symbol)
        snapshot = self._build_snapshot(symbol, frame, data_source="AKSHARE", data_status="LIVE")
        self._save_cache(snapshot)
        return snapshot

    def fetch_symbols(self, symbols: Iterable[str]) -> list[SymbolSnapshot]:
        snapshots: list[SymbolSnapshot] = []
        for symbol in symbols:
            try:
                snapshots.append(self._fetch_one(symbol))
            except Exception:
                cached = self._load_cache(symbol)
                if cached is not None:
                    snapshots.append(
                        SymbolSnapshot(
                            symbol=cached.symbol,
                            trend=cached.trend,
                            volatility=cached.volatility,
                            momentum=cached.momentum,
                            breadth=cached.breadth,
                            liquidity=cached.liquidity,
                            volume_pressure=cached.volume_pressure,
                            close=cached.close,
                            data_source=cached.data_source,
                            data_status="STALE",
                            timestamp=cached.timestamp,
                        )
                    )
                else:
                    snapshots.append(
                        SymbolSnapshot(
                            symbol=symbol,
                            trend=0.50,
                            volatility=0.50,
                            momentum=0.50,
                            breadth=0.50,
                            liquidity=0.50,
                            volume_pressure=0.50,
                            close=0.0,
                            data_source="MOCK",
                            data_status="STALE",
                            timestamp=_now_iso(),
                        )
                    )
        return snapshots
