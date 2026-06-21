"""UI schema for human-readable V12 investment interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class UIComponent:
    type: str
    data: Mapping[str, Any] = field(default_factory=dict)
    label: str = ""
    highlight: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "type": self.type,
            "data": dict(self.data),
        }
        if self.label:
            payload["label"] = self.label
        if self.highlight:
            payload["highlight"] = True
        return payload


@dataclass(frozen=True)
class V12UISchema:
    layout: str = "dashboard"
    components: Sequence[UIComponent] = field(default_factory=tuple)
    mode: str = "MANUAL_REFRESH_ONLY"
    confidence_state: str = "NORMAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout": self.layout,
            "mode": self.mode,
            "confidence_state": self.confidence_state,
            "components": [component.to_dict() for component in self.components],
        }

