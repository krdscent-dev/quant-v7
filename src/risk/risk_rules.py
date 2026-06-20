"""Risk rules."""

from __future__ import annotations


class RiskRules:
    MAX_POSITION = {
        "CORE": 0.12,
        "SATELLITE": 0.06,
        "WATCHLIST": 0.0,
        "EXCLUDED": 0.0,
    }

    def concentration_level(self, ratio: float, *, is_theme: bool = False) -> str:
        if is_theme:
            if ratio <= 0.35:
                return "LOW"
            if ratio <= 0.45:
                return "MEDIUM"
            if ratio <= 0.55:
                return "HIGH"
            return "CRITICAL"
        if ratio <= 0.30:
            return "LOW"
        if ratio <= 0.40:
            return "MEDIUM"
        if ratio <= 0.50:
            return "HIGH"
        return "CRITICAL"

    def low_confidence_limit(self, confidence_score: float, recommended_weight: float) -> float:
        if confidence_score < 0.60:
            return 0.0
        if confidence_score < 0.70:
            return min(recommended_weight, 0.03)
        return recommended_weight

    def high_risk_limit(self, risk_score: float, recommended_weight: float) -> float:
        if risk_score > 0.85:
            return 0.0
        if risk_score > 0.70:
            return min(recommended_weight, 0.03)
        return recommended_weight

    def total_risk_score(self, concentration_risk: float, position_risk: float, confidence_risk: float, theme_risk: float) -> float:
        return max(
            0.0,
            min(1.0, 0.30 * concentration_risk + 0.25 * position_risk + 0.25 * confidence_risk + 0.20 * theme_risk),
        )

    def risk_level(self, total_risk_score: float) -> str:
        if total_risk_score <= 0.30:
            return "LOW"
        if total_risk_score <= 0.55:
            return "MEDIUM"
        if total_risk_score <= 0.75:
            return "HIGH"
        return "CRITICAL"

