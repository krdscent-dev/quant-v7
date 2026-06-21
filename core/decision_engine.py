"""V10.4 risk-aware action decision layer.

The V10.4 flow is alpha-first, causal-aware, and sector-aware:
1. AlphaEngine checks selective opportunity.
2. CognitiveGraph context adjusts causal conviction.
3. SectorEngine context adjusts leadership bias.
4. Regime adjusts exposure intensity.
5. Confidence changes weight, not decision validity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.alpha_engine import AlphaEngine
from core.ial import InvestmentActionLanguage


@dataclass(frozen=True)
class DecisionOutput:
    """Action-based decision output."""

    symbol: str
    action: str
    confidence: float
    reason: str
    horizon: str
    sector: str
    sector_strength: float
    leader_flag: bool
    causal_chain: list[str]
    bottleneck_node: str


class DecisionEngine:
    """Convert score + alpha + sector + regime + confidence into an action."""

    def __init__(self, alpha_engine: AlphaEngine | None = None) -> None:
        self.alpha_engine = alpha_engine or AlphaEngine()

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _normalize_regime(self, regime: Any) -> str:
        if hasattr(regime, "regime"):
            return str(getattr(regime, "regime")).upper()
        return str(regime or "").upper()

    def _base_action(self, score: float) -> str:
        if score >= 80:
            return InvestmentActionLanguage.ADD.value
        if score >= 55:
            return InvestmentActionLanguage.HOLD.value
        if score >= 15:
            return InvestmentActionLanguage.OBSERVE.value
        return InvestmentActionLanguage.REDUCE.value

    def _apply_sector_intelligence(
        self,
        action: str,
        sector_strength: float,
        leader_flag: bool,
        sector_rank: int,
        sector: str,
    ) -> tuple[str, str]:
        """Apply V10.3 sector leadership rules before regime sizing."""

        if sector in {"UNKNOWN", ""} or sector_strength <= 0.0:
            return action, " Sector context unavailable; action unchanged."

        if sector_strength > 0.75:
            if leader_flag:
                return (
                    InvestmentActionLanguage.ADD.value,
                    " Sector leadership bias: strong sector leader upgraded to ADD before regime sizing.",
                )
            if sector_rank == 2:
                return (
                    InvestmentActionLanguage.HOLD.value,
                    " Sector leadership bias: second-ranked sector name held for confirmation.",
                )
            if action == InvestmentActionLanguage.REDUCE.value:
                return (
                    InvestmentActionLanguage.OBSERVE.value,
                    " Strong sector breadth prevents automatic reduction.",
                )
            return action, " Strong sector context retained."

        if 0.50 <= sector_strength <= 0.75:
            if action in {
                InvestmentActionLanguage.ADD.value,
                InvestmentActionLanguage.SMALL_ADD.value,
            }:
                return InvestmentActionLanguage.HOLD.value, " Mid-strength sector caps action at HOLD."
            if action == InvestmentActionLanguage.REDUCE.value:
                return InvestmentActionLanguage.OBSERVE.value, " Mid-strength sector uses OBSERVE instead of REDUCE."
            return action, " Mid-strength sector requires confirmation."

        if action in {
            InvestmentActionLanguage.ADD.value,
            InvestmentActionLanguage.SMALL_ADD.value,
            InvestmentActionLanguage.HOLD.value,
        }:
            return InvestmentActionLanguage.OBSERVE.value, " Weak sector context downgrades action to OBSERVE."
        return action, " Weak sector context limits alpha deployment."

    def _apply_cognitive_intelligence(
        self,
        action: str,
        chain_strength: str,
        causal_chain: list[str],
        bottleneck_node: str,
        score: float,
        has_cognitive_context: bool,
    ) -> tuple[str, str]:
        """Apply V10.4 causal chain rules before sector leadership rules."""

        if not has_cognitive_context:
            return action, " Cognitive graph context unavailable; action unchanged."

        if not causal_chain or chain_strength == "NONE":
            if score >= 15:
                return InvestmentActionLanguage.OBSERVE.value, " No causal structure found; defaulting to OBSERVE."
            return InvestmentActionLanguage.REDUCE.value, " No causal structure found; low score keeps REDUCE."

        if chain_strength == "STRONG":
            if bottleneck_node != "NONE" and "Revenue Conversion" not in causal_chain[-1]:
                return (
                    InvestmentActionLanguage.HOLD.value,
                    f" Strong causal chain exists but bottleneck remains at {bottleneck_node}.",
                )
            return (
                InvestmentActionLanguage.ADD.value,
                " Strong causal chain supports ADD before sector and regime sizing.",
            )

        if chain_strength == "PARTIAL":
            return (
                InvestmentActionLanguage.HOLD.value,
                " Partial causal chain supports HOLD while waiting for missing validation.",
            )

        return action, " Causal chain does not change action."

    def _apply_regime(self, action: str, regime: str) -> str:
        if regime == "BEAR":
            if action in {"BUY", "ADD"}:
                return InvestmentActionLanguage.SMALL_ADD.value
            if action == "EXIT":
                return InvestmentActionLanguage.REDUCE.value
            return action
        if regime == "DEFENSIVE":
            if action == "BUY":
                return InvestmentActionLanguage.ADD.value
            if action == "ADD":
                return InvestmentActionLanguage.SMALL_ADD.value
            return action
        return action

    def _apply_confidence(self, action: str, confidence: float) -> str:
        if confidence < 0.20:
            if action == "HOLD":
                return InvestmentActionLanguage.OBSERVE.value
        if confidence < 0.35 and action == "ADD":
            return InvestmentActionLanguage.SMALL_ADD.value
        return action

    def decide(
        self,
        symbol: str,
        score: float,
        regime: Any,
        confidence: float,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a standardized V10.3 action dictionary."""

        context = context or {}
        regime_name = self._normalize_regime(regime)
        score = max(0.0, min(100.0, float(score)))
        confidence = self._clamp(float(confidence))
        confidence = self._clamp(
            confidence * float(context.get("confidence_sensitivity", 1.0) or 1.0)
            + float(context.get("confidence_bias", 0.0) or 0.0)
        )
        sector = str(context.get("sector", "UNKNOWN"))
        sector_strength = self._clamp(float(context.get("sector_strength", 0.0) or 0.0))
        leader_flag = bool(context.get("sector_leader_flag", context.get("leader_flag", False)))
        causal_chain = [str(item) for item in context.get("causal_chain", [])]
        bottleneck_node = str(context.get("bottleneck_node", "NONE") or "NONE")
        chain_strength = str(context.get("chain_strength", "NONE") or "NONE").upper()
        has_cognitive_context = any(
            key in context for key in ("causal_chain", "bottleneck_node", "chain_strength")
        )
        try:
            sector_rank = int(context.get("sector_rank", 99))
        except Exception:
            sector_rank = 99

        alpha = self.alpha_engine.evaluate(
            score=score,
            confidence=confidence,
            regime=regime_name,
            context=context,
        )
        if alpha.has_alpha:
            action = alpha.action
            reason = alpha.reason
        else:
            action = self._base_action(score)
            reason = "Base action derived from score, with regime and confidence adjustments."

        action, cognitive_reason = self._apply_cognitive_intelligence(
            action=action,
            chain_strength=chain_strength,
            causal_chain=causal_chain,
            bottleneck_node=bottleneck_node,
            score=score,
            has_cognitive_context=has_cognitive_context,
        )
        reason = f"{reason}{cognitive_reason}"
        action, sector_reason = self._apply_sector_intelligence(
            action=action,
            sector_strength=sector_strength,
            leader_flag=leader_flag,
            sector_rank=sector_rank,
            sector=sector,
        )
        reason = f"{reason}{sector_reason}"
        action = self._apply_regime(action, regime_name)
        action = self._apply_confidence(action, confidence)
        if action == InvestmentActionLanguage.INVALIDATE.value:
            action = InvestmentActionLanguage.OBSERVE.value

        horizon = "mid"
        if action in {"REDUCE"}:
            horizon = "short"
        elif action == "OBSERVE":
            horizon = "short"

        risk_note = (
            f" Regime={regime_name}; confidence={confidence:.2f}; "
            f"alpha_strength={alpha.strength:.2f}; sector={sector}; "
            f"sector_strength={sector_strength:.2f}; leader={leader_flag}; "
            f"chain_strength={chain_strength}; bottleneck={bottleneck_node}."
        )
        output = DecisionOutput(
            symbol=str(symbol),
            action=action,
            confidence=round(confidence, 2),
            reason=f"{reason}{risk_note}",
            horizon=horizon,
            sector=sector,
            sector_strength=round(sector_strength, 2),
            leader_flag=leader_flag,
            causal_chain=causal_chain,
            bottleneck_node=bottleneck_node,
        )
        return {
            "symbol": output.symbol,
            "action": output.action,
            "confidence": output.confidence,
            "reason": output.reason,
            "horizon": output.horizon,
            "sector": output.sector,
            "sector_strength": output.sector_strength,
            "leader_flag": output.leader_flag,
            "causal_chain": output.causal_chain,
            "bottleneck_node": output.bottleneck_node,
        }
