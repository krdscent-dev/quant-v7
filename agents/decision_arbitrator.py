"""Final V11.1 decision aggregation layer."""

from __future__ import annotations

from typing import Any, Mapping

from agents.conflict_resolver import ConflictResolution, ConflictResolver


class DecisionArbitrator:
    """Produce one unified final decision from all agent outputs."""

    def __init__(self, resolver: ConflictResolver | None = None) -> None:
        self.resolver = resolver or ConflictResolver()

    def arbitrate(self, agent_payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        resolution: ConflictResolution = self.resolver.resolve(agent_payloads)
        risk_score = float(agent_payloads.get("RiskAgent", {}).get("risk_score", 0.0) or 0.0)
        allocation = self._allocation_for(resolution.final_decision, risk_score)
        return {
            "agent_opinions": resolution.agent_opinions,
            "conflict_detected": resolution.conflict_detected,
            "final_decision": resolution.final_decision,
            "final_allocation": allocation,
            "arbitration_score": resolution.arbitration_score,
            "arbitration_reason": resolution.arbitration_reason,
        }

    def _allocation_for(self, decision: str, risk_score: float) -> float:
        if decision == "ADD":
            base = 0.08
        elif decision == "SMALL_ADD":
            base = 0.03
        else:
            base = 0.0
        return round(max(0.0, base * (1.0 - risk_score)), 4)
