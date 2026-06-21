"""System-level backtest for the V12 trading stack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from analytics.v12_6_attribution_engine import V126AttributionEngine, V126AttributionResult
from core.decision_engine import DecisionEngine
from core.v12_1_structure_engine import MarketStructureEngine
from core.v12_2_capital_flow_engine import CapitalFlowEngine
from core.v12_3_narrative_engine import NarrativeEngine
from core.v12_4_cycle_engine import CycleEngine
from core.v12_5_capital_control_engine import CapitalControlEngine
from logs.v12_6_trade_logger import V126TradeLogger


@dataclass(frozen=True)
class V126SystemBacktestResult:
    total_return: float
    max_drawdown: float
    win_rate: float
    equity_curve: list[dict[str, Any]]
    trade_log: list[dict[str, Any]]
    attribution: dict[str, float]
    warnings: list[str]


class V126SystemBacktestEngine:
    """Replay the full V12 -> V12.5 -> V11 pipeline with execution friction."""

    def __init__(
        self,
        trade_logger: V126TradeLogger | None = None,
        attribution_engine: V126AttributionEngine | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        self.trade_logger = trade_logger or V126TradeLogger(base_dir / "logs" / "v12_6_trade_log.jsonl")
        self.attribution_engine = attribution_engine or V126AttributionEngine()
        self.decision_engine = decision_engine or DecisionEngine()
        self.structure_engine = MarketStructureEngine()
        self.flow_engine = CapitalFlowEngine()
        self.narrative_engine = NarrativeEngine()
        self.cycle_engine = CycleEngine()
        self.capital_control_engine = CapitalControlEngine()

    def simulate(
        self,
        historical_market_data: Sequence[Mapping[str, Any]],
        system_modules: Mapping[str, Any] | None = None,
        starting_equity: float = 100.0,
    ) -> V126SystemBacktestResult:
        if not historical_market_data:
            return V126SystemBacktestResult(
                total_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                equity_curve=[],
                trade_log=[],
                attribution={"market_contribution": 0.0, "capital_contribution": 0.0, "execution_contribution": 0.0},
                warnings=["no_historical_data"],
            )

        equity = float(starting_equity)
        peak_equity = equity
        equity_curve: list[dict[str, Any]] = []
        trade_log: list[dict[str, Any]] = []
        trade_wins = 0
        warnings: list[str] = []
        system_modules = dict(system_modules or {})
        current_exposure = 0.0

        for index, record in enumerate(historical_market_data):
            snapshot = self._normalize_snapshot(record)
            market_data = snapshot["market_data"]
            future_return = snapshot["future_return"]
            timestamp = snapshot["timestamp"]
            symbol = snapshot["symbol"]

            structure = self.structure_engine.analyze_market_structure(market_data)
            sector_data = self._sector_data(market_data)
            stock_data = self._stock_data(market_data)
            flow = self.flow_engine.analyze_capital_flow(
                {
                    "sector_data": sector_data,
                    "stock_data": stock_data,
                }
            )
            narrative = self.narrative_engine.extract_market_theme(
                {
                    "sectors": list(sector_data) or list(market_data.get("sectors", [])),
                    "flow_strength": flow["flow_strength"],
                    "sector_flows": sector_data,
                    "news_keywords": market_data.get("news_keywords", []),
                }
            )
            cycle = self.cycle_engine.build_cycle_state(
                {
                    "volatility": self._to_float(market_data.get("volatility"), default=0.5),
                    "flow_strength": flow["flow_strength"],
                    "narrative_strength": narrative["narrative_strength"],
                    "fear_index": market_data.get("fear_index", 50.0),
                }
            )
            capital = self.capital_control_engine.build_capital_control(
                {
                    "regime": structure["regime"],
                    "flow_strength": flow["flow_strength"],
                    "narrative_strength": narrative["narrative_strength"],
                    "cycle_state": cycle["unified_cycle_state"],
                },
                {
                    "current_exposure": current_exposure,
                    "max_drawdown": (peak_equity - equity) / peak_equity if peak_equity else 0.0,
                },
            )

            score = self._score(structure, flow["flow_strength"], narrative["narrative_strength"])
            confidence = self._confidence(structure, flow["flow_strength"], narrative["narrative_strength"])
            top_sector = self._top_sector(sector_data)
            sector_strength = self._sector_strength(top_sector, sector_data)
            leader_flag = self._leader_flag(top_sector, stock_data)
            decision = self.decision_engine.decide(
                symbol=symbol,
                score=score,
                regime=structure["regime"],
                confidence=confidence,
                context={
                    "sector": top_sector,
                    "sector_strength": sector_strength,
                    "sector_leader_flag": leader_flag,
                    "cycle_state": cycle["unified_cycle_state"],
                    "risk_appetite": self._risk_appetite(cycle["unified_cycle_state"]),
                    "liquidity_cycle": cycle["liquidity_cycle"],
                    "sentiment_cycle": cycle["sentiment_cycle"],
                    "industry_cycle": cycle["industry_cycle"],
                    "combined_cycle_state": cycle["unified_cycle_state"],
                    "confidence_sensitivity": capital["leverage_adjustment"],
                },
            )
            size = self._decision_size(decision["action"], capital["position_multiplier"], capital["leverage_adjustment"])
            slippage = self._clamp(self._to_float(market_data.get("volatility"), default=0.5) * 0.01)
            fill_probability = self._clamp(1.0 - self._to_float(market_data.get("volatility"), default=0.5))
            fill_factor = self._clamp(fill_probability * (1.0 - slippage))
            action_sign = -1.0 if decision["action"] in {"REDUCE", "EXIT"} else 1.0
            gross_pnl = action_sign * size * future_return
            pnl = gross_pnl * fill_factor
            if confidence < 0.60:
                pnl *= 0.80

            market_contribution, capital_contribution, execution_contribution = self._attribution_components(
                gross_pnl=gross_pnl,
                actual_pnl=pnl,
                structure_strength=structure["structure_strength"],
                position_multiplier=capital["position_multiplier"],
            )
            trade_record = {
                "timestamp": timestamp,
                "step": index,
                "symbol": symbol,
                "action": decision["action"],
                "future_return": round(future_return, 6),
                "volatility": round(self._to_float(market_data.get("volatility"), default=0.5), 4),
                "size": round(size, 6),
                "slippage": round(slippage, 6),
                "fill_probability": round(fill_probability, 6),
                "fill_factor": round(fill_factor, 6),
                "pnl": round(pnl, 6),
                "market_state": {
                    "structure": structure,
                    "flow": flow,
                    "narrative": narrative,
                    "cycle": cycle,
                },
                "capital_state": capital,
                "decision": decision,
                "layer_contributions": {
                    "market_structure": round(market_contribution, 6),
                    "capital_control": round(capital_contribution, 6),
                    "execution": round(execution_contribution, 6),
                },
                "context": {
                    "score": round(score, 4),
                    "confidence": round(confidence, 4),
                    "sector": top_sector,
                    "sector_strength": round(sector_strength, 4),
                    "leader_flag": leader_flag,
                    "cycle_state": cycle["unified_cycle_state"],
                },
            }
            trade_log.append(self.trade_logger.log_trade(trade_record))

            if pnl > 0:
                trade_wins += 1
            equity *= 1.0 + pnl
            peak_equity = max(peak_equity, equity)
            drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
            current_exposure = min(1.0, abs(size))
            equity_curve.append(
                {
                    "timestamp": timestamp,
                    "equity": round(equity, 6),
                    "pnl": round(pnl, 6),
                    "drawdown": round(drawdown, 6),
                    "regime": structure["regime"],
                    "cycle_state": cycle["unified_cycle_state"],
                }
            )

        attribution: V126AttributionResult = self.attribution_engine.analyze(trade_log, starting_equity=starting_equity)
        max_drawdown = max((float(item["drawdown"]) for item in equity_curve), default=0.0)
        total_return = (equity / starting_equity) - 1.0 if starting_equity else 0.0
        win_rate = trade_wins / len(trade_log) if trade_log else 0.0
        warnings.extend(attribution.warnings)

        return V126SystemBacktestResult(
            total_return=round(total_return, 6),
            max_drawdown=round(max_drawdown, 6),
            win_rate=round(win_rate, 4),
            equity_curve=equity_curve,
            trade_log=trade_log,
            attribution=attribution.layer_breakdown,
            warnings=warnings,
        )

    def _normalize_snapshot(self, record: Mapping[str, Any]) -> dict[str, Any]:
        market_data = dict(record.get("market_data", {}) or {})
        if not market_data:
            market_data = {
                "close": 1.0,
                "high": 1.0,
                "low": 1.0,
                "volatility": 0.5,
            }
        timestamp = str(record.get("timestamp", "2026-06-21T00:00:00+00:00"))
        symbol = str(record.get("symbol", market_data.get("symbol", "UNKNOWN")))
        future_return = self._to_float(record.get("future_return"), default=0.0)
        return {
            "timestamp": timestamp,
            "symbol": symbol,
            "future_return": future_return,
            "market_data": market_data,
        }

    @staticmethod
    def _sector_data(market_data: Mapping[str, Any]) -> dict[str, float]:
        sector_data = market_data.get("sector_data", {}) or {}
        if isinstance(sector_data, Mapping):
            normalized: dict[str, float] = {}
            for key, value in sector_data.items():
                try:
                    normalized[str(key)] = float(value)
                except Exception:
                    continue
            return normalized
        sectors = market_data.get("sectors", []) or []
        if isinstance(sectors, Sequence) and not isinstance(sectors, (str, bytes)):
            return {str(sector): 1.0 for sector in sectors}
        return {}

    @staticmethod
    def _stock_data(market_data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        stock_data = market_data.get("stock_data", {}) or {}
        if not isinstance(stock_data, Mapping):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for symbol, payload in stock_data.items():
            if not isinstance(payload, Mapping):
                continue
            normalized[str(symbol)] = {
                "volume": float(payload.get("volume", 0.0) or 0.0),
                "price_change": float(payload.get("price_change", 0.0) or 0.0),
                "is_leader": bool(payload.get("is_leader", False)),
            }
        return normalized

    def _score(self, structure: Mapping[str, Any], flow_strength: float, narrative_strength: float) -> float:
        structure_strength = self._to_float(structure.get("structure_strength"), default=0.5)
        trend_score = self._to_float(structure.get("trend_score"), default=0.5)
        score = 100.0 * (
            0.35 * trend_score
            + 0.20 * self._clamp(flow_strength)
            + 0.20 * self._clamp(narrative_strength)
            + 0.25 * self._clamp(structure_strength)
        )
        return self._clamp(score / 100.0) * 100.0

    def _confidence(self, structure: Mapping[str, Any], flow_strength: float, narrative_strength: float) -> float:
        structure_confidence = self._to_float(structure.get("trend_score"), default=0.5)
        confidence = 0.40 + 0.30 * self._clamp(flow_strength) + 0.20 * self._clamp(narrative_strength) + 0.10 * structure_confidence
        return self._clamp(confidence)

    @staticmethod
    def _top_sector(sector_data: Mapping[str, float]) -> str:
        if not sector_data:
            return "UNKNOWN"
        return max(sector_data.items(), key=lambda item: float(item[1]))[0]

    @staticmethod
    def _sector_strength(top_sector: str, sector_data: Mapping[str, float]) -> float:
        if not sector_data or top_sector == "UNKNOWN":
            return 0.0
        values = [float(value) for value in sector_data.values()]
        max_value = max(values) if values else 1.0
        if max_value <= 0.0:
            return 0.0
        return float(sector_data.get(top_sector, 0.0)) / max_value

    @staticmethod
    def _leader_flag(top_sector: str, stock_data: Mapping[str, Mapping[str, Any]]) -> bool:
        if not stock_data or top_sector == "UNKNOWN":
            return False
        return any(bool(payload.get("is_leader", False)) for payload in stock_data.values())

    @staticmethod
    def _risk_appetite(cycle_state: str) -> str:
        if cycle_state == "RISK_ON":
            return "RISING"
        if cycle_state == "RISK_OFF":
            return "FALLING"
        return "SELECTIVE"

    @staticmethod
    def _decision_size(action: str, position_multiplier: float, leverage_adjustment: float) -> float:
        base_map = {
            "ADD": 0.08,
            "SMALL_ADD": 0.04,
            "HOLD": 0.02,
            "OBSERVE": 0.0,
            "REDUCE": 0.05,
            "EXIT": 0.10,
        }
        size = base_map.get(action.upper(), 0.02) * max(0.5, position_multiplier) * max(0.5, leverage_adjustment)
        return round(max(0.0, min(0.15, size)), 6)

    def _attribution_components(
        self,
        *,
        gross_pnl: float,
        actual_pnl: float,
        structure_strength: float,
        position_multiplier: float,
    ) -> tuple[float, float, float]:
        market_contribution = gross_pnl * (0.30 + 0.20 * self._clamp(structure_strength))
        capital_contribution = gross_pnl * (0.15 + 0.10 * max(0.0, position_multiplier - 1.0))
        execution_contribution = actual_pnl - market_contribution - capital_contribution
        return market_contribution, capital_contribution, execution_contribution

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

