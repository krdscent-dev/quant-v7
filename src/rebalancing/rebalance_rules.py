"""Rebalance rules."""

from __future__ import annotations


class RebalanceRules:
    PRIORITY_MAP = {
        "SELL": 2,
        "REDUCE": 3,
        "BUY": 4,
        "ADD": 5,
        "HOLD": 9,
        "WATCH": 10,
    }

    def __init__(self) -> None:
        self.bucket_watchlist = {"WATCHLIST", "EXCLUDED"}

    def adjusted_target_weight(
        self,
        *,
        bucket: str,
        target_weight: float,
        confidence_score: float,
        risk_score: float,
    ) -> tuple[float, list[str]]:
        warnings: list[str] = []
        bucket = str(bucket).upper()
        target = max(0.0, float(target_weight))
        if bucket in self.bucket_watchlist:
            return 0.0, warnings
        if confidence_score < 0.60:
            warnings.append("confidence_below_060")
            return 0.0, warnings
        if confidence_score < 0.70:
            warnings.append("confidence_below_070_cap_3pct")
            target = min(target, 0.03)
        if risk_score > 0.85:
            warnings.append("risk_above_085")
            return 0.0, warnings
        if risk_score > 0.70:
            warnings.append("risk_above_070_cap_3pct")
            target = min(target, 0.03)
        return round(target, 4), warnings

    def determine_action(
        self,
        *,
        current_weight: float,
        target_weight: float,
        bucket: str,
        confidence_score: float,
        risk_score: float,
        critical_risk: bool = False,
        critical_affected: bool = False,
    ) -> str:
        bucket = str(bucket).upper()
        current_weight = max(0.0, float(current_weight))
        target_weight = max(0.0, float(target_weight))

        if bucket in self.bucket_watchlist:
            return "SELL" if current_weight > 0 else "WATCH"

        if confidence_score < 0.60:
            return "SELL" if current_weight > 0 else "WATCH"
        if risk_score > 0.85:
            return "SELL" if current_weight > 0 else "WATCH"

        if critical_risk and critical_affected:
            return "SELL" if current_weight > 0 and target_weight <= 0 else ("REDUCE" if current_weight > 0 else "WATCH")

        if current_weight <= 0 and target_weight > 0:
            return "BUY"

        diff = target_weight - current_weight
        if abs(diff) <= 0.01:
            return "HOLD" if target_weight > 0 or current_weight > 0 else "WATCH"
        if diff > 0.01:
            return "ADD"
        if target_weight <= 0:
            return "SELL" if current_weight > 0 else "WATCH"
        return "REDUCE"

    def priority(self, action: str, *, critical_risk: bool = False, critical_affected: bool = False) -> int:
        action = str(action).upper()
        if critical_risk and critical_affected and action in {"SELL", "REDUCE"}:
            return 1
        return self.PRIORITY_MAP.get(action, 10)

