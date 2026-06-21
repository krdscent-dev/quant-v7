"""V11 multi-agent investment organization.

Agents wrap existing V10 engines into an institutional-style workflow. No
single agent can make the final decision; PortfolioAgent combines inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from agents.adaptive_governor import AdaptiveGovernor
from agents.agent_lifecycle_manager import AgentLifecycleManager
from agents.agent_performance_tracker import AgentPerformanceTracker
from agents.decision_arbitrator import DecisionArbitrator
from agents.weight_manager import AgentWeightManager
from core.v10_audit_engine import V10AuditEngine
from core.v10_portfolio_autopilot import V10PortfolioAutopilot
from core.v10_sector_engine import V10SectorEngine


@dataclass(frozen=True)
class AgentOutput:
    agent_name: str
    symbol: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


class MacroAgent:
    """Determine market regime."""

    def evaluate(self, regime_result: Any) -> AgentOutput:
        return AgentOutput(
            agent_name="MacroAgent",
            symbol="MARKET",
            payload={
                "macro_regime": str(getattr(regime_result, "regime", regime_result)),
                "trend": float(getattr(regime_result, "trend", 0.0)),
                "volatility": float(getattr(regime_result, "volatility", 0.0)),
                "confidence": float(getattr(regime_result, "confidence", 0.0)),
            },
        )


class SectorAgent:
    """Evaluate sector context and leadership."""

    def __init__(self, sector_engine: V10SectorEngine) -> None:
        self.sector_engine = sector_engine
        self.context = sector_engine.build_sector_context()

    def evaluate(self, symbol: str) -> AgentOutput:
        context = dict(self.context.get(str(symbol), {}))
        return AgentOutput(
            agent_name="SectorAgent",
            symbol=str(symbol),
            payload={
                "sector": context.get("sector", "UNKNOWN"),
                "sector_strength": float(context.get("sector_strength", 0.0)),
                "sector_leader_flag": bool(context.get("sector_leader_flag", False)),
                "sector_rank": int(context.get("sector_rank", 99)),
                "rotation_signal": context.get("rotation_signal", "UNKNOWN"),
            },
        )


class AlphaAgent:
    """Suggest opportunities, but never makes final decisions."""

    def evaluate(self, decision: Mapping[str, Any]) -> AgentOutput:
        action = str(decision.get("action", "OBSERVE"))
        chain = list(decision.get("causal_chain", []))
        sector_strength = float(decision.get("sector_strength", 0.0) or 0.0)
        confidence = float(decision.get("confidence", 0.0) or 0.0)
        action_bonus = 0.20 if action in {"SMALL_ADD", "ADD"} else 0.10 if action == "HOLD" else 0.0
        chain_bonus = min(len(chain), 5) * 0.08
        alpha_score = max(0.0, min(1.0, 0.35 * sector_strength + chain_bonus + action_bonus + 0.15 * confidence))
        return AgentOutput(
            agent_name="AlphaAgent",
            symbol=str(decision.get("symbol", "UNKNOWN")),
            payload={
                "alpha_score": round(alpha_score, 2),
                "suggested_action": action,
                "causal_chain": chain,
                "bottleneck_node": decision.get("bottleneck_node", "NONE"),
            },
        )


class RiskAgent:
    """Control exposure and risk limits. It can reduce but not generate trades."""

    def evaluate(self, decision: Mapping[str, Any]) -> AgentOutput:
        risk_score = float(decision.get("risk_score", 0.0) or 0.0)
        exposure = float(decision.get("portfolio_exposure", 0.0) or 0.0)
        risk_action = "REDUCE" if exposure > 0.35 or risk_score > 0.70 else "ALLOW"
        return AgentOutput(
            agent_name="RiskAgent",
            symbol=str(decision.get("symbol", "UNKNOWN")),
            payload={
                "risk_score": round(risk_score, 2),
                "portfolio_exposure": round(exposure, 2),
                "risk_action": risk_action,
                "risk_reason": "Exposure/risk within limits." if risk_action == "ALLOW" else "Risk limit requires reduction.",
            },
        )


class PortfolioAgent:
    """Make final allocation from all agent inputs."""

    def evaluate(
        self,
        base_decision: Mapping[str, Any],
        macro: AgentOutput,
        sector: AgentOutput,
        alpha: AgentOutput,
        risk: AgentOutput,
    ) -> AgentOutput:
        action = str(base_decision.get("action", "OBSERVE"))
        alpha_score = float(alpha.payload["alpha_score"])
        risk_score = float(risk.payload["risk_score"])
        regime = str(macro.payload["macro_regime"])
        sector_strength = float(sector.payload["sector_strength"])

        if risk.payload["risk_action"] == "REDUCE":
            final_action = "REDUCE"
            allocation = 0.0
        elif action in {"SMALL_ADD", "ADD"} and alpha_score >= 0.70 and regime != "BEAR":
            final_action = "ADD"
            allocation = 0.08
        elif action in {"SMALL_ADD", "ADD"} and alpha_score >= 0.60:
            final_action = "SMALL_ADD"
            allocation = 0.03
        elif action == "HOLD" or sector_strength >= 0.75:
            final_action = "HOLD"
            allocation = 0.0
        else:
            final_action = "OBSERVE"
            allocation = 0.0

        risk_adjusted = max(0.0, allocation * (1.0 - risk_score))
        return AgentOutput(
            agent_name="PortfolioAgent",
            symbol=str(base_decision.get("symbol", "UNKNOWN")),
            payload={
                "final_action": final_action,
                "final_allocation": round(risk_adjusted, 4),
                "consensus_basis": {
                    "macro_regime": regime,
                    "alpha_score": round(alpha_score, 2),
                    "risk_score": round(risk_score, 2),
                    "sector_strength": round(sector_strength, 2),
                },
            },
        )


class AuditAgent:
    """Log every multi-agent decision."""

    def __init__(self, audit_engine: V10AuditEngine) -> None:
        self.audit_engine = audit_engine

    def log(self, symbol: str, outputs: list[AgentOutput]) -> dict[str, Any]:
        payload = {
            "symbol": symbol,
            "agents": {item.agent_name: item.payload for item in outputs},
        }
        return self.audit_engine.log_event("V11_AGENT_DECISION", payload)


class V11AgentOrchestrator:
    """Run V11 consensus workflow for final decisions."""

    def __init__(self, sector_engine: V10SectorEngine, audit_engine: V10AuditEngine) -> None:
        self.macro_agent = MacroAgent()
        self.sector_agent = SectorAgent(sector_engine)
        self.alpha_agent = AlphaAgent()
        self.risk_agent = RiskAgent()
        self.portfolio_agent = PortfolioAgent()
        self.decision_arbitrator = DecisionArbitrator()
        self.performance_tracker = AgentPerformanceTracker()
        self.weight_manager = AgentWeightManager()
        self.adaptive_governor = AdaptiveGovernor()
        self.lifecycle_manager = AgentLifecycleManager()
        self.audit_agent = AuditAgent(audit_engine)

    def run(
        self,
        decision: Mapping[str, Any],
        regime_result: Any,
        agent_performance_log: list[Mapping[str, object]] | None = None,
    ) -> dict[str, Any]:
        symbol = str(decision.get("symbol", "UNKNOWN"))
        macro = self.macro_agent.evaluate(regime_result)
        sector = self.sector_agent.evaluate(symbol)
        alpha = self.alpha_agent.evaluate({**decision, **sector.payload})
        risk = self.risk_agent.evaluate(decision)
        portfolio = self.portfolio_agent.evaluate(decision, macro, sector, alpha, risk)
        agent_payloads = {
            "MacroAgent": macro.payload,
            "SectorAgent": sector.payload,
            "AlphaAgent": alpha.payload,
            "RiskAgent": risk.payload,
            "PortfolioAgent": portfolio.payload,
        }
        performance_summary = self.performance_tracker.summarize(agent_performance_log)
        current_weights = self.weight_manager.update_weights(performance_summary)
        regime_adjusted_weights = self.adaptive_governor.adjust_for_regime(
            current_weights,
            str(macro.payload["macro_regime"]),
        )
        lifecycle_result = self.lifecycle_manager.evaluate(performance_summary, regime_adjusted_weights)
        arbitration = self.decision_arbitrator.arbitrate(
            agent_payloads,
            agent_weights=regime_adjusted_weights,
        )
        arbitrator_output = AgentOutput(
            agent_name="DecisionArbitrator",
            symbol=symbol,
            payload=arbitration,
        )
        audit_record = self.audit_agent.log(symbol, [macro, sector, alpha, risk, portfolio, arbitrator_output])
        return {
            "symbol": symbol,
            "alpha_score": alpha.payload["alpha_score"],
            "risk_score": risk.payload["risk_score"],
            "macro_regime": macro.payload["macro_regime"],
            "market_intelligence": {
                "dominant_narrative": decision.get("dominant_narrative", "UNKNOWN"),
                "active_narratives": decision.get("active_narratives", []),
                "narrative_strength": decision.get("narrative_strength", 0.0),
                "narrative_phase": decision.get("narrative_phase", "UNKNOWN"),
                "narrative_consistency": decision.get("narrative_consistency", "UNKNOWN"),
                "macro_cycle": decision.get("macro_cycle", "UNKNOWN"),
                "liquidity_cycle": decision.get("liquidity_cycle", "UNKNOWN"),
                "risk_appetite": decision.get("risk_appetite", "UNKNOWN"),
                "capital_flow_score": decision.get("capital_flow_score", 0.0),
                "capital_flow_direction": decision.get("capital_flow_direction", "UNKNOWN"),
                "leader_concentration": decision.get("leader_concentration", 0.0),
                "rotation_path": decision.get("rotation_path", []),
            },
            "sector_context": sector.payload,
            "agent_opinions": arbitration["agent_opinions"],
            "current_agent_weights": current_weights,
            "regime_adjusted_weights": regime_adjusted_weights,
            "conflict_detected": arbitration["conflict_detected"],
            "final_action": arbitration["final_decision"],
            "final_allocation": arbitration["final_allocation"],
            "final_weighted_decision": arbitration["final_decision"],
            "arbitration_reason": arbitration["arbitration_reason"],
            "agent_performance_summary": {
                agent: {
                    "accuracy": item.accuracy,
                    "pnl_contribution": item.pnl_contribution,
                    "sample_count": item.sample_count,
                }
                for agent, item in performance_summary.items()
            },
            "active_agents": lifecycle_result.active_agents,
            "removed_agents": lifecycle_result.removed_agents,
            "newly_created_agents": lifecycle_result.newly_created_agents,
            "promoted_agents": lifecycle_result.promoted_agents,
            "agent_performance_scores": lifecycle_result.performance_scores,
            "structural_changes": lifecycle_result.structural_changes,
            "audit_trail": {
                "event_type": audit_record["event_type"],
                "timestamp": audit_record["timestamp"],
                "agents": lifecycle_result.active_agents,
            },
        }
