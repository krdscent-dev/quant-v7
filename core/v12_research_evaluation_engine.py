"""V12 pure research and evaluation engine.

This module intentionally avoids all execution, broker, and order-routing
logic. It combines the V12 market intelligence stack with backtesting,
diagnosis, repair suggestions, and stability evaluation into a deterministic
research report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from core.research_engine import run_research_pipeline
from core.v12_1_structure_engine import MarketStructureEngine
from core.v12_2_capital_flow_engine import CapitalFlowEngine
from core.v12_3_narrative_engine import NarrativeEngine
from core.v12_4_cycle_engine import CycleEngine
from core.v12_5_capital_control_engine import CapitalControlEngine
from core.v12_validation_engine import V12SystemValidationEngine
from diagnosis.bias_detector import BiasDetector
from diagnosis.repair_engine import RepairEngine
from diagnosis.v12_7_health_monitor import HealthMonitor
from portfolio.multi_symbol_data_engine import MultiSymbolDataEngine, SymbolSnapshot, _clamp
from core.v12_6_system_backtest_engine import V126SystemBacktestEngine
from production.stability_monitor import StabilityMonitor


DEFAULT_SYMBOLS = ("000001", "000333", "300750", "600519", "601318")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(frozen=True)
class ResearchEvaluationResult:
    market_regime: dict[str, Any]
    capital_flow: dict[str, Any]
    narrative: dict[str, Any]
    cycle_state: dict[str, Any]
    strategy_score: float
    stability_score: float
    risk_score: float
    backtest_result: dict[str, float]
    recommendation: str
    confidence: float
    confidence_label: str
    repair_suggestions: list[dict[str, Any]]
    diagnosis: dict[str, Any]
    evaluation_summary: str


class V12ResearchEvaluationEngine:
    """Combine the V12 research stack into a pure evaluation report."""

    def __init__(
        self,
        *,
        symbol_engine: MultiSymbolDataEngine | None = None,
        backtest_engine: V126SystemBacktestEngine | None = None,
        validation_engine: V12SystemValidationEngine | None = None,
        health_monitor: HealthMonitor | None = None,
        bias_detector: BiasDetector | None = None,
        repair_engine: RepairEngine | None = None,
        stability_monitor: StabilityMonitor | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.symbol_engine = symbol_engine or MultiSymbolDataEngine()
        self.structure_engine = MarketStructureEngine()
        self.flow_engine = CapitalFlowEngine()
        self.narrative_engine = NarrativeEngine()
        self.cycle_engine = CycleEngine()
        self.capital_control_engine = CapitalControlEngine()
        self.backtest_engine = backtest_engine or V126SystemBacktestEngine()
        self.validation_engine = validation_engine or V12SystemValidationEngine(self.backtest_engine)
        self.health_monitor = health_monitor or HealthMonitor()
        self.bias_detector = bias_detector or BiasDetector()
        self.repair_engine = repair_engine or RepairEngine()
        self.stability_monitor = stability_monitor or StabilityMonitor()
        self.output_dir = output_dir or (Path("reports") / "research")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _aggregate_market_data(self, snapshots: Sequence[SymbolSnapshot]) -> dict[str, Any]:
        if not snapshots:
            return {
                "close": 1.0,
                "high": 1.0,
                "low": 1.0,
                "historical_close_series": [],
                "volatility": 0.5,
                "trend": 0.5,
                "momentum": 0.5,
            }
        close = mean(item.close for item in snapshots)
        high = mean(item.close * (1.0 + item.volatility * 0.02) for item in snapshots)
        low = mean(item.close * (1.0 - item.volatility * 0.02) for item in snapshots)
        volatility = mean(item.volatility for item in snapshots)
        trend = mean(item.trend for item in snapshots)
        momentum = mean(item.momentum for item in snapshots)
        historical_series: list[float] = []
        for offset in range(1, 6):
            values = [
                getattr(item, "historical_close_series", [item.close])[-offset]
                for item in snapshots
                if len(getattr(item, "historical_close_series", [item.close])) >= offset
            ]
            if values:
                historical_series.append(round(sum(values) / len(values), 4))
        return {
            "close": round(close, 4),
            "high": round(high, 4),
            "low": round(low, 4),
            "historical_close_series": list(reversed(historical_series)),
            "volatility": round(volatility, 4),
            "trend": round(trend, 4),
            "momentum": round(momentum, 4),
        }

    def _sector_data(self, snapshots: Sequence[SymbolSnapshot]) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
        sector_data: dict[str, float] = {}
        stock_data: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            sector = self._sector_name(snapshot)
            volume_proxy = getattr(snapshot, "volume", None)
            if volume_proxy is None:
                volume_proxy = max(1_000_000.0 * (0.8 + snapshot.breadth), 1.0)
            value = max(snapshot.close * float(volume_proxy), 1.0)
            sector_data[sector] = sector_data.get(sector, 0.0) + value
            stock_data[snapshot.symbol] = {
                "volume": float(volume_proxy),
                "price_change": snapshot.momentum - 0.5,
                "is_leader": snapshot.trend >= 0.7,
            }
        return sector_data, stock_data

    @staticmethod
    def _sector_name(snapshot: SymbolSnapshot) -> str:
        sector = getattr(snapshot, "sector", None)
        if sector:
            return str(sector)
        symbol = str(getattr(snapshot, "symbol", "UNKNOWN"))
        if symbol.startswith(("300", "688")):
            return "AI Computing"
        if symbol.startswith(("000", "002")):
            return "Domestic Substitution"
        if symbol.startswith(("600", "601")):
            return "Blue Chip"
        return "General"

    def _build_historical_records(self, snapshots: Sequence[SymbolSnapshot]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not snapshots:
            return [
                {
                    "timestamp": _now_iso(),
                    "symbol": "UNKNOWN",
                    "future_return": 0.0,
                    "market_data": {"close": 1.0, "high": 1.0, "low": 1.0, "volatility": 0.5},
                }
            ]
        for index, snapshot in enumerate(snapshots):
            future_return = round((snapshot.trend - snapshot.volatility) * 0.04 + (snapshot.momentum - 0.5) * 0.03, 6)
            records.append(
                {
                    "timestamp": snapshot.timestamp,
                    "symbol": snapshot.symbol,
                    "future_return": future_return,
                    "market_data": {
                        "close": snapshot.close,
                        "high": snapshot.close * 1.02,
                        "low": snapshot.close * 0.98,
                        "volatility": snapshot.volatility,
                        "trend": snapshot.trend,
                        "momentum": snapshot.momentum,
                    },
                }
            )
        return records

    def _strategy_score(self, symbols: Sequence[str]) -> tuple[float, list[dict[str, Any]]]:
        scores: list[float] = []
        details: list[dict[str, Any]] = []
        for symbol in symbols:
            research = run_research_pipeline(symbol)
            score = float(research.get("strategic_score", 0.0) or 0.0)
            scores.append(score)
            details.append(
                {
                    "symbol": symbol,
                    "strategic_score": round(score, 2),
                    "decision": research.get("research_conclusion", ""),
                    "confidence": float(research.get("factor_input_summary", {}).get("provider_summary", {}).get("financial_summary", {}).get("confidence_score", 0.0) or 0.0),
                }
            )
        if not scores:
            return 0.0, details
        top_scores = sorted(scores, reverse=True)[: min(3, len(scores))]
        strategy_score = sum(top_scores) / len(top_scores)
        return round(strategy_score, 2), details

    def evaluate(
        self,
        symbols: Sequence[str] | None = None,
        historical_market_data: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        symbol_list = tuple(symbols or DEFAULT_SYMBOLS)
        snapshots = self.symbol_engine.fetch_symbols(symbol_list)
        market_data = self._aggregate_market_data(snapshots)
        structure = self.structure_engine.analyze_market_structure(market_data)
        sector_data, stock_data = self._sector_data(snapshots)
        capital_flow = self.flow_engine.analyze_capital_flow(
            {"sector_data": sector_data, "stock_data": stock_data}
        )
        narrative = self.narrative_engine.extract_market_theme(
            {
                "sectors": list(sector_data.keys()),
                "flow_strength": capital_flow["flow_strength"],
                "sector_flows": sector_data,
                "news_keywords": list(sector_data.keys()),
            }
        )
        cycle_state = self.cycle_engine.build_cycle_state(
            {
                "volatility": market_data["volatility"],
                "flow_strength": capital_flow["flow_strength"],
                "narrative_strength": narrative["narrative_strength"],
            }
        )
        capital_simulation = self.capital_control_engine.build_capital_control(
            {
                "regime": structure["regime"],
                "flow_strength": capital_flow["flow_strength"],
                "narrative_strength": narrative["narrative_strength"],
                "cycle_state": cycle_state["unified_cycle_state"],
            },
            {
                "current_exposure": 0.0,
                "max_drawdown": 0.0,
            },
        )

        strategy_score, research_details = self._strategy_score(symbol_list)
        records = list(historical_market_data or self._build_historical_records(snapshots))
        backtest_result = self.backtest_engine.simulate(records)
        validation = self.validation_engine.validate(records)
        backtest_volatility_proxy = _clamp(
            float(backtest_result.max_drawdown) * 1.5 + (1.0 - float(backtest_result.win_rate)) * 0.4,
            0.0,
            1.0,
        )
        health = self.health_monitor.assess(backtest_result.__dict__, backtest_result.trade_log, {
            "agent_accuracy": backtest_result.win_rate,
            "risk_events": len(backtest_result.warnings),
            "volatility": backtest_volatility_proxy,
        })
        biases = self.bias_detector.detect(
            backtest_result.trade_log,
            agent_weights={"RiskAgent": 0.30, "AlphaAgent": 0.30},
            performance_metrics={"confidence_bias": "neutral"},
        )
        repairs = self.repair_engine.propose(health, biases, backtest_result.__dict__)
        stability = self.stability_monitor.assess(
            backtest_result.trade_log,
            [
                {
                    "final_weighted_decision": item.get("action", "OBSERVE"),
                    "market_intelligence": {"capital_flow_score": capital_flow["flow_strength"]},
                }
                for item in backtest_result.trade_log
            ],
            {"status": health.status},
        )

        stability_score = float(validation.get("stability_score", 0.0) or 0.0)
        risk_score = _clamp(
            max(
                float(validation.get("overfit_risk", 0.0) or 0.0),
                1.0 - float(health.score),
                0.5 * len([bias for bias in biases if bias.severity in {"HIGH", "CRITICAL"}]) / max(len(biases), 1),
            ),
            0.0,
            1.0,
        )
        confidence = _clamp(
            0.35 * float(health.score)
            + 0.35 * float(validation.get("stability_score", 0.0) or 0.0)
            + 0.30 * (1.0 - risk_score),
            0.0,
            1.0,
        )

        confidence_label = "LOW CONFIDENCE" if (not records or confidence < 0.5) else "CONFIDENT"
        if not records or not snapshots:
            recommendation = "OBSERVE"
            confidence_label = "LOW CONFIDENCE"
        elif float(validation.get("overfit_risk", 0.0) or 0.0) > 0.7:
            recommendation = "NO_GO"
        elif float(backtest_result.max_drawdown) > 0.2:
            recommendation = "OBSERVE"
        elif stability_score > 0.7 and float(backtest_result.total_return) > 0:
            recommendation = "GO"
        elif health.status == "CRITICAL" or stability_score < 0.5 or risk_score > 0.7:
            recommendation = "NO_GO"
        else:
            recommendation = "NEED_OPTIMIZATION"

        backtest_summary = {
            "return": round(float(backtest_result.total_return), 4),
            "drawdown": round(float(backtest_result.max_drawdown), 4),
            "win_rate": round(float(backtest_result.win_rate), 4),
        }
        evaluation_summary = (
            f"regime={structure['regime']} strategy_score={strategy_score:.2f} "
            f"stability={stability_score:.2f} risk={risk_score:.2f} recommendation={recommendation}"
        )
        return {
            "market_regime": {
                "structure": structure,
                "capital_flow": capital_flow,
                "narrative": narrative,
                "cycle_state": cycle_state,
                "capital_simulation": capital_simulation,
                "confidence": round(confidence, 4),
            },
            "capital_flow": capital_flow,
            "narrative": narrative,
            "cycle_state": cycle_state,
            "strategy_score": round(strategy_score, 2),
            "stability_score": round(stability_score, 4),
            "risk_score": round(risk_score, 4),
            "backtest_result": backtest_summary,
            "recommendation": recommendation,
            "confidence": round(confidence, 4),
            "confidence_label": confidence_label,
            "diagnosis": {
                "health": asdict(health),
                "biases": [asdict(item) for item in biases],
                "repairs": [asdict(item) for item in repairs],
                "stability": asdict(stability),
            },
            "research_details": research_details,
            "validation": validation,
            "evaluation_summary": evaluation_summary,
        }


def run_v12_research_evaluation(
    symbols: Sequence[str] | None = None,
    historical_market_data: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return V12ResearchEvaluationEngine().evaluate(symbols=symbols, historical_market_data=historical_market_data)
