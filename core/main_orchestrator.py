"""Unified orchestration entry point for V12, V12.5, and V11."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping

from core.decision_engine import DecisionEngine
from core.v10_audit_engine import V10AuditEngine
from core.v10_cognitive_graph import V10CognitiveGraph
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import V11AgentOrchestrator
from core.v12_5_capital_control import V125CapitalControlEngine
from market.v12_1_structure_engine import analyze_market_structure
from market.v12_2_capital_flow_engine import V122CapitalFlowEngine
from market.v12_3_narrative_engine import V123NarrativeEngine
from market.v12_4_cycle_engine import V124CycleEngine


@dataclass(frozen=True)
class V12OrchestrationResult:
    """Structured output for the unified pipeline."""

    market_state: dict[str, Any]
    capital_state: dict[str, Any]
    decisions: list[dict[str, Any]]
    v11_decisions: list[dict[str, Any]]
    sector_engine: V10SectorEngine
    regime_result: Any


class MainOrchestrator:
    """Run market brain -> capital control -> V11 decision system."""

    def __init__(
        self,
        ranked_results: list[Any],
        decision_engine: DecisionEngine | None = None,
        audit_engine: V10AuditEngine | None = None,
    ) -> None:
        self.ranked_results = list(ranked_results)
        self.decision_engine = decision_engine or DecisionEngine()
        self.audit_engine = audit_engine or V10AuditEngine()
        self.cognitive_graph = V10CognitiveGraph()
        self.capital_control = V125CapitalControlEngine()
        self.sector_engine = V10SectorEngine.from_results(self.ranked_results)
        self.v11_orchestrator = V11AgentOrchestrator(self.sector_engine, self.audit_engine)

    def run(
        self,
        learning_context: Mapping[str, Any] | None = None,
    ) -> V12OrchestrationResult:
        learning_context = dict(learning_context or {})
        market_data = self._market_snapshot(self.ranked_results)
        market_structure = analyze_market_structure(
            trend_score=market_data["trend"],
            volatility=market_data["volatility"],
            price_momentum=market_data["price_momentum"],
        )
        sector_volume, capital_inflow, capital_outflow, leader_volume = self._sector_flow_inputs(self.sector_engine)
        capital_flow_analysis = V122CapitalFlowEngine().analyze_sector_flows(
            sector_trading_volume=sector_volume,
            capital_inflow=capital_inflow,
            capital_outflow=capital_outflow,
            leader_stock_volume=leader_volume,
        )
        narrative = V123NarrativeEngine().extract_market_theme(
            sector_data=self.sector_engine.sector_scores,
            capital_flow_data=capital_flow_analysis,
            market_structure=market_structure,
        )
        cycle_inputs = self._cycle_inputs(
            market_structure,
            capital_flow_analysis,
            narrative,
            self.sector_engine,
            self.ranked_results,
        )
        cycle_state = V124CycleEngine().build_cycle_state(*cycle_inputs)
        regime_result = self._regime_adapter(market_structure)
        sector_context = self.sector_engine.build_sector_context()
        flow_by_sector = {item.sector: item for item in capital_flow_analysis.ranked_flows}

        raw_decisions: list[dict[str, Any]] = []
        for item in self.ranked_results[:10]:
            confidence = self._confidence_from_result(item)
            symbol = getattr(item, "code", "UNKNOWN")
            theme = getattr(item, "theme", "UNKNOWN")
            item_sector_context = sector_context.get(str(symbol), {})
            sector_flow = flow_by_sector.get(str(item_sector_context.get("sector", "")))
            causal = self.cognitive_graph.infer_for_context(
                sector=str(item_sector_context.get("sector", "UNKNOWN")),
                theme=str(theme),
            )
            decision = self.decision_engine.decide(
                symbol=symbol,
                score=float(getattr(item, "strategic_score", 0.0)),
                regime=regime_result,
                confidence=confidence,
                context={
                    "price_zone": "UNKNOWN",
                    "momentum": "UNKNOWN",
                    "stage": "UNKNOWN",
                    "theme": theme,
                    "theme_tags": [
                        theme,
                        item_sector_context.get("sector", "UNKNOWN"),
                    ],
                    "causal_chain": causal.causal_chain,
                    "bottleneck_node": causal.bottleneck_node,
                    "chain_strength": causal.chain_strength,
                    "confidence_bias": learning_context.get("confidence_bias", 0.0),
                    "confidence_sensitivity": learning_context.get("confidence_sensitivity", 1.0),
                    "dominant_narrative": narrative.dominant_narrative,
                    "active_narratives": [item.narrative for item in narrative.active_narratives],
                    "narrative_strength": narrative.narrative_strength,
                    "narrative_phase": narrative.narrative_phase,
                    "narrative_consistency": narrative.consistency,
                    "supporting_themes": narrative.supporting_themes,
                    "macro_cycle": cycle_state.macro_cycle,
                    "liquidity_cycle": cycle_state.liquidity_cycle,
                    "sentiment_cycle": cycle_state.sentiment_cycle,
                    "industry_cycle": cycle_state.industry_cycle,
                    "risk_appetite": cycle_state.risk_appetite,
                    "combined_cycle_state": cycle_state.combined_cycle_state,
                    "cycle_aggressiveness": cycle_state.aggressiveness,
                    "capital_flow_score": sector_flow.flow_score if sector_flow else 0.0,
                    "capital_flow_direction": sector_flow.direction if sector_flow else "UNKNOWN",
                    "leader_concentration": sector_flow.leader_concentration if sector_flow else 0.0,
                    "rotation_path": capital_flow_analysis.rotation_path,
                    "cycle_state": {
                        "liquidity_cycle": cycle_state.liquidity_cycle,
                        "sentiment_cycle": cycle_state.sentiment_cycle,
                        "industry_cycle": cycle_state.industry_cycle,
                        "combined_cycle_state": cycle_state.combined_cycle_state,
                        "risk_appetite": cycle_state.risk_appetite,
                        "aggressiveness": cycle_state.aggressiveness,
                        "liquidity_score": cycle_state.liquidity_score,
                        "fear_index": cycle_state.fear_index,
                        "industry_growth": cycle_state.industry_growth,
                        "valuation_score": cycle_state.valuation_score,
                    },
                    **item_sector_context,
                },
            )
            decision["score"] = round(float(getattr(item, "strategic_score", 0.0)), 2)
            decision["dominant_narrative"] = narrative.dominant_narrative
            decision["active_narratives"] = [item.narrative for item in narrative.active_narratives]
            decision["narrative_strength"] = narrative.narrative_strength
            decision["narrative_phase"] = narrative.narrative_phase
            decision["narrative_consistency"] = narrative.consistency
            decision["supporting_themes"] = narrative.supporting_themes
            decision["macro_cycle"] = cycle_state.macro_cycle
            decision["liquidity_cycle"] = cycle_state.liquidity_cycle
            decision["sentiment_cycle"] = cycle_state.sentiment_cycle
            decision["industry_cycle"] = cycle_state.industry_cycle
            decision["risk_appetite"] = cycle_state.risk_appetite
            decision["combined_cycle_state"] = cycle_state.combined_cycle_state
            decision["cycle_aggressiveness"] = cycle_state.aggressiveness
            decision["capital_flow_score"] = sector_flow.flow_score if sector_flow else 0.0
            decision["capital_flow_direction"] = sector_flow.direction if sector_flow else "UNKNOWN"
            decision["leader_concentration"] = sector_flow.leader_concentration if sector_flow else 0.0
            decision["rotation_path"] = capital_flow_analysis.rotation_path
            decision["cycle_state"] = {
                "liquidity_cycle": cycle_state.liquidity_cycle,
                "sentiment_cycle": cycle_state.sentiment_cycle,
                "industry_cycle": cycle_state.industry_cycle,
                "combined_cycle_state": cycle_state.combined_cycle_state,
                "risk_appetite": cycle_state.risk_appetite,
                "aggressiveness": cycle_state.aggressiveness,
                "liquidity_score": cycle_state.liquidity_score,
                "fear_index": cycle_state.fear_index,
                "industry_growth": cycle_state.industry_growth,
                "valuation_score": cycle_state.valuation_score,
            }
            raw_decisions.append(decision)

        capital_decisions = self.capital_control.apply_constraints(raw_decisions)
        capital_state = self.capital_control.build_capital_state(
            capital_decisions,
            cycle_state=raw_decisions[0].get("cycle_state") if raw_decisions else {},
        )
        v11_decisions = [
            self.v11_orchestrator.run(
                decision,
                regime_result,
                agent_performance_log=self._agent_performance_from_decisions(capital_decisions, regime_result.regime),
            )
            for decision in capital_decisions
        ]
        market_state = {
            "regime": market_structure.regime,
            "structure": market_structure,
            "capital_flow": capital_flow_analysis,
            "narrative": narrative,
            "cycle": cycle_state,
            "regime_result": regime_result,
            "sector_dashboard": self.sector_engine.sector_dashboard(),
            "rotation_path": capital_flow_analysis.rotation_path,
            "dominant_narrative": narrative.dominant_narrative,
            "narrative_strength": narrative.narrative_strength,
            "narrative_phase": narrative.narrative_phase,
        }
        return V12OrchestrationResult(
            market_state=market_state,
            capital_state={
                "exposure": capital_state.exposure,
                "risk_score": capital_state.risk_score,
                "rebalance_signals": capital_state.rebalance_signals,
                "capital_bias": capital_state.capital_bias,
                "allocation_ceiling": capital_state.allocation_ceiling,
                "exposure_breadth": capital_state.exposure_breadth,
                "reason": capital_state.reason,
            },
            decisions=capital_decisions,
            v11_decisions=v11_decisions,
            sector_engine=self.sector_engine,
            regime_result=regime_result,
        )

    @staticmethod
    def _confidence_from_result(result: Any) -> float:
        breakdown = getattr(result, "factor_breakdown", {}) or {}
        value = breakdown.get("final_confidence", breakdown.get("confidence_score", 0.0))
        try:
            confidence = float(value)
        except Exception:
            confidence = 0.0
        if confidence > 1.0:
            confidence /= 100.0
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _market_snapshot(results: list[Any]) -> dict[str, float]:
        scores = [float(getattr(item, "strategic_score", 0.0)) for item in results]
        confidences = [MainOrchestrator._confidence_from_result(item) for item in results]
        if not scores:
            return {"trend": 0.0, "volatility": 1.0, "price_momentum": 0.0}
        top_score = max(scores)
        score_spread = max(scores) - min(scores)
        avg_conf = mean(confidences) if confidences else 0.0
        trend = max(0.0, min(1.0, top_score / 100.0))
        volatility = max(0.0, min(1.0, score_spread / 100.0 + (1.0 - avg_conf) * 0.35))
        momentum = max(0.0, min(1.0, (top_score - mean(scores)) / 100.0 + avg_conf * 0.30))
        return {"trend": trend, "volatility": volatility, "price_momentum": momentum}

    @staticmethod
    def _sector_flow_inputs(sector_engine: V10SectorEngine) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
        volume: dict[str, float] = {}
        inflow: dict[str, float] = {}
        outflow: dict[str, float] = {}
        leader_volume: dict[str, float] = {}
        for row in sector_engine.sector_dashboard():
            sector = str(row["sector"])
            strength = float(row["sector_strength"])
            sector_volume = round(100.0 * max(strength, 0.05), 4)
            volume[sector] = sector_volume
            inflow[sector] = round(sector_volume * strength, 4)
            outflow[sector] = round(sector_volume * max(0.0, 1.0 - strength), 4)
            leader_volume[sector] = round(sector_volume * (0.35 + 0.40 * strength), 4)
        return volume, inflow, outflow, leader_volume

    @staticmethod
    def _cycle_inputs(
        market_structure: Any,
        capital_flow_analysis: Any,
        narrative: Any,
        sector_engine: V10SectorEngine,
        ranked_results: list[Any],
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        flow_strength_map = {"STRONG": 0.90, "MEDIUM": 0.65, "WEAK": 0.35}
        liquidity_score = max(
            0.0,
            min(
                1.0,
                0.45 * flow_strength_map.get(str(capital_flow_analysis.flow_strength), 0.35)
                + 0.35 * (1.0 - float(getattr(market_structure, "volatility", 0.0) or 0.0))
                + 0.20 * float(getattr(market_structure, "structure_strength", 0.5) or 0.5),
            ),
        )
        fear_index = max(
            0.0,
            min(
                100.0,
                100.0
                * (
                    0.60 * float(getattr(market_structure, "volatility", 0.0) or 0.0)
                    + 0.40 * (1.0 - float(getattr(narrative, "narrative_strength", 0.0) or 0.0))
                ),
            ),
        )
        avg_sector_strength = sum(float(value) for value in sector_engine.sector_scores.values()) / max(
            len(sector_engine.sector_scores), 1
        )
        sector_growth = max(
            0.0,
            min(1.0, 0.55 * avg_sector_strength + 0.45 * float(getattr(narrative, "narrative_strength", 0.0) or 0.0)),
        )
        avg_score = sum(float(getattr(item, "strategic_score", 0.0)) for item in ranked_results) / max(len(ranked_results), 1)
        valuation_score = max(0.0, min(1.0, 1.0 - (avg_score / 100.0)))
        return (
            {"liquidity_score": round(liquidity_score, 4)},
            {"fear_index": round(fear_index, 2)},
            {"industry_growth": round(sector_growth, 4), "valuation_score": round(valuation_score, 4)},
        )

    @staticmethod
    def _agent_performance_from_decisions(decisions: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for decision in decisions:
            action = str(decision.get("action", "OBSERVE"))
            risk_score = float(decision.get("risk_score", 0.0) or 0.0)
            sector_strength = float(decision.get("sector_strength", 0.0) or 0.0)
            confidence = float(decision.get("confidence", 0.0) or 0.0)

            records.append(
                {
                    "agent_name": "AlphaAgent",
                    "outcome": "WIN" if action in {"ADD", "SMALL_ADD", "HOLD"} and confidence >= 0.5 else "LOSS",
                    "pnl_contribution": 0.04 if action in {"ADD", "SMALL_ADD"} else 0.01,
                }
            )
            records.append(
                {
                    "agent_name": "RiskAgent",
                    "outcome": "WIN" if risk_score <= 0.7 or regime in {"BEAR", "DEFENSIVE"} else "LOSS",
                    "pnl_contribution": 0.03 if regime in {"BEAR", "DEFENSIVE"} else 0.0,
                }
            )
            records.append(
                {
                    "agent_name": "SectorAgent",
                    "outcome": "WIN" if sector_strength >= 0.5 else "LOSS",
                    "pnl_contribution": 0.02 if sector_strength >= 0.75 else 0.0,
                }
            )
            records.append(
                {
                    "agent_name": "MacroAgent",
                    "outcome": "WIN" if regime in {"BULL", "STRUCTURAL", "ROTATION", "BEAR"} else "LOSS",
                    "pnl_contribution": 0.01,
                }
            )
            records.append(
                {
                    "agent_name": "PortfolioAgent",
                    "outcome": "WIN" if action in {"HOLD", "OBSERVE", "ADD", "SMALL_ADD"} else "LOSS",
                    "pnl_contribution": 0.01,
                }
            )
        return records

    @staticmethod
    def _regime_adapter(market_structure: Any) -> Any:
        class _Adapter:
            def __init__(self, structure: Any) -> None:
                self.regime = structure.regime
                self.trend = structure.trend
                self.volatility = structure.volatility
                self.confidence = structure.confidence
                self.reason = structure.reason

        return _Adapter(market_structure)
