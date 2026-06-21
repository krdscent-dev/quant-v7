"""V10.2 alpha opportunity detector.

AlphaEngine sits above regime adjustment. It detects selective opportunities
that deserve HOLD or SMALL_ADD even when the broad regime is BEAR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AlphaSignal:
    """Alpha opportunity signal."""

    has_alpha: bool
    action: str
    strength: float
    reason: str


class AlphaEngine:
    """Detect theme-driven alpha opportunities from score context."""

    STRONG_THEME_KEYWORDS = (
        "ai",
        "compute",
        "domestic",
        "supernode",
        "ascend",
        "packaging",
        "diamond",
        "material",
    )

    def _theme_strength(self, context: Mapping[str, Any]) -> float:
        if "theme_strength" in context:
            return max(0.0, min(1.0, float(context.get("theme_strength", 0.0))))
        theme = str(context.get("theme", "")).lower()
        tags = " ".join(str(item).lower() for item in context.get("theme_tags", []))
        combined = f"{theme} {tags}"
        if any(keyword in combined for keyword in self.STRONG_THEME_KEYWORDS):
            return 0.72
        return 0.45

    def evaluate(
        self,
        *,
        score: float,
        confidence: float,
        regime: str,
        context: Mapping[str, Any] | None = None,
    ) -> AlphaSignal:
        """Return a selective alpha signal before regime sizing adjustment."""

        context = context or {}
        score = float(score)
        confidence = max(0.0, min(1.0, float(confidence)))
        regime_name = str(regime).upper()
        theme_strength = self._theme_strength(context)
        alpha_strength = min(1.0, score / 100.0 * 0.65 + theme_strength * 0.25 + confidence * 0.10)

        if score >= 70 and theme_strength >= 0.65 and confidence >= 0.35:
            return AlphaSignal(
                has_alpha=True,
                action="SMALL_ADD" if regime_name in {"BEAR", "DEFENSIVE"} else "ADD",
                strength=round(alpha_strength, 2),
                reason="High score and strong theme create a selective alpha opportunity.",
            )
        if score >= 45 and theme_strength >= 0.65:
            return AlphaSignal(
                has_alpha=True,
                action="HOLD",
                strength=round(alpha_strength, 2),
                reason="Theme strength justifies holding exposure despite weak regime.",
            )
        if regime_name == "BEAR" and score >= 25 and theme_strength >= 0.65:
            return AlphaSignal(
                has_alpha=True,
                action="OBSERVE",
                strength=round(alpha_strength, 2),
                reason="Bear regime allows observation of strong themes, but score is not deployable.",
            )
        return AlphaSignal(
            has_alpha=False,
            action="OBSERVE",
            strength=round(alpha_strength, 2),
            reason="No alpha override detected.",
        )
