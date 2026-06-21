"""Circuit breaker rules for V12.9."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CircuitBreakerDecision:
    """Final gate applied before execution."""

    final_allowed_action: str
    reason: str
    override: bool
    warnings: list[str]


class CircuitBreaker:
    """Override all decisions under unstable or stressed conditions."""

    def decide(
        self,
        stability_report: Mapping[str, object],
        latency_report: Mapping[str, object],
        stress_report: Mapping[str, object],
    ) -> CircuitBreakerDecision:
        stability_status = str(stability_report.get("status", "WARNING"))
        latency_status = str(latency_report.get("status", "HIGH_LATENCY"))
        sync_status = str(latency_report.get("synchronization_status", "DESYNCED"))
        stress_state = str(stress_report.get("state", "ELEVATED"))
        stress_score = float(stress_report.get("stress_score", 0.0) or 0.0)

        warnings: list[str] = []
        if stress_state == "EXTREME" or stability_status == "UNSTABLE" or sync_status == "DESYNCED":
            warnings.append("circuit_breaker_triggered")
            return CircuitBreakerDecision(
                final_allowed_action="STOP",
                reason="Extreme stress or unstable synchronization detected; trading halted.",
                override=True,
                warnings=warnings,
            )
        if stress_state == "ELEVATED" or latency_status == "HIGH_LATENCY" or stability_status == "WARNING":
            warnings.append("circuit_breaker_degraded_mode")
            return CircuitBreakerDecision(
                final_allowed_action="REDUCE",
                reason="Stress elevated; trading size should be reduced.",
                override=True,
                warnings=warnings,
            )
        if stress_score >= 0.35:
            warnings.append("circuit_breaker_observe_mode")
            return CircuitBreakerDecision(
                final_allowed_action="REDUCE",
                reason="Stress above baseline; conservative mode applied.",
                override=False,
                warnings=warnings,
            )
        return CircuitBreakerDecision(
            final_allowed_action="ALLOW",
            reason="System is stable and synchronized; trading may proceed.",
            override=False,
            warnings=warnings,
        )

