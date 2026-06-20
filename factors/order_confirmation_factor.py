"""Order confirmation factor framework.

This module defines a research-only order confirmation score used to
measure whether a business story is moving into earnings validation.
No real market data is used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class OrderConfirmationResult:
    """Order confirmation factor output."""

    order_confirmation_score: float
    new_orders: float
    capacity_expansion: float
    management_guidance: float
    customer_verification: float
    revenue_acceleration: float
    details: Mapping[str, float]


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _normalize_input_score(value: Any) -> float:
    """Normalize research inputs to a 0-100 scale."""

    score = float(value)
    if 0.0 <= score <= 1.0:
        score *= 100.0
    return _clamp_0_100(score)


def calculate_order_confirmation_score(
    factor_dict: Mapping[str, Any],
) -> OrderConfirmationResult:
    """Calculate the order confirmation score.

    Framework intent:
    - new_orders: whether new orders are landing
    - capacity_expansion: whether capacity is expanding to support demand
    - management_guidance: whether management guidance confirms demand
    - customer_verification: whether customers explicitly validate the story
    - revenue_acceleration: whether revenue begins to accelerate

    The score is a research placeholder and does not use external APIs.
    """

    new_orders = _normalize_input_score(factor_dict.get("new_orders", 0.0))
    capacity_expansion = _normalize_input_score(factor_dict.get("capacity_expansion", 0.0))
    management_guidance = _normalize_input_score(factor_dict.get("management_guidance", 0.0))
    customer_verification = _normalize_input_score(factor_dict.get("customer_verification", 0.0))
    revenue_acceleration = _normalize_input_score(factor_dict.get("revenue_acceleration", 0.0))

    order_confirmation_score = _clamp_0_100(
        0.28 * new_orders
        + 0.15 * capacity_expansion
        + 0.17 * management_guidance
        + 0.20 * customer_verification
        + 0.20 * revenue_acceleration
    )

    return OrderConfirmationResult(
        order_confirmation_score=round(order_confirmation_score, 2),
        new_orders=round(new_orders, 2),
        capacity_expansion=round(capacity_expansion, 2),
        management_guidance=round(management_guidance, 2),
        customer_verification=round(customer_verification, 2),
        revenue_acceleration=round(revenue_acceleration, 2),
        details={
            "new_orders": round(new_orders, 2),
            "capacity_expansion": round(capacity_expansion, 2),
            "management_guidance": round(management_guidance, 2),
            "customer_verification": round(customer_verification, 2),
            "revenue_acceleration": round(revenue_acceleration, 2),
        },
    )
