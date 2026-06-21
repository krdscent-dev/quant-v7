"""Live execution risk gate.

All orders must pass through this gate before routing. The guard defaults to
blocking anything that lacks explicit approval or looks operationally unsafe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RiskApprovalResult:
    approved: bool
    blocked: bool
    reason: str
    severity: str
    checks: list[str]


class LiveRiskGuard:
    """Approve or block live orders before they reach any broker layer."""

    def __init__(
        self,
        *,
        max_notional: float = 200_000.0,
        max_position_size: float = 0.15,
        max_exposure: float = 0.60,
    ) -> None:
        self.max_notional = float(max_notional)
        self.max_position_size = float(max_position_size)
        self.max_exposure = float(max_exposure)

    def check(
        self,
        order: Mapping[str, Any],
        portfolio_state: Mapping[str, Any] | None = None,
        system_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        portfolio_state = dict(portfolio_state or {})
        system_state = dict(system_state or {})
        checks: list[str] = []
        blocked = False

        approved_flag = bool(order.get("risk_approved", False))
        if not approved_flag:
            blocked = True
            checks.append("missing_risk_approval")

        if self._abnormal_size(order, portfolio_state):
            blocked = True
            checks.append("abnormal_position_size")

        if self._unstable_system(system_state):
            blocked = True
            checks.append("system_instability_detected")

        exposure = self._to_float(portfolio_state.get("current_exposure"), default=0.0)
        if exposure > self.max_exposure:
            blocked = True
            checks.append("portfolio_exposure_too_high")

        if blocked:
            reason = "Risk gate blocked the order."
            severity = "HIGH" if len(checks) >= 2 else "MEDIUM"
        else:
            reason = "Risk gate approved the order."
            severity = "LOW"

        result = RiskApprovalResult(
            approved=not blocked,
            blocked=blocked,
            reason=reason,
            severity=severity,
            checks=checks,
        )
        return {
            "approved": result.approved,
            "blocked": result.blocked,
            "reason": result.reason,
            "severity": result.severity,
            "checks": result.checks,
        }

    def _abnormal_size(self, order: Mapping[str, Any], portfolio_state: Mapping[str, Any]) -> bool:
        notional = self._to_float(order.get("notional"), default=0.0)
        quantity = self._to_float(order.get("quantity"), default=0.0)
        portfolio_value = self._to_float(portfolio_state.get("portfolio_value"), default=0.0)
        if notional > self.max_notional:
            return True
        if portfolio_value > 0.0 and notional / portfolio_value > self.max_position_size:
            return True
        if quantity > 0.0 and quantity > 1_000_000 * self.max_position_size:
            return True
        return False

    @staticmethod
    def _unstable_system(system_state: Mapping[str, Any]) -> bool:
        if not system_state:
            return False
        if bool(system_state.get("unstable", False)):
            return True
        if bool(system_state.get("circuit_breaker", False)):
            return True
        return str(system_state.get("status", "")).upper() in {"UNSTABLE", "HALTED", "PANIC"}

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default
