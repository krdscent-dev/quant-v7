"""Financial cross validation between AkShare and Tushare.

This layer compares provider-level financial summaries before factor
mapping. It is intentionally source-facing only and does not depend on
factor contracts or scoring logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

CORE_FIELDS: tuple[str, ...] = (
    "营业收入",
    "净利润",
    "ROE",
    "毛利率",
    "营收同比",
    "净利润同比",
)


@dataclass(frozen=True)
class CrossValidationResult:
    field_name: str
    akshare_value: Any
    tushare_value: Any
    difference: float | None
    difference_ratio: float | None
    confidence_level: str
    conflict_flags: list[str]


class FinancialCrossValidator:
    """Compare AkShare and Tushare financial summary payloads."""

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _confidence_for_field(self, ak_value: Any, ts_value: Any, diff_ratio: float | None) -> str:
        if ak_value is None and ts_value is None:
            return "low"
        if ak_value is None or ts_value is None:
            return "medium"
        if diff_ratio is None:
            return "medium"
        if diff_ratio <= 0.05:
            return "high"
        if diff_ratio <= 0.20:
            return "medium"
        return "low"

    def _conflict_flags(self, field_name: str, ak_value: Any, ts_value: Any, diff_ratio: float | None) -> list[str]:
        flags: list[str] = []
        if ak_value is None and ts_value is None:
            flags.append("both_sources_missing")
        elif ak_value is None:
            flags.append("akshare_missing")
        elif ts_value is None:
            flags.append("tushare_missing")
        if diff_ratio is not None and diff_ratio > 0.20:
            flags.append("material_difference")
        if field_name in {"ROE", "毛利率", "营收同比", "净利润同比"} and diff_ratio is not None and diff_ratio > 0.10:
            flags.append("core_metric_divergence")
        return flags

    def compare_financial_summary(
        self,
        akshare_summary: Mapping[str, Any],
        tushare_summary: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return field-by-field comparison output."""

        result_fields: dict[str, dict[str, Any]] = {}
        confidence_order = {"high": 2, "medium": 1, "low": 0}
        overall_confidence = "high"
        any_missing = False
        any_conflict = False

        for field_name in CORE_FIELDS:
            ak_value = akshare_summary.get(field_name)
            ts_value = tushare_summary.get(field_name)
            ak_num = self._to_float(ak_value)
            ts_num = self._to_float(ts_value)
            difference: float | None = None
            difference_ratio: float | None = None
            if ak_num is not None and ts_num is not None:
                difference = ak_num - ts_num
                denominator = max(abs(ak_num), abs(ts_num), 1e-9)
                difference_ratio = abs(difference) / denominator
            confidence_level = self._confidence_for_field(ak_value, ts_value, difference_ratio)
            flags = self._conflict_flags(field_name, ak_value, ts_value, difference_ratio)
            if confidence_order[confidence_level] < confidence_order[overall_confidence]:
                overall_confidence = confidence_level
            if "both_sources_missing" in flags or "akshare_missing" in flags or "tushare_missing" in flags:
                any_missing = True
            if "material_difference" in flags or "core_metric_divergence" in flags:
                any_conflict = True

            result_fields[field_name] = {
                "akshare_value": ak_value,
                "tushare_value": ts_value,
                "difference": difference,
                "difference_ratio": difference_ratio,
                "confidence_level": confidence_level,
                "conflict_flags": flags,
                "validation_status": _validation_status_from_confidence(confidence_level, flags),
            }

        if any_conflict:
            overall_confidence = "low"
        elif any_missing and overall_confidence == "high":
            overall_confidence = "medium"

        return {
            "overall_confidence_level": overall_confidence,
            "overall_confidence": _confidence_score(overall_confidence),
            "field_results": result_fields,
            "validation_status": _validation_status_from_confidence(overall_confidence, [
                flag for item in result_fields.values() for flag in item.get("conflict_flags", [])
            ]),
            "provider_trust_score": self._default_provider_trust_score(),
        }

    def _default_provider_trust_score(self) -> float:
        return 0.0


def _confidence_score(level: str) -> float:
    mapping = {"high": 1.0, "medium": 0.75, "low": 0.35}
    return mapping.get(str(level).lower(), 0.0)


def _validation_status_from_confidence(level: str, conflict_flags: list[str]) -> str:
    level = str(level).lower()
    if "both_sources_missing" in conflict_flags:
        return "INVALID"
    if "material_difference" in conflict_flags or "core_metric_divergence" in conflict_flags:
        return "MAJOR_DIFF"
    if level == "high":
        return "PASS"
    if level == "medium":
        return "MINOR_DIFF"
    return "MISSING"
