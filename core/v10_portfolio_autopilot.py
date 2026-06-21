"""V10.5 portfolio autopilot layer.

This module applies portfolio-level constraints after single-symbol decisions.
It does not change scoring, alpha detection, sector intelligence, cognitive
reasoning, or the base decision engine.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from core.ial import InvestmentActionLanguage


@dataclass(frozen=True)
class PortfolioConstraint:
    """Portfolio-level adjustment for one decision."""

    symbol: str
    sector: str
    original_action: str
    final_action: str
    portfolio_exposure: float
    risk_score: float
    rebalance_signal: str
    reason: str


class V10PortfolioAutopilot:
    """Convert independent decisions into portfolio-aware final actions."""

    OVEREXPOSURE_LIMIT = 0.35
    UNDEREXPOSURE_LIMIT = 0.10
    HIGH_RISK_LIMIT = 0.70

    def calculate_exposure(self, portfolio: Iterable[Mapping[str, Any]]) -> dict[str, float]:
        """Calculate sector exposure from current/proposed portfolio rows."""

        rows = list(portfolio)
        if not rows:
            return {}

        weighted: Counter[str] = Counter()
        total_weight = 0.0
        for row in rows:
            sector = str(row.get("sector", "UNKNOWN"))
            weight = self._row_weight(row)
            weighted[sector] += weight
            total_weight += weight

        if total_weight <= 0:
            return {}
        return {
            sector: round(float(weight) / total_weight, 4)
            for sector, weight in weighted.items()
        }

    def risk_score(self, exposure: Mapping[str, float]) -> float:
        """Return portfolio risk from sector concentration."""

        if not exposure:
            return 0.0
        max_exposure = max(float(value) for value in exposure.values())
        concentration_penalty = max(0.0, max_exposure - self.OVEREXPOSURE_LIMIT) / 0.65
        breadth_penalty = max(0.0, 0.25 - min(float(value) for value in exposure.values()))
        risk = 0.55 * max_exposure + 0.30 * concentration_penalty + 0.15 * breadth_penalty
        return round(max(0.0, min(1.0, risk)), 2)

    def rebalance_signal(self, exposure: Mapping[str, float]) -> dict[str, str]:
        """Return sector-level rebalance signals."""

        signals: dict[str, str] = {}
        for sector, value in exposure.items():
            sector_exposure = float(value)
            if sector_exposure > self.OVEREXPOSURE_LIMIT:
                signals[sector] = "REDUCE"
            elif sector_exposure < self.UNDEREXPOSURE_LIMIT:
                signals[sector] = "INCREASE"
            else:
                signals[sector] = "NEUTRAL"
        return signals

    def apply_constraints(self, decisions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Apply portfolio constraints to final action output."""

        rows = [dict(item) for item in decisions]
        exposure = self.calculate_exposure(rows)
        portfolio_risk = self.risk_score(exposure)
        signals = self.rebalance_signal(exposure)

        adjusted: list[dict[str, Any]] = []
        for row in rows:
            sector = str(row.get("sector", "UNKNOWN"))
            original_action = str(row.get("action", InvestmentActionLanguage.OBSERVE.value))
            sector_exposure = float(exposure.get(sector, 0.0))
            signal = signals.get(sector, "NEUTRAL")
            final_action, reason = self._final_action(
                action=original_action,
                sector_exposure=sector_exposure,
                portfolio_risk=portfolio_risk,
                signal=signal,
            )
            row.update(
                {
                    "original_action": original_action,
                    "action": final_action,
                    "portfolio_exposure": round(sector_exposure, 2),
                    "risk_score": portfolio_risk,
                    "rebalance_signal": signal,
                    "portfolio_reason": reason,
                }
            )
            adjusted.append(row)
        return adjusted

    def _row_weight(self, row: Mapping[str, Any]) -> float:
        action = str(row.get("action", "")).upper()
        if action in {"ADD", "BUY"}:
            return 1.5
        if action == "SMALL_ADD":
            return 1.0
        if action == "HOLD":
            return 0.8
        if action == "OBSERVE":
            return 0.4
        if action == "REDUCE":
            return 0.2
        return 0.1

    def _final_action(
        self,
        action: str,
        sector_exposure: float,
        portfolio_risk: float,
        signal: str,
    ) -> tuple[str, str]:
        if sector_exposure > self.OVEREXPOSURE_LIMIT:
            if action in {"ADD", "SMALL_ADD", "HOLD"}:
                return InvestmentActionLanguage.REDUCE.value, "Sector exposure above 35%; reduce bias applied."
            return action, "Sector exposure above 35%; no increase allowed."

        if portfolio_risk > self.HIGH_RISK_LIMIT:
            if action in {"ADD", "SMALL_ADD"}:
                return InvestmentActionLanguage.HOLD.value, "Portfolio risk above 0.70; shifted to HOLD bias."
            if action == "HOLD":
                return InvestmentActionLanguage.OBSERVE.value, "Portfolio risk above 0.70; shifted to OBSERVE bias."
            return action, "Portfolio risk above 0.70; defensive action retained."

        if sector_exposure < self.UNDEREXPOSURE_LIMIT and action == "OBSERVE":
            return InvestmentActionLanguage.HOLD.value, "Sector exposure below 10%; increase watch bias applied."

        if signal == "INCREASE":
            return action, "Sector exposure below target; increase signal recorded."
        if signal == "REDUCE":
            return action, "Sector exposure above target; reduce signal recorded."
        return action, "Portfolio exposure within constraint band."
