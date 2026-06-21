"""V12.5 capital control layer.

This layer computes portfolio-level position and risk constraints only. It does
not select stocks or generate alpha; it only shapes sizing and exposure before
the V11 decision system consumes the inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from core.v10_portfolio_autopilot import V10PortfolioAutopilot


@dataclass(frozen=True)
class CapitalControlState:
    """Portfolio-level capital state for one orchestration run."""

    exposure: dict[str, float]
    risk_score: float
    rebalance_signals: dict[str, str]
    capital_bias: str
    allocation_ceiling: float
    exposure_breadth: int
    reason: str


class V125CapitalControlEngine:
    """Compute capital constraints from already-ranked decisions."""

    def __init__(self, autopilot: V10PortfolioAutopilot | None = None) -> None:
        self.autopilot = autopilot or V10PortfolioAutopilot()

    def apply_constraints(self, decisions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Apply portfolio-level constraints without changing stock selection."""

        return self.autopilot.apply_constraints(decisions)

    def build_capital_state(
        self,
        decisions: Iterable[Mapping[str, Any]],
        cycle_state: Mapping[str, Any] | None = None,
    ) -> CapitalControlState:
        """Summarize exposure and risk limits for the current portfolio view."""

        rows = [dict(item) for item in decisions]
        exposure = self.autopilot.calculate_exposure(rows)
        risk_score = self.autopilot.risk_score(exposure)
        rebalance_signals = self.autopilot.rebalance_signal(exposure)
        cycle_state = dict(cycle_state or {})
        risk_appetite = str(cycle_state.get("risk_appetite", "SELECTIVE"))
        capital_bias = self._capital_bias(risk_appetite, risk_score)
        allocation_ceiling = self._allocation_ceiling(risk_appetite, risk_score)
        reason = (
            f"risk_appetite={risk_appetite}; risk_score={risk_score:.2f}; "
            f"exposure_max={max(exposure.values()) if exposure else 0.0:.2f}."
        )
        return CapitalControlState(
            exposure=exposure,
            risk_score=risk_score,
            rebalance_signals=rebalance_signals,
            capital_bias=capital_bias,
            allocation_ceiling=allocation_ceiling,
            exposure_breadth=len(exposure),
            reason=reason,
        )

    @staticmethod
    def _capital_bias(risk_appetite: str, risk_score: float) -> str:
        if risk_appetite in {"RISING", "AGGRESSIVE"} and risk_score < 0.45:
            return "EXPANSIVE"
        if risk_appetite in {"FALLING", "DEFENSIVE"} or risk_score > 0.70:
            return "DEFENSIVE"
        return "BALANCED"

    @staticmethod
    def _allocation_ceiling(risk_appetite: str, risk_score: float) -> float:
        if risk_appetite in {"RISING", "AGGRESSIVE"} and risk_score < 0.45:
            return 0.15
        if risk_appetite in {"FALLING", "DEFENSIVE"} or risk_score > 0.70:
            return 0.05
        return 0.10
