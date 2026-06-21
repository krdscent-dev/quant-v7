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
from typing import Iterable


SEED = int(os.environ.get("V12_SEED", "42"))
DEFAULT_INTERVAL_SECONDS = float(os.environ.get("V12_INTERVAL_SECONDS", "2.0"))
DEFAULT_ITERATIONS = int(os.environ.get("V12_ITERATIONS", "1"))


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
            timestamp=_now_iso(),
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


def _run_cycle(
    iteration: int,
    feed: MockMarketFeed,
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


def run_once() -> CycleResult:
    feed = MockMarketFeed()
    brain = MarketBrain()
    controller = CapitalController()
    decision_engine = DecisionEngine()
    diagnoser = Diagnoser()
    safety_guard = SafetyGuard()
    logger = PipelineLogger(Path("reports") / "production" / "v12_pipeline.log")
    return _run_cycle(0, feed, brain, controller, decision_engine, diagnoser, safety_guard, logger)


def run_loop(iterations: int | None, interval_seconds: float) -> None:
    feed = MockMarketFeed()
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


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V12 single-file trading pipeline")
    parser.add_argument("--loop", action="store_true", help="Run continuously instead of a single cycle.")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="Number of cycles to run when looping.")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS, help="Seconds between cycles when looping.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    loop_requested = args.loop or os.environ.get("V12_LOOP", "0") == "1"
    if loop_requested:
        iterations = args.iterations if args.iterations > 0 else None
        run_loop(iterations, args.interval)
    else:
        run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
