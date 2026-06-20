"""Factor confidence registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .confidence_contract import FactorConfidence


@dataclass(frozen=True)
class ConfidenceRecord:
    factor_name: str
    history: list[FactorConfidence]


class ConfidenceRegistry:
    def __init__(self) -> None:
        self._history: dict[str, list[FactorConfidence]] = {}

    def add(self, confidence: FactorConfidence) -> None:
        self._history.setdefault(confidence.factor_name, []).append(confidence)

    def get_history(self, factor_name: str) -> list[FactorConfidence]:
        return list(self._history.get(factor_name, []))

    def latest(self, factor_name: str) -> FactorConfidence | None:
        history = self._history.get(factor_name, [])
        return history[-1] if history else None

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {
            factor_name: [
                {
                    "symbol": item.symbol,
                    "period": item.period,
                    "factor_name": item.factor_name,
                    "validation_confidence": item.validation_confidence,
                    "provider_confidence": item.provider_confidence,
                    "completeness_confidence": item.completeness_confidence,
                    "stability_confidence": item.stability_confidence,
                    "final_confidence": item.final_confidence,
                    "warnings": list(item.warnings),
                }
                for item in history
            ]
            for factor_name, history in self._history.items()
        }

