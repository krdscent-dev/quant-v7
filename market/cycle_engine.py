"""Detect macro and liquidity cycle state for V12."""

from __future__ import annotations

from dataclasses import dataclass

from market.market_structure_engine import MarketStructure


@dataclass(frozen=True)
class CycleState:
    macro_cycle: str
    liquidity_cycle: str
    risk_appetite: str
    reason: str


class CycleEngine:
    """Translate market structure into cycle and risk-appetite context."""

    def detect(self, market_structure: MarketStructure) -> CycleState:
        if market_structure.regime == "BULL":
            return CycleState(
                macro_cycle="EXPANSION",
                liquidity_cycle="EASING_OR_SUPPORTIVE",
                risk_appetite="RISING",
                reason="Bull structure supports higher risk appetite.",
            )
        if market_structure.regime == "BEAR":
            return CycleState(
                macro_cycle="CONTRACTION_OR_STRESS",
                liquidity_cycle="TIGHT_OR_UNCERTAIN",
                risk_appetite="FALLING",
                reason="Bear structure requires defensive sizing and stricter validation.",
            )
        return CycleState(
            macro_cycle="MID_CYCLE",
            liquidity_cycle="NEUTRAL",
            risk_appetite="SELECTIVE",
            reason="Range structure favors rotation and selective opportunities.",
        )
