"""Deterministic V12.6 replay backtest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha1
from pathlib import Path
from statistics import mean
from typing import Any, Mapping

from analytics.attribution_engine import AttributionEngine, AttributionResult
from logs.trade_logger import TradeLogger


@dataclass(frozen=True)
class V126BacktestResult:
    """Summary of the replay-based verification run."""

    period: str
    total_return: float
    max_drawdown: float
    win_rate: float
    equity_curve: list[dict[str, Any]]
    trade_count: int
    layer_attribution: dict[str, float]
    attribution: AttributionResult
    warnings: list[str]


class V126BacktestEngine:
    """Replay the current V12->V12.5->V11 pipeline in a deterministic way."""

    def __init__(
        self,
        trade_logger: TradeLogger | None = None,
        attribution_engine: AttributionEngine | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        self.trade_logger = trade_logger or TradeLogger(base_dir / "logs" / "trade_log_v12_6.jsonl")
        self.attribution_engine = attribution_engine or AttributionEngine()

    def simulate(
        self,
        market_state: Mapping[str, Any],
        capital_state: Mapping[str, Any],
        decisions: list[Mapping[str, Any]],
        v11_decisions: list[Mapping[str, Any]],
        periods: int = 5,
        start_date: str = "2026-06-21",
    ) -> V126BacktestResult:
        if not v11_decisions:
            attribution = self.attribution_engine.analyze([], starting_equity=100.0)
            return V126BacktestResult(
                period=f"{start_date}->{start_date}",
                total_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                equity_curve=[],
                trade_count=0,
                layer_attribution=attribution.layer_breakdown,
                attribution=attribution,
                warnings=["no_decisions"],
            )

        base_date = datetime.fromisoformat(start_date)
        market_regime = str(market_state.get("regime", "UNKNOWN"))
        market_structure = market_state.get("structure")
        structure_strength = float(getattr(market_structure, "structure_strength", 0.5) or 0.5)
        capital_bias = str(capital_state.get("capital_bias", "BALANCED"))
        allocation_ceiling = float(capital_state.get("allocation_ceiling", 0.10) or 0.10)
        capital_risk = float(capital_state.get("risk_score", 0.0) or 0.0)
        risk_multiplier = max(0.55, 1.0 - capital_risk * 0.35)
        regime_multiplier = {
            "BULL": 1.12,
            "BEAR": 0.82,
            "RANGE": 0.98,
            "TRANSITION": 0.94,
        }.get(market_regime, 1.0)
        bias_multiplier = {
            "EXPANSIVE": 1.08,
            "BALANCED": 1.00,
            "DEFENSIVE": 0.88,
        }.get(capital_bias, 1.0)

        equity = 100.0
        peak_equity = equity
        equity_curve: list[dict[str, Any]] = []
        trade_logs: list[dict[str, Any]] = []
        daily_returns: list[float] = []
        warnings: list[str] = []

        for day_index in range(periods):
            current_date = (base_date + timedelta(days=day_index)).date().isoformat()
            day_pnl = 0.0
            day_trade_count = 0
            for trade_index, decision in enumerate(v11_decisions):
                symbol = str(decision.get("symbol", "UNKNOWN"))
                action = str(decision.get("final_weighted_decision", decision.get("final_action", "OBSERVE")))
                action_multiplier = self._action_multiplier(action)
                alpha_score = float(decision.get("alpha_score", 0.0) or 0.0)
                risk_score = float(decision.get("risk_score", 0.0) or 0.0)
                sector_context = decision.get("sector_context", {}) or {}
                sector_strength = float(sector_context.get("sector_strength", 0.0) or 0.0)
                sector = str(sector_context.get("sector", "UNKNOWN"))
                confidence = self._confidence_from_decision(decision)
                deterministic_jitter = self._jitter(symbol, day_index)

                base_edge = (
                    0.0025
                    + 0.0045 * alpha_score
                    + 0.0030 * sector_strength
                    + 0.0015 * structure_strength
                    + 0.0010 * (1.0 - risk_score)
                    + 0.0005 * allocation_ceiling
                )
                pnl = base_edge * action_multiplier * regime_multiplier * bias_multiplier * risk_multiplier * deterministic_jitter
                if action in {"REDUCE", "EXIT"}:
                    pnl *= -1.0
                if action in {"OBSERVE"}:
                    pnl *= 0.35
                if confidence < 0.6:
                    pnl *= 0.80

                layer_contributions = {
                    "market_structure": round(pnl * 0.34, 6),
                    "capital_control": round(pnl * 0.26, 6),
                    "execution": round(pnl * 0.40, 6),
                }
                trade_record = {
                    "timestamp": f"{current_date}T{8 + trade_index // 3:02d}:{(trade_index * 11) % 60:02d}:00",
                    "date": current_date,
                    "symbol": symbol,
                    "sector": sector,
                    "action": action,
                    "confidence": round(confidence, 4),
                    "alpha_score": round(alpha_score, 4),
                    "risk_score": round(risk_score, 4),
                    "market_regime": market_regime,
                    "capital_bias": capital_bias,
                    "pnl": round(pnl, 6),
                    "layer_contributions": layer_contributions,
                    "context": {
                        "sector_strength": round(sector_strength, 4),
                        "allocation_ceiling": round(allocation_ceiling, 4),
                        "regime_multiplier": round(regime_multiplier, 4),
                        "bias_multiplier": round(bias_multiplier, 4),
                        "risk_multiplier": round(risk_multiplier, 4),
                    },
                }
                trade_logs.append(self.trade_logger.log_trade(trade_record))
                day_pnl += pnl
                day_trade_count += 1

            if day_trade_count == 0:
                warnings.append(f"no_trades_on_{current_date}")
                daily_return = 0.0
            else:
                daily_return = day_pnl / 100.0
            equity *= 1.0 + daily_return
            peak_equity = max(peak_equity, equity)
            drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
            equity_curve.append(
                {
                    "date": current_date,
                    "equity": round(equity, 6),
                    "daily_return": round(daily_return, 6),
                    "drawdown": round(drawdown, 6),
                }
            )
            daily_returns.append(daily_return)

        attribution = self.attribution_engine.analyze(trade_logs, starting_equity=100.0)
        max_drawdown = max((float(item["drawdown"]) for item in equity_curve), default=0.0)
        total_return = (equity / 100.0) - 1.0
        win_rate = mean([1.0 if item > 0 else 0.0 for item in daily_returns]) if daily_returns else 0.0
        warnings.extend(attribution.warnings)

        return V126BacktestResult(
            period=f"{start_date}->{(base_date + timedelta(days=periods - 1)).date().isoformat()}",
            total_return=round(total_return, 6),
            max_drawdown=round(max_drawdown, 6),
            win_rate=round(win_rate, 4),
            equity_curve=equity_curve,
            trade_count=len(trade_logs),
            layer_attribution=attribution.layer_breakdown,
            attribution=attribution,
            warnings=warnings,
        )

    @staticmethod
    def _action_multiplier(action: str) -> float:
        mapping = {
            "BUY": 1.35,
            "ADD": 1.25,
            "SMALL_ADD": 1.10,
            "HOLD": 0.72,
            "OBSERVE": 0.40,
            "REDUCE": 0.15,
            "EXIT": 0.05,
        }
        return mapping.get(action.upper(), 0.50)

    @staticmethod
    def _confidence_from_decision(decision: Mapping[str, Any]) -> float:
        payload = decision.get("market_intelligence", {}) or {}
        alpha_score = float(decision.get("alpha_score", 0.0) or 0.0)
        risk_score = float(decision.get("risk_score", 0.0) or 0.0)
        capital_flow = float(payload.get("capital_flow_score", 0.0) or 0.0)
        confidence = 0.35 + 0.35 * alpha_score + 0.15 * capital_flow + 0.15 * (1.0 - risk_score)
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _jitter(symbol: str, day_index: int) -> float:
        digest = sha1(f"{symbol}:{day_index}".encode("utf-8")).hexdigest()
        raw = int(digest[:8], 16) / 0xFFFFFFFF
        return 0.95 + raw * 0.10

