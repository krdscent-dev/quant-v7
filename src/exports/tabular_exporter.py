"""Tabular export helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Sequence


class TabularExporter:
    def to_dict(self, obj: Any) -> dict[str, Any]:
        if obj is None:
            return {}
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            data = obj.to_dict()
            if isinstance(data, dict):
                return dict(data)
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, Mapping):
            return dict(obj)
        if hasattr(obj, "__dict__"):
            return {key: value for key, value in vars(obj).items() if not key.startswith("_")}
        return {"value": obj}

    def _select_records(self, data: Mapping[str, Any]) -> list[Any]:
        for key in ("records", "candidates", "ranked_candidates", "checks", "equity_curve", "recommendations", "steps", "actions"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]

    def to_records(self, obj: Any) -> list[dict[str, Any]]:
        if obj is None:
            return []
        if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
            return [self.to_dict(item) for item in obj]
        data = self.to_dict(obj)
        records = self._select_records(data)
        output: list[dict[str, Any]] = []
        for item in records:
            if isinstance(item, Mapping):
                output.append(dict(item))
            else:
                output.append(self.to_dict(item))
        return output

    def to_dataframe_records(self, obj: Any) -> list[dict[str, Any]]:
        return self.to_records(obj)

