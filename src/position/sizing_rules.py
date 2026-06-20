"""Position sizing rules."""

from __future__ import annotations


class SizingRules:
    BASE_WEIGHTS = {
        "CORE": 0.08,
        "SATELLITE": 0.04,
        "WATCHLIST": 0.0,
        "EXCLUDED": 0.0,
    }
    MAX_WEIGHTS = {
        "CORE": 0.12,
        "SATELLITE": 0.06,
        "WATCHLIST": 0.0,
        "EXCLUDED": 0.0,
    }
    MIN_WEIGHTS = {
        "CORE": 0.04,
        "SATELLITE": 0.01,
        "WATCHLIST": 0.0,
        "EXCLUDED": 0.0,
    }

    def confidence_multiplier(self, confidence_score: float) -> float:
        if confidence_score >= 0.90:
            return 1.20
        if confidence_score >= 0.80:
            return 1.10
        if confidence_score < 0.60:
            return 0.70
        return 1.00

    def risk_multiplier(self, risk_score: float) -> float:
        if risk_score >= 0.70:
            return 0.70
        if risk_score >= 0.50:
            return 0.85
        return 1.00

    def base_weight(self, bucket: str) -> float:
        return self.BASE_WEIGHTS.get(str(bucket).upper(), 0.0)

    def max_weight(self, bucket: str) -> float:
        return self.MAX_WEIGHTS.get(str(bucket).upper(), 0.0)

    def min_weight(self, bucket: str) -> float:
        return self.MIN_WEIGHTS.get(str(bucket).upper(), 0.0)

    def recommended_weight(self, bucket: str, confidence_score: float, risk_score: float) -> float:
        base = self.base_weight(bucket)
        weight = base * self.confidence_multiplier(confidence_score) * self.risk_multiplier(risk_score)
        return round(weight, 4)

