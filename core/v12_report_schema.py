"""Unified schema for V12 research outputs.

This layer standardizes the output of the V12 research stack into a single
deterministic schema that is suitable for dashboard rendering and API
transport.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class V12MarketStateSchema:
    structure: float = 0.5
    flow: float = 0.5
    narrative: float = 0.5
    cycle: float = 0.5


@dataclass(frozen=True)
class V12CapitalStateSchema:
    risk_level: float = 0.5
    exposure: float = 0.5


@dataclass(frozen=True)
class V12PerformanceSchema:
    return_value: float = 0.5
    drawdown: float = 0.5
    win_rate: float = 0.5

    def to_dict(self) -> dict[str, float]:
        """Return the schema using the mandated field names."""

        return {
            "return": self.return_value,
            "drawdown": self.drawdown,
            "win_rate": self.win_rate,
        }


@dataclass(frozen=True)
class V12SystemHealthSchema:
    stability: float = 0.5
    overfitting_risk: float = 0.5
    data_quality: float = 0.5


@dataclass(frozen=True)
class V12DecisionSchema:
    action: str = "HOLD"
    confidence: float = 0.3
    risk_level: str = "MEDIUM"


@dataclass(frozen=True)
class V12ExplanationSchema:
    key_factors: Sequence[str] = field(default_factory=tuple)
    dominant_driver: str = "neutral fallback"


@dataclass(frozen=True)
class V12ReportSchema:
    """Canonical V12 research report payload."""

    market_state: V12MarketStateSchema = field(default_factory=V12MarketStateSchema)
    capital_state: V12CapitalStateSchema = field(default_factory=V12CapitalStateSchema)
    performance: V12PerformanceSchema = field(default_factory=V12PerformanceSchema)
    system_health: V12SystemHealthSchema = field(default_factory=V12SystemHealthSchema)
    decision: V12DecisionSchema = field(default_factory=V12DecisionSchema)
    explanation: V12ExplanationSchema = field(default_factory=V12ExplanationSchema)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the mandatory plain dictionary representation."""

        return {
            "market_state": asdict(self.market_state),
            "capital_state": asdict(self.capital_state),
            "performance": self.performance.to_dict(),
            "system_health": asdict(self.system_health),
            "decision": asdict(self.decision),
            "explanation": {
                "key_factors": list(self.explanation.key_factors),
                "dominant_driver": self.explanation.dominant_driver,
            },
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "V12ReportSchema":
        """Build a schema instance from a normalized mapping."""

        market_state = payload.get("market_state", {})
        capital_state = payload.get("capital_state", {})
        performance = payload.get("performance", {})
        system_health = payload.get("system_health", {})
        decision = payload.get("decision", {})
        explanation = payload.get("explanation", {})
        return cls(
            market_state=V12MarketStateSchema(
                structure=float(market_state.get("structure", 0.5)),
                flow=float(market_state.get("flow", 0.5)),
                narrative=float(market_state.get("narrative", 0.5)),
                cycle=float(market_state.get("cycle", 0.5)),
            ),
            capital_state=V12CapitalStateSchema(
                risk_level=float(capital_state.get("risk_level", 0.5)),
                exposure=float(capital_state.get("exposure", 0.5)),
            ),
            performance=V12PerformanceSchema(
                return_value=float(performance.get("return", 0.5)),
                drawdown=float(performance.get("drawdown", 0.5)),
                win_rate=float(performance.get("win_rate", 0.5)),
            ),
            system_health=V12SystemHealthSchema(
                stability=float(system_health.get("stability", 0.5)),
                overfitting_risk=float(system_health.get("overfitting_risk", 0.5)),
                data_quality=float(system_health.get("data_quality", 0.5)),
            ),
            decision=V12DecisionSchema(
                action=str(decision.get("action", "HOLD")),
                confidence=float(decision.get("confidence", 0.3)),
                risk_level=str(decision.get("risk_level", "MEDIUM")),
            ),
            explanation=V12ExplanationSchema(
                key_factors=tuple(explanation.get("key_factors", [])),
                dominant_driver=str(explanation.get("dominant_driver", "neutral fallback")),
            ),
        )

