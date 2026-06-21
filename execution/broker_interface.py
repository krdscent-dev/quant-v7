"""Abstract broker interface for the live trading bridge.

The bridge never calls a concrete broker directly. It only works with this
interface so dry-run and production wiring stay separated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class BrokerOrder:
    symbol: str
    action: str
    quantity: float
    price: float
    order_type: str = "LIMIT"


@dataclass(frozen=True)
class BrokerOrderResult:
    order_id: str
    status: str
    message: str
    payload: dict[str, Any]


class BrokerInterface(Protocol):
    def send_order(self, order: BrokerOrder) -> BrokerOrderResult:
        ...

    def cancel_order(self, order_id: str) -> BrokerOrderResult:
        ...

    def query_position(self, symbol: str) -> dict[str, Any]:
        ...
