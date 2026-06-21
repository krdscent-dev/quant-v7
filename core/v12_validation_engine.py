"""System validation layer for the V12 trading stack."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any, Mapping, Sequence

from core.v12_6_system_backtest_engine import V126SystemBacktestEngine


@dataclass(frozen=True)
class ValidationResult:
    stability_score: float
    profit_score: float
    overfit_risk: float
    overall_score: float
    failure_points: list[str]
    recommendation: str


class StabilityTestEngine:
    """Measure how stable the full system behaves across regimes."""

    def __init__(self, backtest_engine: V126SystemBacktestEngine | None = None) -> None:
        self.backtest_engine = backtest_engine or V126SystemBacktestEngine()

    def run(self, historical_market_data: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        scenarios = self._build_scenarios(historical_market_data)
        results = [self.backtest_engine.simulate(scenario) for scenario in scenarios]
        returns = [result.total_return for result in results]
        drawdowns = [result.max_drawdown for result in results]
        return {
            "scenario_results": results,
            "returns": returns,
            "drawdowns": drawdowns,
            "stability_score": self._stability_score(results),
        }

    def _stability_score(self, results: Sequence[Any]) -> float:
        if not results:
            return 0.0
        avg_drawdown = sum(float(result.max_drawdown) for result in results) / len(results)
        return self._clamp(1.0 - avg_drawdown)

    def _build_scenarios(self, historical_market_data: Sequence[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
        base = [self._normalize_record(record) for record in historical_market_data]
        if not base:
            base = [self._default_record()]
        return [
            self._mutate_regime(base, "HIGH_VOL"),
            self._mutate_regime(base, "LOW_VOL"),
            self._mutate_regime(base, "BULL"),
            self._mutate_regime(base, "BEAR"),
            self._shuffle(base),
        ]

    def _mutate_regime(self, base: Sequence[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
        mutated: list[dict[str, Any]] = []
        for index, record in enumerate(base):
            payload = self._clone(record)
            market_data = dict(payload["market_data"])
            future_return = float(payload["future_return"])
            volatility = self._to_float(market_data.get("volatility"), default=0.5)
            close = self._to_float(market_data.get("close"), default=1.0)
            high = self._to_float(market_data.get("high"), default=close)
            low = self._to_float(market_data.get("low"), default=close)

            if mode == "HIGH_VOL":
                market_data["volatility"] = self._clamp(max(volatility, 0.75))
                market_data["high"] = close * 1.08
                market_data["low"] = close * 0.92
                future_return *= 0.35
            elif mode == "LOW_VOL":
                market_data["volatility"] = self._clamp(min(volatility, 0.20))
                market_data["high"] = close * 1.01
                market_data["low"] = close * 0.99
                future_return *= 0.90
            elif mode == "BULL":
                market_data["volatility"] = self._clamp(min(volatility, 0.35))
                close *= 1.03 + 0.01 * index
                market_data["close"] = close
                market_data["high"] = close * 1.02
                market_data["low"] = close * 0.99
                future_return = abs(future_return) + 0.02
            elif mode == "BEAR":
                market_data["volatility"] = self._clamp(max(volatility, 0.65))
                close *= 0.98 - 0.01 * index
                market_data["close"] = close
                market_data["high"] = close * 1.01
                market_data["low"] = close * 0.95
                future_return = -abs(future_return) - 0.015

            payload["market_data"] = market_data
            payload["future_return"] = round(future_return, 6)
            mutated.append(payload)
        return mutated

    def _shuffle(self, base: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = [self._clone(record) for record in base]
        ordered.sort(key=lambda record: self._stable_key(record), reverse=True)
        return ordered

    @staticmethod
    def _stable_key(record: Mapping[str, Any]) -> int:
        timestamp = str(record.get("timestamp", ""))
        symbol = str(record.get("symbol", ""))
        digest = sha1(f"{timestamp}:{symbol}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    @staticmethod
    def _normalize_record(record: Mapping[str, Any]) -> dict[str, Any]:
        payload = {
            "timestamp": str(record.get("timestamp", "2026-06-21T00:00:00+00:00")),
            "symbol": str(record.get("symbol", "UNKNOWN")),
            "future_return": float(record.get("future_return", 0.0) or 0.0),
            "market_data": dict(record.get("market_data", {}) or {}),
        }
        market_data = payload["market_data"]
        if "volatility" not in market_data:
            close = float(market_data.get("close", 1.0) or 1.0)
            high = float(market_data.get("high", close) or close)
            low = float(market_data.get("low", close) or close)
            market_data["volatility"] = (high - low) / close if close else 0.5
        if "close" not in market_data:
            market_data["close"] = 1.0
        if "high" not in market_data:
            market_data["high"] = float(market_data["close"]) * 1.01
        if "low" not in market_data:
            market_data["low"] = float(market_data["close"]) * 0.99
        return payload

    @staticmethod
    def _clone(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "timestamp": str(record.get("timestamp", "2026-06-21T00:00:00+00:00")),
            "symbol": str(record.get("symbol", "UNKNOWN")),
            "future_return": float(record.get("future_return", 0.0) or 0.0),
            "market_data": dict(record.get("market_data", {}) or {}),
        }

    @staticmethod
    def _default_record() -> dict[str, Any]:
        return {
            "timestamp": "2026-06-21T00:00:00+00:00",
            "symbol": "UNKNOWN",
            "future_return": 0.0,
            "market_data": {"close": 1.0, "high": 1.0, "low": 1.0, "volatility": 0.5},
        }

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


class ProfitRobustnessTestEngine:
    """Measure whether the system maintains positive returns across regimes."""

    def score(self, scenario_results: Sequence[Any]) -> float:
        if not scenario_results:
            return 0.0
        returns = [self._to_float(result.total_return) for result in scenario_results]
        positive_ratio = sum(1 for item in returns if item > 0) / len(returns)
        average_return = sum(returns) / len(returns)
        return max(0.0, min(1.0, 0.55 * positive_ratio + 0.45 * max(0.0, min(1.0, average_return + 0.5))))

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default


class OverfittingStressTestEngine:
    """Estimate overfitting risk using shuffled vs. structured scenarios."""

    def score(self, ordered_results: Sequence[Any], shuffled_results: Sequence[Any]) -> float:
        if not ordered_results or not shuffled_results:
            return 0.5
        ordered_return = sum(self._to_float(result.total_return) for result in ordered_results) / len(ordered_results)
        shuffled_return = sum(self._to_float(result.total_return) for result in shuffled_results) / len(shuffled_results)
        drift = abs(ordered_return - shuffled_return)
        volatility_penalty = sum(self._to_float(result.max_drawdown) for result in ordered_results) / len(ordered_results)
        return max(0.0, min(1.0, 0.5 * drift + 0.5 * volatility_penalty))

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default


class V12SystemValidationEngine:
    """Evaluate full V12 robustness across stress scenarios."""

    def __init__(self, backtest_engine: V126SystemBacktestEngine | None = None) -> None:
        self.stability_engine = StabilityTestEngine(backtest_engine)
        self.profit_engine = ProfitRobustnessTestEngine()
        self.overfit_engine = OverfittingStressTestEngine()

    def validate(self, historical_market_data: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not historical_market_data:
            return {
                "stability_score": 0.0,
                "profit_score": 0.0,
                "overfit_risk": 0.5,
                "overall_score": 0.0,
                "failure_points": ["no_historical_data"],
                "recommendation": "Provide historical market data before validating the system.",
            }
        stability = self.stability_engine.run(historical_market_data)
        scenario_results = stability["scenario_results"]
        ordered_results = scenario_results[:4]
        shuffled_results = scenario_results[4:]
        stability_score = self._stability_score(stability["stability_score"], scenario_results)
        profit_score = self.profit_engine.score(scenario_results)
        overfit_risk = self.overfit_engine.score(ordered_results, shuffled_results)
        overall_score = self._overall_score(stability_score, profit_score, overfit_risk)
        failure_points = self._failure_points(stability_score, profit_score, overfit_risk, scenario_results)
        recommendation = self._recommendation(stability_score, profit_score, overfit_risk, failure_points)
        return {
            "stability_score": round(stability_score, 4),
            "profit_score": round(profit_score, 4),
            "overfit_risk": round(overfit_risk, 4),
            "overall_score": round(overall_score, 4),
            "failure_points": failure_points,
            "recommendation": recommendation,
        }

    def _stability_score(self, base_score: float, scenario_results: Sequence[Any]) -> float:
        drawdowns = [self._to_float(result.max_drawdown) for result in scenario_results]
        if not drawdowns:
            return max(0.0, min(1.0, base_score))
        consistency_penalty = max(drawdowns) - min(drawdowns)
        return max(0.0, min(1.0, 0.7 * base_score + 0.3 * (1.0 - consistency_penalty)))

    def _overall_score(self, stability_score: float, profit_score: float, overfit_risk: float) -> float:
        return max(0.0, min(1.0, 0.45 * stability_score + 0.35 * profit_score + 0.20 * (1.0 - overfit_risk)))

    def _failure_points(
        self,
        stability_score: float,
        profit_score: float,
        overfit_risk: float,
        scenario_results: Sequence[Any],
    ) -> list[str]:
        failures: list[str] = []
        if stability_score < 0.5:
            failures.append("stability_score_below_threshold")
        if overfit_risk > 0.7:
            failures.append("overfit_risk_above_threshold")
        drawdowns = [self._to_float(result.max_drawdown) for result in scenario_results]
        if sum(1 for item in drawdowns if item > 0.2) >= 2:
            failures.append("multiple_regimes_exceed_drawdown_threshold")
        if profit_score < 0.45:
            failures.append("profit_robustness_low")
        return failures

    def _recommendation(
        self,
        stability_score: float,
        profit_score: float,
        overfit_risk: float,
        failure_points: Sequence[str],
    ) -> str:
        if failure_points:
            return "Harden system controls before deployment."
        if stability_score >= 0.7 and profit_score >= 0.6 and overfit_risk <= 0.4:
            return "System is robust enough for controlled production use."
        return "Continue monitoring and improve robustness before scaling."

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default
