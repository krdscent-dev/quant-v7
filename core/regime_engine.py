"""Simple market regime classifier for the V10 decision layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RegimeResult:
    """Classification output for one market snapshot."""

    regime: str
    trend: float
    volatility: float
    confidence: float
    reason: str


class RegimeEngine:
    """Classify market conditions from basic trend and volatility inputs."""

    def _clamp(self, value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value))

    def classify(self, market_data: Mapping[str, Any] | None) -> RegimeResult:
        """Return one of: BULL / STRUCTURAL / ROTATION / DEFENSIVE / BEAR."""

        data = market_data or {}
        trend = self._clamp(float(data.get("trend", 0.0)))
        volatility = self._clamp(float(data.get("volatility", 0.0)))

        if trend >= 0.75 and volatility <= 0.35:
            regime = "BULL"
            confidence = 0.92
            reason = "趋势强且波动可控，属于风险偏好上行环境。"
        elif trend >= 0.55 and volatility <= 0.55:
            regime = "STRUCTURAL"
            confidence = 0.84
            reason = "趋势中强，市场更偏结构性主线驱动。"
        elif trend >= 0.35 and volatility <= 0.70:
            regime = "ROTATION"
            confidence = 0.78
            reason = "趋势一般但存在轮动，适合围绕主题切换观察。"
        elif volatility >= 0.70 and trend >= 0.25:
            regime = "DEFENSIVE"
            confidence = 0.74
            reason = "波动偏高，风险控制优先。"
        else:
            regime = "BEAR"
            confidence = 0.88
            reason = "趋势偏弱或波动偏大，防守优先。"

        return RegimeResult(
            regime=regime,
            trend=round(trend, 4),
            volatility=round(volatility, 4),
            confidence=confidence,
            reason=reason,
        )

