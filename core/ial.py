"""Investment Action Language (IAL).

This module defines the action vocabulary used by the V10 decision layer.
It is intentionally lightweight so it can sit on top of the existing V9
scoring pipeline without changing any score calculation logic.
"""

from __future__ import annotations

from enum import Enum


class InvestmentActionLanguage(str, Enum):
    """Canonical investment actions."""

    BUY = "BUY"
    SMALL_ADD = "SMALL_ADD"
    ADD = "ADD"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    OBSERVE = "OBSERVE"
    INVALIDATE = "INVALIDATE"


VALID_ACTIONS: tuple[str, ...] = tuple(action.value for action in InvestmentActionLanguage)


def normalize_action(action: str | None) -> str:
    """Normalize arbitrary text into a supported action value."""

    candidate = str(action or "").strip().upper()
    return candidate if candidate in VALID_ACTIONS else InvestmentActionLanguage.OBSERVE.value
