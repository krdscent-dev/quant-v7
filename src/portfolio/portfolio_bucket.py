"""Portfolio bucketing rules."""

from __future__ import annotations


class PortfolioBucket:
    CORE = "CORE"
    SATELLITE = "SATELLITE"
    WATCHLIST = "WATCHLIST"
    EXCLUDED = "EXCLUDED"

    def classify(self, *, final_decision: str, total_score: float, confidence_score: float) -> str:
        decision = str(final_decision).upper()
        if decision == "AVOID" or confidence_score < 0.50:
            return self.EXCLUDED
        if decision == "BUY" and total_score >= 85 and confidence_score >= 0.75:
            return self.CORE
        if decision in {"BUY", "WATCH"} and total_score >= 70 and confidence_score >= 0.65:
            return self.SATELLITE
        if decision in {"WATCH", "REVIEW"} and total_score >= 55:
            return self.WATCHLIST
        return self.EXCLUDED

