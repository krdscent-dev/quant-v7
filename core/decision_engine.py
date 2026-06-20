"""V10 action decision layer.

This module converts V9 strategic scores into action-oriented decisions
without changing any upstream scoring model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.ial import InvestmentActionLanguage


@dataclass(frozen=True)
class DecisionOutput:
    """Action-based decision output."""

    symbol: str
    action: str
    confidence: float
    reason: str
    horizon: str


class DecisionEngine:
    """Convert score + regime + confidence into an action."""

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _normalize_regime(self, regime: Any) -> str:
        if hasattr(regime, "regime"):
            return str(getattr(regime, "regime")).upper()
        return str(regime or "").upper()

    def decide(
        self,
        symbol: str,
        score: float,
        regime: Any,
        confidence: float,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a standardized decision dictionary.

        Output format:
        {
          symbol,
          action,
          confidence,
          reason,
          horizon
        }
        """

        context = context or {}
        regime_name = self._normalize_regime(regime)
        score = float(score)
        confidence = self._clamp(float(confidence))
        price_zone = str(context.get("price_zone", "UNKNOWN")).upper()
        momentum = str(context.get("momentum", "UNKNOWN")).upper()
        stage = str(context.get("stage", "UNKNOWN")).upper()

        if not (score >= 0.0 and score <= 100.0) or confidence <= 0.0:
            action = InvestmentActionLanguage.INVALIDATE.value
            reason = "分数或置信度无效，无法形成有效决策。"
            horizon = "unknown"
        elif confidence < 0.35 or score < 15:
            action = InvestmentActionLanguage.INVALIDATE.value
            reason = "置信度过低或分数过弱，当前信号不可用。"
            horizon = "short"
        elif regime_name == "BULL":
            if score >= 85 and confidence >= 0.75:
                action = InvestmentActionLanguage.BUY.value
            elif score >= 70 and confidence >= 0.60:
                action = InvestmentActionLanguage.ADD.value
            elif score >= 55:
                action = InvestmentActionLanguage.HOLD.value
            else:
                action = InvestmentActionLanguage.OBSERVE.value
            horizon = "long" if action in {"BUY", "ADD"} else "mid"
            reason = f"牛市结构下，{stage or '趋势'}和{momentum or '动量'}支持{action}。"
        elif regime_name == "STRUCTURAL":
            if score >= 85 and confidence >= 0.70:
                action = InvestmentActionLanguage.BUY.value
            elif score >= 70:
                action = InvestmentActionLanguage.ADD.value
            elif score >= 50:
                action = InvestmentActionLanguage.HOLD.value
            else:
                action = InvestmentActionLanguage.OBSERVE.value
            horizon = "mid" if action != InvestmentActionLanguage.BUY.value else "long"
            reason = f"结构性行情中，重点看主题和周期位置，当前建议{action}。"
        elif regime_name == "ROTATION":
            if score >= 80 and confidence >= 0.70:
                action = InvestmentActionLanguage.ADD.value
            elif score >= 60:
                action = InvestmentActionLanguage.HOLD.value
            elif score >= 45:
                action = InvestmentActionLanguage.OBSERVE.value
            else:
                action = InvestmentActionLanguage.REDUCE.value
            horizon = "mid"
            reason = f"轮动环境下，优先跟踪强主题，当前价格区间为{price_zone}。"
        elif regime_name == "DEFENSIVE":
            if score >= 75 and confidence >= 0.70:
                action = InvestmentActionLanguage.HOLD.value
            elif score >= 50:
                action = InvestmentActionLanguage.OBSERVE.value
            elif score >= 35:
                action = InvestmentActionLanguage.REDUCE.value
            else:
                action = InvestmentActionLanguage.EXIT.value
            horizon = "short"
            reason = f"防御环境下优先控制回撤，价格区间={price_zone}。"
        else:
            if score >= 70 and confidence >= 0.70:
                action = InvestmentActionLanguage.OBSERVE.value
            elif score >= 45:
                action = InvestmentActionLanguage.REDUCE.value
            else:
                action = InvestmentActionLanguage.EXIT.value
            horizon = "short"
            reason = f"熊市或弱市环境下，优先降低暴露，当前动作={action}。"

        if regime_name in {"DEFENSIVE", "BEAR"} and action == InvestmentActionLanguage.BUY.value:
            action = InvestmentActionLanguage.OBSERVE.value
            reason = f"{regime_name} 环境不支持直接 BUY，已降级为 OBSERVE。"

        output = DecisionOutput(
            symbol=str(symbol),
            action=action,
            confidence=round(confidence, 2),
            reason=reason,
            horizon=horizon,
        )
        return {
            "symbol": output.symbol,
            "action": output.action,
            "confidence": output.confidence,
            "reason": output.reason,
            "horizon": output.horizon,
        }

