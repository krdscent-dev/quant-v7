"""Build factor input objects from validated data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .factor_confidence import confidence_from_validation_status
from .factor_input_contract import FactorInput, FactorInputContract, normalize_factor_input


@dataclass
class FactorInputBuilder:
    """Convert validation results into factor inputs."""

    default_period: str = "TTM"

    def from_validation_result(
        self,
        *,
        symbol: str,
        factor_name: str,
        value: float | int | None,
        source_field: str,
        provider: str,
        validation_status: str,
        warnings: list[str] | None = None,
        period: str | None = None,
    ) -> FactorInput:
        confidence_score = confidence_from_validation_status(validation_status)
        payload = {
            "symbol": symbol,
            "period": period or self.default_period,
            "factor_name": factor_name,
            "value": 0.0 if value is None else float(value),
            "source_field": source_field,
            "provider": provider,
            "validation_status": validation_status,
            "confidence_score": confidence_score,
            "warnings": list(warnings or []),
        }
        return normalize_factor_input(payload)

    def from_cross_validation(
        self,
        *,
        symbol: str,
        period: str,
        factor_name: str,
        cross_validation_result: Mapping[str, Any],
        source_field: str,
        provider: str,
    ) -> FactorInput:
        status = str(cross_validation_result.get("validation_status", "MISSING"))
        value = cross_validation_result.get("value")
        warnings = list(cross_validation_result.get("conflict_flags", []))
        return self.from_validation_result(
            symbol=symbol,
            period=period,
            factor_name=factor_name,
            value=value,
            source_field=source_field,
            provider=provider,
            validation_status=status,
            warnings=warnings,
        )

