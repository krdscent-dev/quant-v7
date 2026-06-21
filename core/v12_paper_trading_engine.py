"""V12 paper trading engine.

The engine reuses the V12 market brain, capital control, and decision layers
to run a live simulation against real A-share market data without placing real
orders. Execution is simulated through a deterministic slippage and fill model.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import os
import random
import time
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

try:  # pragma: no cover - optional dependency
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ak = None

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.decision_engine import DecisionEngine
from core.v12_1_structure_engine import MarketStructureEngine
from core.v12_2_capital_flow_engine import CapitalFlowEngine
from core.v12_3_narrative_engine import NarrativeEngine
from core.v12_4_cycle_engine import CycleEngine
from core.v12_5_capital_control_engine import CapitalControlEngine
from portfolio.alpha_ranker import AlphaRanker, RankedSymbol
from portfolio.multi_symbol_data_engine import _clamp
from portfolio.paper_portfolio import PaperPortfolio, PortfolioSnapshot
from portfolio.portfolio_allocator import PortfolioAllocator, PortfolioWeight
from reporting.daily_paper_report import DailyPaperReport


DEFAULT_SYMBOLS = ("000001", "000333", "300750", "600519", "601318")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _column_name(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lowered = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def _normalize_series(series: Any) -> list[float]:
    if series is None:
        return []
    if isinstance(series, Mapping):
        series = series.values()
    if not isinstance(series, Sequence) or isinstance(series, (str, bytes)):
        return []
    values: list[float] = []
    for item in series:
        try:
            values.append(float(item))
        except Exception:
            continue
    return values


def _stable_seed(*parts: Any) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


@dataclass(frozen=True)
class PaperSymbolSnapshot:
    symbol: str
    name: str
    sector: str
    close: float
    high: float
    low: float
    volume: float
    historical_close_series: list[float] = field(default_factory=list)
    trend: float = 0.5
    volatility: float = 0.5
    momentum: float = 0.5
    breadth: float = 0.5
    liquidity: float = 0.5
    volume_pressure: float = 0.5
    data_source: str = "MOCK"
    data_status: str = "STALE"
    timestamp: str = field(default_factory=_now_iso)


@dataclass(frozen=True)
class PaperTradingDecision:
    symbol: str
    sector: str
    alpha_score: float
    ranking_score: float
    market_regime: str
    confidence: float
    action: str
    requested_notional: float
    filled_notional: float
    fill_probability: float
    fill_ratio: float
    slippage: float
    fill_status: str
    fill_price: float
    reason: str
    sector_strength: float
    leader_flag: bool


@dataclass(frozen=True)
class PaperTradingRunResult:
    timestamp: str
    symbols: tuple[str, ...]
    source_status: str
    market_state: dict[str, Any]
    capital_state: dict[str, Any]
    ranked_symbols: list[dict[str, Any]]
    weights: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    trade_records: list[dict[str, Any]]
    portfolio_snapshot: dict[str, Any]
    report_path: str
    warnings: list[str] = field(default_factory=list)


class PaperMarketDataFeed:
    """Fetch real A-share market data with cache fallback."""

    def __init__(
        self,
        *,
        lookback_days: int = 60,
        cache_dir: Path | None = None,
        sector_map: Mapping[str, str] | None = None,
    ) -> None:
        self.lookback_days = max(30, int(lookback_days))
        self.cache_dir = cache_dir or (Path("reports") / "cache" / "paper_market")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sector_map = {str(key): str(value) for key, value in (sector_map or {}).items()}

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        code = str(symbol).strip()
        if code.startswith(("sh", "sz")):
            return code
        return ("sh" if code.startswith("6") else "sz") + code

    @staticmethod
    def _sector_for_symbol(symbol: str) -> str:
        code = str(symbol).strip()
        if code.startswith(("300", "688")):
            return "AI Computing"
        if code.startswith("000") or code.startswith("002"):
            return "Domestic Substitution"
        if code.startswith("600") or code.startswith("601"):
            return "Blue Chip"
        return "General"

    def _cache_path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol}.json"

    def _load_cache(self, symbol: str) -> PaperSymbolSnapshot | None:
        path = self._cache_path(symbol)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return PaperSymbolSnapshot(**payload)
        except Exception:
            return None

    def _save_cache(self, snapshot: PaperSymbolSnapshot) -> None:
        try:
            self._cache_path(snapshot.symbol).write_text(
                json.dumps(asdict(snapshot), ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _fetch_frame(self, symbol: str):
        if ak is None:
            raise RuntimeError("akshare is not installed.")
        start_date = (datetime.now() - timedelta(days=self.lookback_days + 30)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        code = str(symbol).strip()
        try:
            return ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        except Exception:
            return ak.stock_zh_a_daily(symbol=self._format_symbol(code))

    def _synthetic_snapshot(self, symbol: str) -> PaperSymbolSnapshot:
        rng = random.Random(_stable_seed(symbol, _today()))
        digest = hashlib.sha256(str(symbol).encode("utf-8")).hexdigest()
        base = 10.0 + (int(digest[:6], 16) % 200) / 10.0
        close = base * (0.95 + 0.10 * rng.random())
        volatility = _clamp(0.12 + 0.55 * rng.random(), 0.0, 1.0)
        high = close * (1.0 + volatility * 0.04)
        low = close * (1.0 - volatility * 0.04)
        history = [close * (0.94 + 0.12 * (i / 19.0)) for i in range(20)]
        trend = _clamp(close / (sum(history) / len(history)) if history else 0.5, 0.0, 1.0)
        momentum = _clamp(0.50 + 0.20 * rng.random() - 0.10 * volatility, 0.0, 1.0)
        breadth = _clamp(0.45 + 0.25 * trend - 0.15 * volatility + 0.10 * momentum, 0.0, 1.0)
        liquidity = _clamp(0.50 + 0.20 * (1.0 - volatility) + 0.10 * momentum, 0.0, 1.0)
        volume_pressure = _clamp(0.45 + 0.25 * trend - 0.20 * volatility, 0.0, 1.0)
        return PaperSymbolSnapshot(
            symbol=symbol,
            name=symbol,
            sector=self.sector_map.get(symbol, self._sector_for_symbol(symbol)),
            close=round(close, 4),
            high=round(high, 4),
            low=round(low, 4),
            volume=round(1_000_000 * (0.6 + rng.random()), 2),
            historical_close_series=[round(value, 4) for value in history],
            trend=round(trend, 4),
            volatility=round(volatility, 4),
            momentum=round(momentum, 4),
            breadth=round(breadth, 4),
            liquidity=round(liquidity, 4),
            volume_pressure=round(volume_pressure, 4),
            data_source="MOCK",
            data_status="STALE",
            timestamp=_now_iso(),
        )

    def _build_snapshot(self, symbol: str, frame: Any, *, data_source: str, data_status: str) -> PaperSymbolSnapshot:
        if frame is None or len(frame) == 0:
            raise ValueError(f"No market data for {symbol}.")

        columns = list(frame.columns)
        close_col = _column_name(columns, ["close", "收盘", "收盘价"])
        high_col = _column_name(columns, ["high", "最高", "最高价"])
        low_col = _column_name(columns, ["low", "最低", "最低价"])
        volume_col = _column_name(columns, ["volume", "成交量", "vol"])
        date_col = _column_name(columns, ["date", "日期", "datetime", "时间"])
        if not close_col or not high_col or not low_col:
            raise ValueError(f"Missing OHLC columns for {symbol}.")

        rows = frame.tail(self.lookback_days).to_dict("records")
        latest = rows[-1]
        previous = rows[-2] if len(rows) >= 2 else latest
        close = float(latest[close_col])
        high = float(latest[high_col])
        low = float(latest[low_col])
        prev_close = float(previous[close_col]) if previous.get(close_col) is not None else close
        series = _normalize_series([row[close_col] for row in rows if row.get(close_col) is not None])
        moving_average = sum(series) / max(len(series), 1)
        trend = _clamp(close / moving_average if moving_average else 0.5, 0.0, 1.0)
        volatility = _clamp((high - low) / close if close else 0.0, 0.0, 1.0)
        momentum = _clamp(close / prev_close if prev_close else 1.0, 0.0, 2.0) / 2.0
        if volume_col and latest.get(volume_col) is not None:
            volume = float(latest[volume_col])
            volume_baseline = sum(
                float(row[volume_col]) for row in rows if row.get(volume_col) is not None
            ) / max(len([row for row in rows if row.get(volume_col) is not None]), 1)
            volume_ratio = volume / max(volume_baseline, 1.0)
        else:
            volume = 0.0
            volume_ratio = 1.0
        breadth = _clamp(0.45 + 0.30 * trend - 0.20 * volatility + 0.10 * momentum, 0.0, 1.0)
        liquidity = _clamp(0.45 + 0.25 * (1.0 - volatility) + 0.15 * momentum + 0.15 * _clamp(volume_ratio, 0.0, 2.0) / 2.0, 0.0, 1.0)
        volume_pressure = _clamp(0.40 + 0.35 * trend - 0.25 * volatility + 0.10 * momentum, 0.0, 1.0)
        timestamp = str(latest[date_col]) if date_col and latest.get(date_col) is not None else _now_iso()
        return PaperSymbolSnapshot(
            symbol=symbol,
            name=symbol,
            sector=self.sector_map.get(symbol, self._sector_for_symbol(symbol)),
            close=round(close, 4),
            high=round(high, 4),
            low=round(low, 4),
            volume=round(volume, 2),
            historical_close_series=[round(value, 4) for value in series[-20:]],
            trend=round(trend, 4),
            volatility=round(volatility, 4),
            momentum=round(momentum, 4),
            breadth=round(breadth, 4),
            liquidity=round(liquidity, 4),
            volume_pressure=round(volume_pressure, 4),
            data_source=data_source,
            data_status=data_status,
            timestamp=timestamp,
        )

    def fetch_symbol(self, symbol: str) -> PaperSymbolSnapshot:
        try:
            frame = self._fetch_frame(symbol)
            snapshot = self._build_snapshot(symbol, frame, data_source="AKSHARE", data_status="LIVE")
            self._save_cache(snapshot)
            return snapshot
        except Exception:
            cached = self._load_cache(symbol)
            if cached is not None:
                return PaperSymbolSnapshot(
                    symbol=cached.symbol,
                    name=cached.name,
                    sector=cached.sector,
                    close=cached.close,
                    high=cached.high,
                    low=cached.low,
                    volume=cached.volume,
                    historical_close_series=list(cached.historical_close_series),
                    trend=cached.trend,
                    volatility=cached.volatility,
                    momentum=cached.momentum,
                    breadth=cached.breadth,
                    liquidity=cached.liquidity,
                    volume_pressure=cached.volume_pressure,
                    data_source=cached.data_source,
                    data_status="STALE",
                    timestamp=cached.timestamp,
                )
            snapshot = self._synthetic_snapshot(symbol)
            self._save_cache(snapshot)
            return snapshot

    def fetch_symbols(self, symbols: Iterable[str]) -> list[PaperSymbolSnapshot]:
        return [self.fetch_symbol(symbol) for symbol in symbols]


class PaperTradingEngine:
    """Execute the V12 paper trading workflow end to end."""

    def __init__(
        self,
        symbols: Iterable[str] | None = None,
        *,
        initial_capital: float = 1_000_000.0,
        sector_map: Mapping[str, str] | None = None,
        report_dir: Path | None = None,
        log_path: Path | None = None,
        feed: PaperMarketDataFeed | None = None,
        portfolio: PaperPortfolio | None = None,
    ) -> None:
        self.symbols = tuple(symbols or DEFAULT_SYMBOLS)
        self.feed = feed or PaperMarketDataFeed(sector_map=sector_map)
        self.portfolio = portfolio or PaperPortfolio(initial_capital=initial_capital)
        self.report_dir = report_dir or (Path("reports") / "paper")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = log_path or (Path("logs") / "paper_trades.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.market_structure_engine = MarketStructureEngine()
        self.capital_flow_engine = CapitalFlowEngine()
        self.narrative_engine = NarrativeEngine()
        self.cycle_engine = CycleEngine()
        self.capital_control_engine = CapitalControlEngine()
        self.decision_engine = DecisionEngine()
        self.alpha_ranker = AlphaRanker()
        self.portfolio_allocator = PortfolioAllocator()
        self.report_writer = DailyPaperReport(self.report_dir)

    def _aggregate_market_data(self, snapshots: Sequence[PaperSymbolSnapshot]) -> dict[str, Any]:
        if not snapshots:
            return {
                "close": 0.0,
                "high": 0.0,
                "low": 0.0,
                "historical_close_series": [],
                "volatility": 0.5,
                "trend": 0.5,
                "momentum": 0.5,
            }

        max_history = max((len(item.historical_close_series) for item in snapshots), default=0)
        aggregate_series: list[float] = []
        for offset in range(1, min(max_history, 20) + 1):
            values = [item.historical_close_series[-offset] for item in snapshots if len(item.historical_close_series) >= offset]
            if values:
                aggregate_series.append(sum(values) / len(values))
        close = mean(item.close for item in snapshots)
        high = mean(item.high for item in snapshots)
        low = mean(item.low for item in snapshots)
        volatility = mean(item.volatility for item in snapshots)
        trend = mean(item.trend for item in snapshots)
        momentum = mean(item.momentum for item in snapshots)
        return {
            "close": round(close, 4),
            "high": round(high, 4),
            "low": round(low, 4),
            "historical_close_series": list(reversed([round(value, 4) for value in aggregate_series])),
            "volatility": round(volatility, 4),
            "trend": round(trend, 4),
            "momentum": round(momentum, 4),
        }

    def _sector_data(self, snapshots: Sequence[PaperSymbolSnapshot]) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
        sector_data: dict[str, float] = {}
        stock_data: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            sector_key = snapshot.sector or "UNKNOWN"
            sector_data[sector_key] = sector_data.get(sector_key, 0.0) + max(snapshot.volume * snapshot.close, 1.0)
            stock_data[snapshot.symbol] = {
                "volume": snapshot.volume,
                "price_change": snapshot.close / max(snapshot.historical_close_series[-2] if len(snapshot.historical_close_series) >= 2 else snapshot.close, 1e-9) - 1.0,
                "is_leader": False,
            }
        if stock_data:
            top_symbol = max(snapshots, key=lambda item: item.close * max(item.volume, 1.0)).symbol
            if top_symbol in stock_data:
                stock_data[top_symbol]["is_leader"] = True
        return sector_data, stock_data

    def _confidence(self, snapshot: PaperSymbolSnapshot, structure: Mapping[str, Any], alpha_score: float) -> float:
        structure_confidence = float(structure.get("structure_strength", 0.5) or 0.5)
        confidence = 0.35 + 0.30 * structure_confidence + 0.20 * (1.0 - snapshot.volatility) + 0.15 * (alpha_score / 100.0)
        return _clamp(confidence, 0.0, 1.0)

    @staticmethod
    def _sector_strength(sector: str, sector_data: Mapping[str, float]) -> float:
        if not sector_data or sector not in sector_data:
            return 0.0
        values = list(sector_data.values())
        top = max(values) if values else 1.0
        if top <= 0.0:
            return 0.0
        return _clamp(float(sector_data[sector]) / top, 0.0, 1.0)

    @staticmethod
    def _risk_appetite(cycle_state: str) -> str:
        if cycle_state == "RISK_ON":
            return "RISING"
        if cycle_state == "RISK_OFF":
            return "FALLING"
        return "SELECTIVE"

    @staticmethod
    def _decision_size(action: str, base_size: float, position_multiplier: float, leverage: float) -> float:
        if action in {"HOLD", "OBSERVE"}:
            return 0.0
        size = float(base_size) * max(0.5, position_multiplier) * max(0.5, leverage)
        return _clamp(size, 0.0, 0.15)

    @staticmethod
    def _execution_roll(symbol: str, timestamp: str) -> float:
        seed = _stable_seed(symbol, timestamp)
        rng = random.Random(seed)
        return rng.random()

    def _simulate_execution(
        self,
        *,
        timestamp: str,
        snapshot: PaperSymbolSnapshot,
        decision: Mapping[str, Any],
        capital_state: Mapping[str, Any],
    ) -> dict[str, Any]:
        action = str(decision.get("action", "OBSERVE")).upper()
        base_size = float(decision.get("size", 0.0) or 0.0)
        requested_notional = self.portfolio.portfolio_value() * self._decision_size(
            action,
            base_size,
            float(capital_state.get("position_multiplier", 1.0) or 1.0),
            float(capital_state.get("leverage_adjustment", 1.0) or 1.0),
        )
        if action in {"REDUCE", "EXIT"}:
            requested_notional = max(requested_notional, self.portfolio.position_value(snapshot.symbol) * max(base_size, 0.05))
        fill_probability = max(0.5, 1.0 - snapshot.volatility)
        fill_ratio = 1.0 if self._execution_roll(snapshot.symbol, timestamp) <= fill_probability else 0.5
        slippage = snapshot.volatility * 0.01
        if action in {"REDUCE", "EXIT"}:
            fill_price = snapshot.close * (1.0 - slippage)
        else:
            fill_price = snapshot.close * (1.0 + slippage)
        if action in {"HOLD", "OBSERVE"}:
            fill_ratio = 0.0
            requested_notional = 0.0
        fill_status = "FILLED" if fill_ratio >= 1.0 else "PARTIAL_FILL" if fill_ratio > 0.0 else "NO_ACTION"
        trade = self.portfolio.apply_trade(
            timestamp=timestamp,
            symbol=snapshot.symbol,
            action=action,
            requested_notional=requested_notional,
            execution_price=fill_price,
            fill_ratio=fill_ratio,
            fill_probability=fill_probability,
            slippage=slippage,
            reason=str(decision.get("reason", "")),
            status=fill_status,
        )
        trade_record = {
            "timestamp": timestamp,
            "symbol": snapshot.symbol,
            "sector": snapshot.sector,
            "action": action,
            "requested_notional": round(requested_notional, 4),
            "filled_notional": trade.filled_notional,
            "fill_probability": round(fill_probability, 4),
            "fill_ratio": round(fill_ratio, 4),
            "slippage": round(slippage, 6),
            "fill_price": round(fill_price, 4),
            "status": trade.status,
            "reason": trade.reason,
            "data_source": snapshot.data_source,
            "data_status": snapshot.data_status,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trade_record, ensure_ascii=False, sort_keys=True) + "\n")
        return trade_record

    def run_once(self) -> PaperTradingRunResult:
        snapshots = self.feed.fetch_symbols(self.symbols)
        source_status = "LIVE" if all(item.data_status == "LIVE" for item in snapshots) else "STALE"
        market_data = self._aggregate_market_data(snapshots)
        market_structure = self.market_structure_engine.analyze_market_structure(market_data)
        ranked = self.alpha_ranker.rank(snapshots)
        weights = self.portfolio_allocator.allocate(ranked)
        weight_by_symbol = {item.symbol: item.weight for item in weights}
        sector_data, stock_data = self._sector_data(snapshots)
        capital_flow = self.capital_flow_engine.analyze_capital_flow(
            {"sector_data": sector_data, "stock_data": stock_data}
        )
        narrative = self.narrative_engine.extract_market_theme(
            {
                "sectors": list(sector_data.keys()),
                "flow_strength": capital_flow["flow_strength"],
                "sector_flows": sector_data,
                "news_keywords": [snapshot.sector for snapshot in snapshots if snapshot.sector],
            }
        )
        cycle = self.cycle_engine.build_cycle_state(
            {
                "volatility": market_data["volatility"],
                "flow_strength": capital_flow["flow_strength"],
                "narrative_strength": narrative["narrative_strength"],
                "fear_index": market_data["volatility"] * 100.0,
            }
        )
        capital_state = self.capital_control_engine.build_capital_control(
            {
                "regime": market_structure["regime"],
                "flow_strength": capital_flow["flow_strength"],
                "narrative_strength": narrative["narrative_strength"],
                "cycle_state": cycle["unified_cycle_state"],
            },
            {
                "current_exposure": self.portfolio.current_exposure(),
                "max_drawdown": self.portfolio.drawdown(),
            },
        )

        ranked_by_symbol = {item.symbol: item for item in ranked}
        decisions: list[dict[str, Any]] = []
        trade_records: list[dict[str, Any]] = []
        for snapshot in snapshots:
            ranked_item = ranked_by_symbol.get(snapshot.symbol)
            if ranked_item is None:
                continue
            sector_strength = self._sector_strength(snapshot.sector, sector_data)
            leader_flag = bool(ranked_item.rank == 1 or ranked_item.alpha_score >= 80.0)
            symbol_structure = self.market_structure_engine.analyze_market_structure(
                {
                    "close": snapshot.close,
                    "high": snapshot.high,
                    "low": snapshot.low,
                    "historical_close_series": snapshot.historical_close_series,
                }
            )
            confidence = self._confidence(snapshot, symbol_structure, ranked_item.alpha_score)
            decision = self.decision_engine.decide(
                symbol=snapshot.symbol,
                score=ranked_item.alpha_score,
                regime=market_structure["regime"],
                confidence=confidence,
                context={
                    "sector": snapshot.sector,
                    "sector_strength": sector_strength,
                    "sector_leader_flag": leader_flag,
                    "sector_rank": ranked_item.rank,
                    "theme": snapshot.sector,
                    "theme_tags": [snapshot.sector, "PaperTrading", snapshot.symbol],
                    "confidence_sensitivity": capital_state["leverage_adjustment"],
                    "confidence_bias": 0.0,
                    "combined_cycle_state": cycle["unified_cycle_state"],
                    "macro_cycle": cycle["unified_cycle_state"],
                    "cycle_state": cycle["unified_cycle_state"],
                    "risk_appetite": self._risk_appetite(cycle["unified_cycle_state"]),
                    "liquidity_cycle": cycle["liquidity_cycle"],
                    "sentiment_cycle": cycle["sentiment_cycle"],
                    "industry_cycle": cycle["industry_cycle"],
                    "capital_flow_score": capital_flow["flow_strength"],
                    "capital_flow_direction": capital_flow["rotation_signal"],
                    "leader_concentration": capital_flow["leader_concentration"],
                    "rotation_path": capital_flow["rotation_signal"],
                    "chain_strength": "PARTIAL" if symbol_structure["regime"] != "BEAR" else "NONE",
                    "bottleneck_node": "Liquidity" if capital_flow["flow_strength"] < 0.5 else "None",
                    "causal_chain": [
                        "Price Trend",
                        "Capital Flow",
                        "Narrative",
                        "Cycle",
                    ],
                },
            )
            trade_record = self._simulate_execution(
                timestamp=snapshot.timestamp,
                snapshot=snapshot,
                decision=decision,
                capital_state=capital_state,
            )
            trade_records.append(trade_record)
            decisions.append(
                {
                    "symbol": snapshot.symbol,
                    "name": snapshot.name,
                    "sector": snapshot.sector,
                    "alpha_score": round(ranked_item.alpha_score, 4),
                    "ranking_score": round(ranked_item.raw_score, 4),
                    "market_regime": market_structure["regime"],
                    "confidence": round(confidence, 4),
                    "action": decision["action"],
                    "reason": decision["reason"],
                    "sector_strength": round(sector_strength, 4),
                    "leader_flag": leader_flag,
                    "weight": round(weight_by_symbol.get(snapshot.symbol, 0.0), 6),
                    "data_source": snapshot.data_source,
                    "data_status": snapshot.data_status,
                }
            )

        portfolio_snapshot = self.portfolio.mark_to_market(
            {snapshot.symbol: snapshot.close for snapshot in snapshots},
            timestamp=max((snapshot.timestamp for snapshot in snapshots), default=_now_iso()),
            status=source_status,
        )
        report_payload = {
            "timestamp": portfolio_snapshot.timestamp,
            "source_status": source_status,
            "market_state": {
                "structure": market_structure,
                "capital_flow": capital_flow,
                "narrative": narrative,
                "cycle": cycle,
            },
            "capital_state": capital_state,
            "ranked_symbols": [asdict(item) for item in ranked],
            "weights": [asdict(item) for item in weights],
            "decisions": decisions,
            "trade_records": trade_records,
            "portfolio_snapshot": asdict(portfolio_snapshot),
            "symbols": list(self.symbols),
            "warnings": ["MARKET_DATA_STALE"] if source_status == "STALE" else [],
        }
        report_path = self.report_writer.write(report_payload)
        return PaperTradingRunResult(
            timestamp=portfolio_snapshot.timestamp,
            symbols=self.symbols,
            source_status=source_status,
            market_state=report_payload["market_state"],
            capital_state=capital_state,
            ranked_symbols=[asdict(item) for item in ranked],
            weights=[asdict(item) for item in weights],
            decisions=decisions,
            trade_records=trade_records,
            portfolio_snapshot=asdict(portfolio_snapshot),
            report_path=str(report_path),
            warnings=report_payload["warnings"],
        )

    def run_loop(self, iterations: int | None = None, interval_seconds: float = 60.0) -> None:
        cycle = 0
        while iterations is None or cycle < iterations:
            result = self.run_once()
            print(result.report_path)
            cycle += 1
            if iterations is None or cycle < iterations:
                time.sleep(max(1.0, interval_seconds))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V12 paper trading engine")
    parser.add_argument("--symbols", type=str, default=os.environ.get("PAPER_SYMBOLS", ",".join(DEFAULT_SYMBOLS)))
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--loop", action="store_true")
    return parser


def _parse_symbols(text: str) -> tuple[str, ...]:
    symbols: list[str] = []
    for item in str(text or "").split(","):
        candidate = item.strip()
        if not candidate:
            continue
        if candidate.isdigit() and len(candidate) < 6:
            candidate = candidate.zfill(6)
        symbols.append(candidate)
    return tuple(symbols or DEFAULT_SYMBOLS)


def main() -> int:
    args = build_argument_parser().parse_args()
    engine = PaperTradingEngine(_parse_symbols(args.symbols))
    if args.loop or args.iterations != 1:
        engine.run_loop(iterations=args.iterations if args.iterations > 0 else None, interval_seconds=args.interval)
    else:
        result = engine.run_once()
        print(result.report_path)
        print(json.dumps(result.portfolio_snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
