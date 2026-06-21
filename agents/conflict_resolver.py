"""Conflict detection and weighted resolution for V11.1 agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ACTION_SCORE = {
    "REDUCE": -1.0,
    "OBSERVE": -0.3,
    "HOLD": 0.0,
    "SMALL_ADD": 0.5,
    "ADD": 0.8,
    "BUY": 1.0,
    "ALLOW": 0.0,
}

AGENT_WEIGHTS = {
    "RiskAgent": 0.40,
    "AlphaAgent": 0.30,
    "MacroAgent": 0.15,
    "SectorAgent": 0.10,
    "PortfolioAgent": 0.05,
}


@dataclass(frozen=True)
class ConflictResolution:
    """Conflict status and weighted arbitration output."""

    conflict_detected: bool
    final_decision: str
    arbitration_score: float
    arbitration_reason: str
    agent_opinions: dict[str, str]


class ConflictResolver:
    """Detect conflicts and resolve them using weighted arbitration."""

    def detect_conflicts(self, agent_opinions: Mapping[str, str]) -> list[str]:
        conflicts: list[str] = []
        alpha = agent_opinions.get("AlphaAgent", "HOLD")
        risk = agent_opinions.get("RiskAgent", "ALLOW")
        macro = agent_opinions.get("MacroAgent", "HOLD")
        sector = agent_opinions.get("SectorAgent", "HOLD")

        if alpha in {"BUY", "ADD", "SMALL_ADD"} and risk == "REDUCE":
            conflicts.append("Alpha suggests risk-on while Risk requires REDUCE.")
        if macro == "HOLD" and sector in {"ADD", "BUY", "SMALL_ADD"}:
            conflicts.append("Macro says HOLD while Sector suggests risk-on.")
        if "REDUCE" in agent_opinions.values() and any(
            value in {"ADD", "BUY", "SMALL_ADD"} for value in agent_opinions.values()
        ):
            conflicts.append("Risk-off and risk-on opinions coexist.")
        return conflicts

    def resolve(
        self,
        agent_payloads: Mapping[str, Mapping[str, Any]],
        agent_weights: Mapping[str, float] | None = None,
    ) -> ConflictResolution:
        opinions = self._extract_opinions(agent_payloads)
        conflicts = self.detect_conflicts(opinions)
        weights = dict(agent_weights or AGENT_WEIGHTS)
        score = 0.0
        for agent, opinion in opinions.items():
            score += weights.get(agent, 0.0) * ACTION_SCORE.get(opinion, 0.0)

        if score >= 0.45:
            decision = "ADD"
        elif score >= 0.20:
            decision = "SMALL_ADD"
        elif score > -0.20:
            decision = "HOLD"
        else:
            decision = "REDUCE"

        if conflicts and abs(score) < 0.20:
            decision = "HOLD"
            reason = "Conflict unresolved by weighted score; HOLD fallback applied."
        elif conflicts:
            reason = f"Conflict resolved by weighted arbitration score {score:.2f}."
        else:
            reason = f"No material conflict; weighted arbitration score {score:.2f}."

        return ConflictResolution(
            conflict_detected=bool(conflicts),
            final_decision=decision,
            arbitration_score=round(score, 4),
            arbitration_reason=reason,
            agent_opinions=opinions,
        )

    def _extract_opinions(self, agent_payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
        macro_regime = str(agent_payloads.get("MacroAgent", {}).get("macro_regime", "HOLD"))
        sector_strength = float(agent_payloads.get("SectorAgent", {}).get("sector_strength", 0.0) or 0.0)
        alpha_action = str(agent_payloads.get("AlphaAgent", {}).get("suggested_action", "HOLD"))
        risk_action = str(agent_payloads.get("RiskAgent", {}).get("risk_action", "ALLOW"))
        portfolio_action = str(agent_payloads.get("PortfolioAgent", {}).get("final_action", "HOLD"))

        macro_opinion = "REDUCE" if macro_regime in {"BEAR", "DEFENSIVE"} else "HOLD"
        if macro_regime in {"BULL", "STRUCTURAL"}:
            macro_opinion = "ADD"

        if sector_strength > 0.75:
            sector_opinion = "SMALL_ADD"
        elif sector_strength >= 0.50:
            sector_opinion = "HOLD"
        else:
            sector_opinion = "REDUCE"

        return {
            "RiskAgent": risk_action,
            "AlphaAgent": alpha_action,
            "MacroAgent": macro_opinion,
            "SectorAgent": sector_opinion,
            "PortfolioAgent": portfolio_action,
        }
