"""Metrics export helpers."""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from typing import Any, Mapping


class MetricsExporter:
    def to_dict(self, obj: Any) -> dict[str, Any]:
        if obj is None:
            return {}
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            data = obj.to_dict()
            if isinstance(data, dict):
                return self._filter_metrics(data)
        if is_dataclass(obj):
            return self._filter_metrics(asdict(obj))
        if isinstance(obj, Mapping):
            return self._filter_metrics(dict(obj))
        if hasattr(obj, "__dict__"):
            return self._filter_metrics({key: value for key, value in vars(obj).items() if not key.startswith("_")})
        return {"value": obj}

    def _filter_metrics(self, data: Mapping[str, Any]) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        for key, value in data.items():
            if key in {"warnings", "summary", "portfolio_summary", "decision_explanation", "score_explanation"}:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[key] = float(value)
            elif isinstance(value, Mapping) and key == "metrics":
                metrics.update(self._filter_metrics(value))
        return metrics

    def to_records(self, obj: Any) -> list[dict[str, Any]]:
        metrics = self.to_dict(obj)
        return [metrics] if metrics else []

