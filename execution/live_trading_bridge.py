"""Live trading bridge with strict DRY_RUN safety defaults."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Mapping
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from execution.order_router import OrderRouter
from risk.live_risk_guard import LiveRiskGuard


@dataclass(frozen=True)
class LiveExecutionResult:
    execution_status: str
    order_details: dict[str, Any]
    risk_approval_result: dict[str, Any]
    dry_run: bool
    message: str


class LiveTradingBridge:
    """Bridge V11 decisions into an execution layer behind a risk gate."""

    def __init__(
        self,
        *,
        dry_run: bool = True,
        risk_guard: LiveRiskGuard | None = None,
        order_router: OrderRouter | None = None,
    ) -> None:
        self.dry_run = bool(dry_run)
        self.risk_guard = risk_guard or LiveRiskGuard()
        self.order_router = order_router or OrderRouter()

    def submit_order(
        self,
        decision: Mapping[str, Any],
        *,
        portfolio_state: Mapping[str, Any] | None = None,
        system_state: Mapping[str, Any] | None = None,
        broker: Any | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        payload = self._build_order(decision, portfolio_state)
        dry_run_mode = self.dry_run if dry_run is None else bool(dry_run)
        risk_result = self.risk_guard.check(payload, portfolio_state=portfolio_state, system_state=system_state)
        routed = self.order_router.route(payload, broker=broker, dry_run=dry_run_mode, risk_result=risk_result)
        execution_status = routed.get("execution_status", "UNKNOWN")
        if risk_result.get("blocked", False):
            execution_status = "BLOCKED"
        result = LiveExecutionResult(
            execution_status=execution_status,
            order_details={
                "order": payload,
                "routed": routed,
            },
            risk_approval_result=risk_result,
            dry_run=dry_run_mode,
            message=routed.get("message", ""),
        )
        return {
            "execution_status": result.execution_status,
            "order_details": result.order_details,
            "risk_approval_result": result.risk_approval_result,
            "dry_run": result.dry_run,
            "message": result.message,
        }

    @staticmethod
    def _build_order(
        decision: Mapping[str, Any],
        portfolio_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        portfolio_state = dict(portfolio_state or {})
        action = str(decision.get("action", "OBSERVE")).upper()
        symbol = str(decision.get("symbol", "UNKNOWN"))
        quantity = float(decision.get("quantity", decision.get("size", 0.0)) or 0.0)
        price = float(decision.get("price", portfolio_state.get("last_price", 0.0)) or 0.0)
        if quantity <= 0.0:
            portfolio_value = float(portfolio_state.get("portfolio_value", 0.0) or 0.0)
            base_weight = float(decision.get("weight", 0.0) or 0.0)
            if portfolio_value > 0.0 and base_weight > 0.0:
                quantity = (portfolio_value * base_weight) / max(price, 1.0)
        notional = quantity * max(price, 0.0)
        return {
            "symbol": symbol,
            "action": action,
            "quantity": round(quantity, 6),
            "price": round(price, 4),
            "notional": round(notional, 4),
            "order_type": str(decision.get("order_type", "LIMIT")),
            "risk_approved": bool(decision.get("risk_approved", False)),
            "decision_confidence": float(decision.get("confidence", 0.0) or 0.0),
            "decision_reason": str(decision.get("reason", "")),
        }
