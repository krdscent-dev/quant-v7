"""Factor confidence engine."""

from __future__ import annotations

from typing import Any, Mapping

from .confidence_calculator import ConfidenceCalculator
from .confidence_contract import FactorConfidence
from .confidence_registry import ConfidenceRegistry


class ConfidenceEngine:
    def __init__(self) -> None:
        self.calculator = ConfidenceCalculator()
        self.registry = ConfidenceRegistry()

    def _completeness_ratio(self, factor_input: Mapping[str, Any], factor_name: str) -> float:
        bundle = factor_input.get("financial_summary", {})
        if isinstance(bundle, Mapping):
            mapped = dict(bundle.get("mapped_financial_summary", {}))
            missing_fields = list(bundle.get("missing_fields", []))
            total_fields = max(len(mapped) + len(missing_fields), len(mapped), 1)
            completeness = (total_fields - len(missing_fields)) / total_fields
            return max(0.0, min(1.0, completeness))
        return 1.0

    def _stability_ratio(self, factor_input: Mapping[str, Any], factor_name: str) -> float:
        history = self.registry.get_history(factor_name)
        if not history:
            factor_confidences = factor_input.get("factor_confidences", {})
            if isinstance(factor_confidences, Mapping):
                history_like = factor_confidences.get(factor_name, {})
                if isinstance(history_like, Mapping) and "stability_confidence" in history_like:
                    return float(history_like.get("stability_confidence", 1.0))
            return 1.0
        success_count = sum(1 for item in history if item.final_confidence >= 0.80)
        return success_count / len(history)

    def _provider_trust_score(self, factor_input: Mapping[str, Any]) -> float:
        financial = factor_input.get("financial_summary", {})
        if isinstance(financial, Mapping):
            if "provider_trust_score" in financial:
                return float(financial.get("provider_trust_score", 0.5))
            factor_confidences = factor_input.get("factor_confidences", {})
            if isinstance(factor_confidences, Mapping):
                item = factor_confidences.get("provider_trust_score")
                if isinstance(item, (int, float)):
                    return float(item)
        return 0.5

    def evaluate(self, factor_input: Mapping[str, Any], factor_name: str) -> FactorConfidence:
        factor_confidences = factor_input.get("factor_confidences", {})
        if isinstance(factor_confidences, Mapping):
            existing = factor_confidences.get(factor_name)
            if isinstance(existing, Mapping) and "final_confidence" in existing:
                return self.calculator.calculate_factor_confidence(
                    symbol=str(existing.get("symbol", factor_input.get("company_code", factor_input.get("symbol", "UNKNOWN")))),
                    period=str(existing.get("period", factor_input.get("period", "TTM"))),
                    factor_name=factor_name,
                    validation_status=str(existing.get("validation_status", factor_input.get("validation_status", "INVALID"))),
                    provider_trust_score=float(existing.get("provider_confidence", self._provider_trust_score(factor_input))),
                    completeness_ratio=float(existing.get("completeness_confidence", self._completeness_ratio(factor_input, factor_name))),
                    stability_ratio=float(existing.get("stability_confidence", self._stability_ratio(factor_input, factor_name))),
                    warnings=list(existing.get("warnings", [])),
                )

        validation_status = str(factor_input.get("validation_status", "INVALID"))
        provider_trust = self._provider_trust_score(factor_input)
        completeness_ratio = self._completeness_ratio(factor_input, factor_name)
        stability_ratio = self._stability_ratio(factor_input, factor_name)
        confidence = self.calculator.calculate_factor_confidence(
            symbol=str(factor_input.get("company_code", factor_input.get("symbol", "UNKNOWN"))),
            period=str(factor_input.get("period", "TTM")),
            factor_name=factor_name,
            validation_status=validation_status,
            provider_trust_score=provider_trust,
            completeness_ratio=completeness_ratio,
            stability_ratio=stability_ratio,
            warnings=list(factor_input.get("warnings", [])) if isinstance(factor_input.get("warnings", []), list) else [],
        )
        self.registry.add(confidence)
        return confidence

