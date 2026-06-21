"""Regime-aware agent weight adjustment for V11.2."""

from __future__ import annotations

from typing import Mapping


class AdaptiveGovernor:
    """Adjust agent weights according to market regime."""

    def adjust_for_regime(self, weights: Mapping[str, float], regime: str) -> dict[str, float]:
        adjusted = dict(weights)
        regime_name = str(regime).upper()

        if regime_name in {"BULL", "STRUCTURAL"}:
            adjusted["AlphaAgent"] = adjusted.get("AlphaAgent", 0.0) + 0.05
            adjusted["RiskAgent"] = max(0.05, adjusted.get("RiskAgent", 0.0) - 0.03)
        elif regime_name in {"BEAR", "DEFENSIVE"}:
            adjusted["RiskAgent"] = adjusted.get("RiskAgent", 0.0) + 0.05
            adjusted["AlphaAgent"] = max(0.05, adjusted.get("AlphaAgent", 0.0) - 0.03)
        elif regime_name in {"RANGE", "ROTATION"}:
            average = 1.0 / max(len(adjusted), 1)
            adjusted = {agent: (value * 0.70 + average * 0.30) for agent, value in adjusted.items()}

        return self._normalize(adjusted)

    def _normalize(self, weights: Mapping[str, float]) -> dict[str, float]:
        total = sum(float(value) for value in weights.values())
        if total <= 0:
            return {agent: round(1.0 / len(weights), 4) for agent in weights}
        return {agent: round(float(value) / total, 4) for agent, value in weights.items()}
