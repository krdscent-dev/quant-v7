"""Validation status to confidence mapping."""

from __future__ import annotations

from enum import Enum


class ValidationStatus(str, Enum):
    PASS = "PASS"
    MINOR_DIFF = "MINOR_DIFF"
    MISSING = "MISSING"
    MAJOR_DIFF = "MAJOR_DIFF"
    INVALID = "INVALID"


CONFIDENCE_SCORE_MAP: dict[ValidationStatus, float] = {
    ValidationStatus.PASS: 1.00,
    ValidationStatus.MINOR_DIFF: 0.85,
    ValidationStatus.MISSING: 0.60,
    ValidationStatus.MAJOR_DIFF: 0.35,
    ValidationStatus.INVALID: 0.00,
}


def confidence_from_validation_status(status: str) -> float:
    try:
        key = ValidationStatus(status.upper())
    except Exception:
        return 0.0
    return CONFIDENCE_SCORE_MAP.get(key, 0.0)

