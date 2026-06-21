"""Order routing layer for dry-run and approved live execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from execution.broker_interface import BrokerInterface, BrokerOrder, BrokerOrderResult


@dataclass(frozen=True)
class RoutedOrder:
    execution_status: str
    route: str
    order: dict[str, Any]
    broker_result: dict[str, Any] | None
    message: str


class OrderRouter:
    """Route orders either to a dry-run simulator or to a broker interface."""

    def route(
        self,
        order: Mapping[str, Any],
        *,
        broker: BrokerInterface | None = None,
        dry_run: bool = True,
        risk_result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(order)
        risk_result = dict(risk_result or {})
        if bool(risk_result.get("blocked", False)):
            routed = RoutedOrder(
                execution_status="BLOCKED",
                route="RISK_GATE",
                order=payload,
                broker_result=None,
                message="Order blocked by risk gate.",
            )
            return routed.__dict__

        if dry_run or broker is None:
            routed = RoutedOrder(
                execution_status="SIMULATED",
                route="DRY_RUN",
                order=payload,
                broker_result=None,
                message="Dry run mode active; no broker call executed.",
            )
            return routed.__dict__

        broker_order = BrokerOrder(
            symbol=str(payload.get("symbol", "")),
            action=str(payload.get("action", "OBSERVE")),
            quantity=float(payload.get("quantity", 0.0) or 0.0),
            price=float(payload.get("price", 0.0) or 0.0),
            order_type=str(payload.get("order_type", "LIMIT")),
        )
        result: BrokerOrderResult = broker.send_order(broker_order)
        routed = RoutedOrder(
            execution_status=result.status,
            route="BROKER",
            order=payload,
            broker_result={
                "order_id": result.order_id,
                "status": result.status,
                "message": result.message,
                "payload": result.payload,
            },
            message="Order routed through broker interface.",
        )
        return routed.__dict__
