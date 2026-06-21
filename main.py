"""V12 production single-file trading decision pipeline.

This module is intentionally self-contained. It uses only the Python standard
library for core execution and keeps the runtime deterministic when mock market
data is used.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Iterable, Protocol

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ak = None

from portfolio.alpha_ranker import AlphaRanker, RankedSymbol
from portfolio.multi_symbol_data_engine import MultiSymbolDataEngine, SymbolSnapshot
from portfolio.portfolio_allocator import PortfolioAllocator, PortfolioWeight


SEED = int(os.environ.get("V12_SEED", "42"))
DEFAULT_INTERVAL_SECONDS = float(os.environ.get("V12_INTERVAL_SECONDS", "2.0"))
DEFAULT_ITERATIONS = int(os.environ.get("V12_ITERATIONS", "1"))
DEFAULT_SYMBOLS = (
    "000001",
    "000333",
    "300750",
    "600519",
    "601318",
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class MarketData:
    iteration: int
    trend: float
    volatility: float
    momentum: float
    breadth: float
    liquidity: float
    volume_pressure: float
    data_source: str
    data_status: str
    timestamp: str


@dataclass(frozen=True)
class MarketState:
    regime: str
    trend: float
    volatility: float
    momentum: float
    volatility_state: str
    structure_strength: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class CapitalState:
    position_multiplier: float
    risk_budget: float
    estimated_exposure: float
    normalized_exposure: float
    exposure_warning: bool
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Decision:
    action: str
    size: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class FinalDecision:
    action: str
    size: float
    allowed: bool
    reason: str


@dataclass
class CycleResult:
    iteration: int
    timestamp: str
    market_data: MarketData
    market_state: MarketState
    capital_state: CapitalState
    decision: Decision
    issues: list[Issue]
    final_decision: FinalDecision


@dataclass(frozen=True)
class PortfolioDecisionRecord:
    symbol: str
    rank: int
    alpha_score: float
    portfolio_weight: float
    market_state: MarketState
    capital_state: CapitalState
    decision: Decision
    issues: tuple[Issue, ...]
    final_decision: FinalDecision
    data_source: str
    data_status: str


@dataclass(frozen=True)
class PortfolioRunResult:
    timestamp: str
    universe: tuple[str, ...]
    symbol_snapshots: tuple[SymbolSnapshot, ...]
    ranked_symbols: tuple[RankedSymbol, ...]
    weights: tuple[PortfolioWeight, ...]
    overall_market_data: MarketData
    overall_market_state: MarketState
    capital_state: CapitalState
    decisions: tuple[PortfolioDecisionRecord, ...]


class MarketFeed(Protocol):
    def sample(self, iteration: int) -> MarketData:
        ...


class MockMarketFeed:
    """Deterministic mock market feed."""

    def __init__(self, seed: int = SEED) -> None:
        self.seed = seed

    def sample(self, iteration: int) -> MarketData:
        rng = random.Random(self.seed + iteration * 7919)
        base_wave = math.sin((iteration + 1) / 3.7)
        trend = _clamp(0.5 + 0.22 * base_wave + rng.uniform(-0.08, 0.08), 0.0, 1.0)
        volatility = _clamp(0.42 + 0.25 * math.cos((iteration + 2) / 4.1) + rng.uniform(-0.08, 0.08), 0.0, 1.0)
        momentum = _clamp(0.45 + 0.30 * base_wave + 0.20 * trend - 0.18 * volatility + rng.uniform(-0.05, 0.05), 0.0, 1.0)
        breadth = _clamp(0.40 + 0.25 * math.sin((iteration + 3) / 5.3) + rng.uniform(-0.07, 0.07), 0.0, 1.0)
        liquidity = _clamp(0.50 + 0.18 * math.cos((iteration + 1) / 6.1) + rng.uniform(-0.06, 0.06), 0.0, 1.0)
        volume_pressure = _clamp(0.45 + 0.25 * trend - 0.20 * volatility + rng.uniform(-0.05, 0.05), 0.0, 1.0)
        return MarketData(
            iteration=iteration,
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


class AKShareMarketFeed:
    """Real A-share market feed with cache fallback."""

    def __init__(self, symbol: str = "sh000300", cache_path: Path | None = None) -> None:
        self.symbol = symbol
        self.cache_path = cache_path or (Path("reports") / "cache" / "v12_akshare_csi300_cache.json")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._mock_fallback = MockMarketFeed()

    def _load_cached_market_data(self) -> MarketData | None:
        if not self.cache_path.exists():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return MarketData(**payload)
        except Exception:
            return None

    def _save_cached_market_data(self, market_data: MarketData) -> None:
        try:
            self.cache_path.write_text(json.dumps(asdict(market_data), ensure_ascii=False, sort_keys=True), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _column_name(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
        lowered = {str(column).strip().lower(): str(column) for column in columns}
        for candidate in candidates:
            if candidate.lower() in lowered:
                return lowered[candidate.lower()]
        return None

    def _build_from_dataframe(self, frame: object, iteration: int) -> MarketData:
        if not hasattr(frame, "tail") or not hasattr(frame, "__len__"):
            raise ValueError("AKShare data is not tabular.")

        if len(frame) == 0:
            raise ValueError("AKShare returned empty data.")

        columns = list(getattr(frame, "columns", []))
        close_col = self._column_name(columns, ["close", "收盘", "收盘价"])
        high_col = self._column_name(columns, ["high", "最高", "最高价"])
        low_col = self._column_name(columns, ["low", "最低", "最低价"])
        date_col = self._column_name(columns, ["date", "日期", "datetime", "时间"])
        volume_col = self._column_name(columns, ["volume", "成交量", "vol"])

        if not close_col or not high_col or not low_col:
            raise ValueError("Required OHLC columns are missing from AKShare data.")

        window = frame.tail(20)
        rows = window.to_dict("records")
        latest = rows[-1]
        previous = rows[-2] if len(rows) >= 2 else latest

        close = float(latest[close_col])
        high = float(latest[high_col])
        low = float(latest[low_col])
        prev_close = float(previous[close_col]) if previous.get(close_col) is not None else close

        moving_average = sum(float(row[close_col]) for row in rows) / max(len(rows), 1)
        trend_ratio = close / moving_average if moving_average else 1.0
        volatility_raw = (high - low) / close if close else 0.0
        momentum_raw = close / prev_close if prev_close else 1.0
        volume_value = float(latest[volume_col]) if volume_col and latest.get(volume_col) is not None else float(len(rows))
        if volume_col:
            volume_samples = [float(row[volume_col]) for row in rows if row.get(volume_col) is not None]
            volume_baseline = mean(volume_samples) if volume_samples else volume_value
        else:
            volume_baseline = volume_value

        trend = _clamp((trend_ratio - 0.95) / 0.10, 0.0, 1.0)
        volatility = _clamp(volatility_raw / 0.05, 0.0, 1.0)
        momentum = _clamp((momentum_raw - 0.99) / 0.03, 0.0, 1.0)
        breadth = _clamp(0.45 + 0.35 * trend - 0.25 * volatility + 0.10 * momentum, 0.0, 1.0)
        liquidity = _clamp(0.50 + 0.25 * (1.0 - volatility) + 0.15 * momentum + 0.10 * _clamp(volume_value / max(volume_baseline, 1.0), 0.0, 2.0) / 2.0, 0.0, 1.0)
        volume_pressure = _clamp(0.40 + 0.40 * trend - 0.30 * volatility + 0.10 * momentum, 0.0, 1.0)

        if date_col and latest.get(date_col) is not None:
            timestamp = str(latest[date_col])
        else:
            timestamp = _now_iso()

        return MarketData(
            iteration=iteration,
            trend=round(trend, 4),
            volatility=round(volatility, 4),
            momentum=round(momentum, 4),
            breadth=round(breadth, 4),
            liquidity=round(liquidity, 4),
            volume_pressure=round(volume_pressure, 4),
            data_source="AKSHARE",
            data_status="LIVE",
            timestamp=timestamp,
        )

    def _fetch_real_market_data(self, iteration: int) -> MarketData:
        if ak is None:
            raise RuntimeError("akshare is not installed.")
        frame = ak.stock_zh_index_daily(symbol=self.symbol)
        market_data = self._build_from_dataframe(frame, iteration)
        self._save_cached_market_data(market_data)
        return market_data

    def sample(self, iteration: int) -> MarketData:
        try:
            return self._fetch_real_market_data(iteration)
        except Exception:
            cached = self._load_cached_market_data()
            if cached is not None:
                return MarketData(
                    iteration=iteration,
                    trend=cached.trend,
                    volatility=cached.volatility,
                    momentum=cached.momentum,
                    breadth=cached.breadth,
                    liquidity=cached.liquidity,
                    volume_pressure=cached.volume_pressure,
                    data_source=cached.data_source if cached.data_source else "AKSHARE",
                    data_status="STALE",
                    timestamp=cached.timestamp,
                )
            fallback = self._mock_fallback.sample(iteration)
            return MarketData(
                iteration=iteration,
                trend=fallback.trend,
                volatility=fallback.volatility,
                momentum=fallback.momentum,
                breadth=fallback.breadth,
                liquidity=fallback.liquidity,
                volume_pressure=fallback.volume_pressure,
                data_source="MOCK",
                data_status="STALE",
                timestamp=fallback.timestamp,
            )


class MarketBrain:
    """V12.1 to V12.4 style market understanding in compact form."""

    def analyze(self, data: MarketData) -> MarketState:
        if data.volatility >= 0.72 and data.trend <= 0.45:
            regime = "BEAR"
            reason = "Low trend and elevated volatility point to defensive conditions."
        elif data.volatility <= 0.38 and data.trend >= 0.58:
            regime = "BULL"
            reason = "Trend is constructive while volatility remains contained."
        else:
            regime = "RANGE"
            reason = "Signals are mixed, indicating range-bound conditions."

        volatility_state = "LOW" if data.volatility < 0.35 else "MEDIUM" if data.volatility < 0.7 else "HIGH"
        structure_strength = _clamp(
            0.55 * abs(data.trend - 0.5) * 2.0 + 0.30 * (1.0 - data.volatility) + 0.15 * data.breadth,
            0.0,
            1.0,
        )
        confidence = _clamp(0.45 + 0.35 * structure_strength + 0.20 * (1.0 - data.volatility), 0.0, 1.0)
        return MarketState(
            regime=regime,
            trend=round(data.trend, 4),
            volatility=round(data.volatility, 4),
            momentum=round(data.momentum, 4),
            volatility_state=volatility_state,
            structure_strength=round(structure_strength, 4),
            confidence=round(confidence, 4),
            reason=reason,
        )


class CapitalController:
    """Capital control layer with exposure normalization."""

    def adjust(self, market_state: MarketState) -> CapitalState:
        if market_state.regime == "BULL":
            base_multiplier = 1.0 + 0.18 * market_state.structure_strength + 0.08 * market_state.trend
            base_risk_budget = 0.22 + 0.08 * market_state.structure_strength
        elif market_state.regime == "BEAR":
            base_multiplier = 0.45 + 0.20 * (1.0 - market_state.volatility) + 0.10 * market_state.structure_strength
            base_risk_budget = 0.08 + 0.05 * (1.0 - market_state.volatility)
        else:
            base_multiplier = 0.72 + 0.12 * market_state.structure_strength + 0.06 * market_state.trend
            base_risk_budget = 0.14 + 0.06 * market_state.structure_strength

        position_multiplier = _clamp(base_multiplier, 0.15, 1.25)
        risk_budget = _clamp(base_risk_budget, 0.05, 0.35)
        estimated_exposure = _clamp(0.18 + 0.32 * position_multiplier + 0.12 * market_state.trend - 0.10 * market_state.volatility, 0.0, 0.75)
        normalized_exposure = _clamp(estimated_exposure, 0.0, 0.35)
        exposure_warning = estimated_exposure > 0.35

        notes: list[str] = []
        if exposure_warning:
            notes.append("Exposure normalized because projected exposure exceeds the safety ceiling.")
        if market_state.regime == "BEAR":
            notes.append("Bearish regime keeps allocation conservative.")
        if market_state.volatility_state == "HIGH":
            notes.append("High volatility lowers the permitted risk budget.")

        return CapitalState(
            position_multiplier=round(position_multiplier, 4),
            risk_budget=round(risk_budget, 4),
            estimated_exposure=round(estimated_exposure, 4),
            normalized_exposure=round(normalized_exposure, 4),
            exposure_warning=exposure_warning,
            notes=tuple(notes),
        )


class DecisionEngine:
    """Generates a simple BUY / HOLD / REDUCE decision."""

    def decide(self, market_state: MarketState, capital_state: CapitalState) -> Decision:
        if market_state.regime == "BEAR":
            action = "REDUCE" if market_state.volatility >= 0.55 else "HOLD"
            reason = "Bear regime keeps the system defensive."
        elif market_state.regime == "BULL" and market_state.trend >= 0.58 and market_state.volatility <= 0.45:
            action = "BUY"
            reason = "Bull regime with acceptable volatility supports participation."
        elif market_state.trend >= 0.55 and market_state.momentum >= 0.50:
            action = "BUY" if market_state.volatility <= 0.60 else "HOLD"
            reason = "Trend and momentum are constructive, but volatility determines aggressiveness."
        elif market_state.trend < 0.42 or market_state.volatility >= 0.70:
            action = "REDUCE"
            reason = "Weak trend or elevated volatility argues for risk reduction."
        else:
            action = "HOLD"
            reason = "Signals are mixed, so the base posture is neutral."

        if action == "BUY":
            base_size = 0.10
        elif action == "REDUCE":
            base_size = 0.06
        else:
            base_size = 0.00

        if action == "BUY":
            size = base_size * capital_state.position_multiplier
        elif action == "REDUCE":
            size = base_size * (2.0 - capital_state.position_multiplier)
        else:
            size = 0.0

        size = _clamp(size, 0.0, 0.15)
        confidence = _clamp(0.35 + 0.35 * market_state.confidence + 0.30 * capital_state.risk_budget, 0.0, 1.0)
        return Decision(action=action, size=round(size, 4), confidence=round(confidence, 4), reason=reason)


class Diagnoser:
    """Detects anomalies and unstable conditions."""

    def diagnose(self, market_state: MarketState, capital_state: CapitalState, decision: Decision) -> list[Issue]:
        issues: list[Issue] = []

        if market_state.volatility >= 0.75:
            issues.append(Issue("HIGH_VOLATILITY", "HIGH", "Volatility is above the comfort zone."))
        elif market_state.volatility >= 0.60:
            issues.append(Issue("ELEVATED_VOLATILITY", "MEDIUM", "Volatility is elevated and deserves caution."))

        if capital_state.exposure_warning:
            issues.append(
                Issue(
                    "OVER_EXPOSURE",
                    "HIGH",
                    f"Projected exposure {_fmt_pct(capital_state.estimated_exposure)} exceeds the normalization threshold.",
                )
            )

        if market_state.regime == "BEAR":
            issues.append(Issue("BEAR_REGIME", "MEDIUM", "Bear regime keeps the system in defensive mode."))

        if market_state.confidence < 0.55:
            issues.append(Issue("LOW_STRUCTURE_CONFIDENCE", "MEDIUM", "Market structure confidence is not robust."))

        if decision.action == "BUY" and market_state.volatility >= 0.60:
            issues.append(Issue("BUY_IN_HIGH_VOL", "HIGH", "Buy decision is being made under high volatility."))

        return issues


class SafetyGuard:
    """Final override layer that enforces trading safety."""

    def apply(
        self,
        market_state: MarketState,
        capital_state: CapitalState,
        decision: Decision,
        issues: Iterable[Issue],
    ) -> FinalDecision:
        issue_codes = {issue.code for issue in issues}
        final_action = decision.action
        final_size = decision.size
        allowed = True
        reasons: list[str] = [decision.reason]

        if "HIGH_VOLATILITY" in issue_codes:
            final_action = "REDUCE" if decision.action == "BUY" else "HOLD"
            final_size = min(final_size, 0.04)
            reasons.append("Safety layer reduced exposure because volatility is high.")

        if "OVER_EXPOSURE" in issue_codes:
            final_action = "REDUCE" if final_action == "BUY" else final_action
            final_size = min(final_size, 0.05)
            reasons.append("Exposure was normalized by the safety layer.")

        if market_state.regime == "BEAR" and final_action == "BUY":
            final_action = "HOLD"
            final_size = 0.0
            reasons.append("Bear regime cannot pass through as a buy decision.")

        if market_state.volatility >= 0.90:
            final_action = "HOLD"
            final_size = 0.0
            allowed = False
            reasons.append("Extreme volatility triggered a hard safety stop.")

        final_size = _clamp(final_size, 0.0, 0.15)
        return FinalDecision(
            action=final_action,
            size=round(final_size, 4),
            allowed=allowed,
            reason=" ".join(reasons),
        )


class PipelineLogger:
    """Records each pipeline step to a log file."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, payload: dict[str, object]) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _print_section(title: str) -> None:
    print(title)


def _print_key_value(key: str, value: object) -> None:
    print(f"{key}: {value}")


def _parse_symbols(symbols_text: str | None) -> tuple[str, ...]:
    if not symbols_text:
        return DEFAULT_SYMBOLS
    symbols = tuple(
        symbol.strip()
        for symbol in symbols_text.split(",")
        if symbol.strip()
    )
    return symbols or DEFAULT_SYMBOLS


def _market_data_from_snapshot(snapshot: SymbolSnapshot, iteration: int = 0) -> MarketData:
    return MarketData(
        iteration=iteration,
        trend=snapshot.trend,
        volatility=snapshot.volatility,
        momentum=snapshot.momentum,
        breadth=snapshot.breadth,
        liquidity=snapshot.liquidity,
        volume_pressure=snapshot.volume_pressure,
        data_source=snapshot.data_source,
        data_status=snapshot.data_status,
        timestamp=snapshot.timestamp,
    )


def _aggregate_market_data(snapshots: Iterable[SymbolSnapshot]) -> MarketData:
    items = list(snapshots)
    if not items:
        return MarketData(
            iteration=0,
            trend=0.5,
            volatility=0.5,
            momentum=0.5,
            breadth=0.5,
            liquidity=0.5,
            volume_pressure=0.5,
            data_source="MOCK",
            data_status="STALE",
            timestamp=_now_iso(),
        )

    trend = mean(item.trend for item in items)
    volatility = mean(item.volatility for item in items)
    momentum = mean(item.momentum for item in items)
    breadth = mean(item.breadth for item in items)
    liquidity = mean(item.liquidity for item in items)
    volume_pressure = mean(item.volume_pressure for item in items)
    data_source = "+".join(sorted({item.data_source for item in items}))
    data_status = "LIVE" if all(item.data_status == "LIVE" for item in items) else "STALE"
    timestamp = max(item.timestamp for item in items)
    return MarketData(
        iteration=0,
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


def _build_symbol_capital_state(
    overall_capital_state: CapitalState,
    symbol_weight: float,
    symbol_market_state: MarketState,
) -> CapitalState:
    position_multiplier = _clamp(
        overall_capital_state.position_multiplier * (0.82 + 0.68 * symbol_weight),
        0.15,
        1.25,
    )
    risk_budget = _clamp(
        overall_capital_state.risk_budget * (0.90 + 0.10 * (1.0 - symbol_weight)),
        0.05,
        0.35,
    )
    estimated_exposure = _clamp(symbol_weight * position_multiplier * (0.90 + 0.10 * symbol_market_state.structure_strength), 0.0, 0.75)
    normalized_exposure = _clamp(estimated_exposure, 0.0, 0.35)
    exposure_warning = estimated_exposure > 0.35
    notes = list(overall_capital_state.notes)
    if exposure_warning:
        notes.append("Portfolio weight normalization flagged a concentration risk.")
    return CapitalState(
        position_multiplier=round(position_multiplier, 4),
        risk_budget=round(risk_budget, 4),
        estimated_exposure=round(estimated_exposure, 4),
        normalized_exposure=round(normalized_exposure, 4),
        exposure_warning=exposure_warning,
        notes=tuple(notes),
    )


def _run_cycle(
    iteration: int,
    feed: MarketFeed,
    brain: MarketBrain,
    controller: CapitalController,
    decision_engine: DecisionEngine,
    diagnoser: Diagnoser,
    safety_guard: SafetyGuard,
    logger: PipelineLogger,
) -> CycleResult:
    market_data = feed.sample(iteration)
    market_state = brain.analyze(market_data)
    capital_state = controller.adjust(market_state)
    decision = decision_engine.decide(market_state, capital_state)
    issues = diagnoser.diagnose(market_state, capital_state, decision)
    final_decision = safety_guard.apply(market_state, capital_state, decision, issues)

    logger.record(
        {
            "iteration": iteration,
            "timestamp": market_data.timestamp,
            "market_data": asdict(market_data),
            "market_state": asdict(market_state),
            "capital_state": asdict(capital_state),
            "decision": asdict(decision),
            "issues": [asdict(item) for item in issues],
            "final_decision": asdict(final_decision),
        }
    )

    _print_section("Market State:")
    _print_key_value("regime", market_state.regime)
    _print_key_value("trend", f"{market_state.trend:.4f}")
    _print_key_value("volatility", f"{market_state.volatility:.4f}")
    _print_key_value("momentum", f"{market_state.momentum:.4f}")
    _print_key_value("volatility_state", market_state.volatility_state)
    _print_key_value("structure_strength", f"{market_state.structure_strength:.4f}")
    _print_key_value("confidence", f"{market_state.confidence:.4f}")
    _print_key_value("data_source", market_data.data_source)
    _print_key_value("data_status", market_data.data_status)
    _print_key_value("reason", market_state.reason)

    _print_section("Capital State:")
    _print_key_value("position_multiplier", f"{capital_state.position_multiplier:.4f}")
    _print_key_value("risk_budget", f"{capital_state.risk_budget:.4f}")
    _print_key_value("estimated_exposure", f"{capital_state.estimated_exposure:.4f}")
    _print_key_value("normalized_exposure", f"{capital_state.normalized_exposure:.4f}")
    _print_key_value("exposure_warning", capital_state.exposure_warning)
    if capital_state.notes:
        _print_key_value("notes", "; ".join(capital_state.notes))

    _print_section("Decision:")
    _print_key_value("action", decision.action)
    _print_key_value("size", f"{decision.size:.4f}")
    _print_key_value("confidence", f"{decision.confidence:.4f}")
    _print_key_value("reason", decision.reason)

    _print_section("Issues:")
    if issues:
        for issue in issues:
            print(f"- [{issue.severity}] {issue.code}: {issue.message}")
    else:
        print("- None")

    _print_section("Final Decision:")
    _print_key_value("adjusted_action", final_decision.action)
    _print_key_value("adjusted_size", f"{final_decision.size:.4f}")
    _print_key_value("allowed", final_decision.allowed)
    _print_key_value("reason", final_decision.reason)
    print()

    return CycleResult(
        iteration=iteration,
        timestamp=market_data.timestamp,
        market_data=market_data,
        market_state=market_state,
        capital_state=capital_state,
        decision=decision,
        issues=issues,
        final_decision=final_decision,
    )


def _print_portfolio_summary(result: PortfolioRunResult) -> None:
    _print_section("Portfolio Universe:")
    _print_key_value("symbols", ", ".join(result.universe))
    _print_key_value("data_status", result.overall_market_data.data_status)
    _print_key_value("data_source", result.overall_market_data.data_source)

    _print_section("Market State:")
    _print_key_value("regime", result.overall_market_state.regime)
    _print_key_value("trend", f"{result.overall_market_state.trend:.4f}")
    _print_key_value("volatility", f"{result.overall_market_state.volatility:.4f}")
    _print_key_value("momentum", f"{result.overall_market_state.momentum:.4f}")
    _print_key_value("volatility_state", result.overall_market_state.volatility_state)
    _print_key_value("structure_strength", f"{result.overall_market_state.structure_strength:.4f}")
    _print_key_value("confidence", f"{result.overall_market_state.confidence:.4f}")
    _print_key_value("reason", result.overall_market_state.reason)

    _print_section("Capital State:")
    _print_key_value("position_multiplier", f"{result.capital_state.position_multiplier:.4f}")
    _print_key_value("risk_budget", f"{result.capital_state.risk_budget:.4f}")
    _print_key_value("estimated_exposure", f"{result.capital_state.estimated_exposure:.4f}")
    _print_key_value("normalized_exposure", f"{result.capital_state.normalized_exposure:.4f}")
    _print_key_value("exposure_warning", result.capital_state.exposure_warning)

    _print_section("Ranked Symbols:")
    for item in result.ranked_symbols:
        weight = next((entry.weight for entry in result.weights if entry.symbol == item.symbol), 0.0)
        print(
            f"{item.rank}. {item.symbol}"
            f"\talpha={item.alpha_score:.2f}"
            f"\traw={item.raw_score:.2f}"
            f"\tweight={weight:.4f}"
            f"\tdata={item.data_source}"
            f"\tstatus={item.data_status}"
        )

    _print_section("Per-Symbol Decisions:")
    for item in result.decisions:
        print(
            f"{item.rank}. {item.symbol}"
            f"\talpha={item.alpha_score:.2f}"
            f"\tweight={item.portfolio_weight:.4f}"
            f"\tregime={item.market_state.regime}"
            f"\taction={item.decision.action}"
            f"\tfinal={item.final_decision.action}"
            f"\tsize={item.final_decision.size:.4f}"
            f"\tdata={item.data_status}"
        )
        if item.issues:
            issue_text = "; ".join(f"{issue.code}:{issue.severity}" for issue in item.issues)
            print(f"    issues={issue_text}")

    print()


def _run_portfolio_cycle(
    iteration: int,
    symbols: Iterable[str],
    data_engine: MultiSymbolDataEngine,
    brain: MarketBrain,
    controller: CapitalController,
    decision_engine: DecisionEngine,
    diagnoser: Diagnoser,
    safety_guard: SafetyGuard,
    logger: PipelineLogger,
    ranker: AlphaRanker,
    allocator: PortfolioAllocator,
) -> PortfolioRunResult:
    symbol_snapshots = tuple(data_engine.fetch_symbols(symbols))
    overall_market_data = _aggregate_market_data(symbol_snapshots)
    overall_market_state = brain.analyze(overall_market_data)
    capital_state = controller.adjust(overall_market_state)
    ranked = tuple(ranker.rank(symbol_snapshots))
    weights = tuple(allocator.allocate(ranked))
    weight_by_symbol = {item.symbol: item.weight for item in weights}
    symbol_snapshot_by_symbol = {item.symbol: item for item in symbol_snapshots}

    decisions: list[PortfolioDecisionRecord] = []
    for ranked_item in ranked:
        snapshot = symbol_snapshot_by_symbol[ranked_item.symbol]
        market_data = _market_data_from_snapshot(snapshot, iteration=iteration)
        symbol_market_state = brain.analyze(market_data)
        symbol_weight = weight_by_symbol.get(ranked_item.symbol, 0.0)
        symbol_capital_state = _build_symbol_capital_state(capital_state, symbol_weight, symbol_market_state)
        decision = decision_engine.decide(symbol_market_state, symbol_capital_state)
        issues = tuple(diagnoser.diagnose(symbol_market_state, symbol_capital_state, decision))
        final_decision = safety_guard.apply(symbol_market_state, symbol_capital_state, decision, issues)
        decisions.append(
            PortfolioDecisionRecord(
                symbol=ranked_item.symbol,
                rank=ranked_item.rank,
                alpha_score=ranked_item.alpha_score,
                portfolio_weight=round(symbol_weight, 6),
                market_state=symbol_market_state,
                capital_state=symbol_capital_state,
                decision=decision,
                issues=issues,
                final_decision=final_decision,
                data_source=ranked_item.data_source,
                data_status=ranked_item.data_status,
            )
        )

    result = PortfolioRunResult(
        timestamp=overall_market_data.timestamp,
        universe=tuple(symbols),
        symbol_snapshots=symbol_snapshots,
        ranked_symbols=ranked,
        weights=weights,
        overall_market_data=overall_market_data,
        overall_market_state=overall_market_state,
        capital_state=capital_state,
        decisions=tuple(decisions),
    )

    logger.record(
        {
            "iteration": iteration,
            "timestamp": result.timestamp,
            "universe": list(result.universe),
            "overall_market_data": asdict(result.overall_market_data),
            "overall_market_state": asdict(result.overall_market_state),
            "capital_state": asdict(result.capital_state),
            "ranked_symbols": [asdict(item) for item in result.ranked_symbols],
            "weights": [asdict(item) for item in result.weights],
            "decisions": [asdict(item) for item in result.decisions],
        }
    )
    return result


def run_once() -> CycleResult:
    feed = AKShareMarketFeed()
    brain = MarketBrain()
    controller = CapitalController()
    decision_engine = DecisionEngine()
    diagnoser = Diagnoser()
    safety_guard = SafetyGuard()
    logger = PipelineLogger(Path("reports") / "production" / "v12_pipeline.log")
    return _run_cycle(0, feed, brain, controller, decision_engine, diagnoser, safety_guard, logger)


def run_portfolio_once(symbols: Iterable[str] | None = None) -> PortfolioRunResult:
    symbol_list = tuple(symbols or DEFAULT_SYMBOLS)
    data_engine = MultiSymbolDataEngine()
    brain = MarketBrain()
    controller = CapitalController()
    decision_engine = DecisionEngine()
    diagnoser = Diagnoser()
    safety_guard = SafetyGuard()
    logger = PipelineLogger(Path("reports") / "production" / "v12_portfolio_pipeline.log")
    ranker = AlphaRanker()
    allocator = PortfolioAllocator()
    result = _run_portfolio_cycle(
        0,
        symbol_list,
        data_engine,
        brain,
        controller,
        decision_engine,
        diagnoser,
        safety_guard,
        logger,
        ranker,
        allocator,
    )
    _print_portfolio_summary(result)
    return result


def run_loop(iterations: int | None, interval_seconds: float) -> None:
    feed = AKShareMarketFeed()
    brain = MarketBrain()
    controller = CapitalController()
    decision_engine = DecisionEngine()
    diagnoser = Diagnoser()
    safety_guard = SafetyGuard()
    logger = PipelineLogger(Path("reports") / "production" / "v12_pipeline.log")

    cycle = 0
    while iterations is None or cycle < iterations:
        _run_cycle(cycle, feed, brain, controller, decision_engine, diagnoser, safety_guard, logger)
        cycle += 1
        if iterations is None or cycle < iterations:
            time.sleep(max(0.1, interval_seconds))


def run_portfolio_loop(symbols: Iterable[str] | None, iterations: int | None, interval_seconds: float) -> None:
    symbol_list = tuple(symbols or DEFAULT_SYMBOLS)
    data_engine = MultiSymbolDataEngine()
    brain = MarketBrain()
    controller = CapitalController()
    decision_engine = DecisionEngine()
    diagnoser = Diagnoser()
    safety_guard = SafetyGuard()
    logger = PipelineLogger(Path("reports") / "production" / "v12_portfolio_pipeline.log")
    ranker = AlphaRanker()
    allocator = PortfolioAllocator()

    cycle = 0
    while iterations is None or cycle < iterations:
        result = _run_portfolio_cycle(
            cycle,
            symbol_list,
            data_engine,
            brain,
            controller,
            decision_engine,
            diagnoser,
            safety_guard,
            logger,
            ranker,
            allocator,
        )
        _print_portfolio_summary(result)
        cycle += 1
        if iterations is None or cycle < iterations:
            time.sleep(max(0.1, interval_seconds))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V12 single-file trading pipeline")
    parser.add_argument("--loop", action="store_true", help="Run continuously instead of a single cycle.")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="Number of cycles to run when looping.")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS, help="Seconds between cycles when looping.")
    parser.add_argument(
        "--symbols",
        type=str,
        default=os.environ.get("V12_SYMBOLS", ",".join(DEFAULT_SYMBOLS)),
        help="Comma-separated A-share symbols for the portfolio engine.",
    )
    parser.add_argument("--single", action="store_true", help="Run the legacy single-symbol mode.")
    return parser


def main() -> int:
    """Run the pure research and evaluation pipeline.

    This replaces live execution behavior with deterministic analysis,
    backtesting, diagnosis, and reporting.
    """

    parser = argparse.ArgumentParser(description="V12 pure research and evaluation pipeline")
    parser.add_argument(
        "--symbols",
        type=str,
        default=os.environ.get("V12_RESEARCH_SYMBOLS", ",".join(DEFAULT_SYMBOLS)),
        help="Comma-separated A-share symbols for the research universe.",
    )
    parser.add_argument(
        "--dashboard-refresh",
        action="store_true",
        help="Run the manual V12 dashboard refresh path and emit dashboard UI JSON.",
    )
    args = parser.parse_args()
    symbols = _parse_symbols(args.symbols)

    from core.v12_research_evaluation_engine import run_v12_research_evaluation
    from core.v12_research_report import V12ResearchReport
    from core.v12_dashboard_refresh import refresh_dashboard

    result = run_v12_research_evaluation(symbols=symbols)
    report_paths = V12ResearchReport().write(result)
    print(report_paths["markdown"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.dashboard_refresh:
        snapshot = refresh_dashboard(symbols=symbols)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
