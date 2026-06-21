"""Dashboard layout schema for standardized V12 reports.

The dashboard layer is intentionally presentation-only. It consumes the
normalized V12 schema and emits a frontend-friendly JSON layout with the
decision core visually dominant.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DashboardMetric:
    key: str
    label: str
    value: float
    display_type: str
    color: str = "neutral"


@dataclass(frozen=True)
class DashboardPanel:
    panel_id: str
    title: str
    priority: int
    dominant: bool = False
    layout: str = "card"
    chart_type: str = "table"
    metrics: Sequence[DashboardMetric] = field(default_factory=tuple)
    data_binding: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "priority": self.priority,
            "dominant": self.dominant,
            "layout": self.layout,
            "chart_type": self.chart_type,
            "metrics": [asdict(metric) for metric in self.metrics],
            "data_binding": dict(self.data_binding),
            "description": self.description,
        }


@dataclass(frozen=True)
class V12DashboardSchema:
    version: str = "v12-dashboard-schema-v1"
    confidence_state: str = "NORMAL"
    headline: str = "Decision first, data second"
    panels: Sequence[DashboardPanel] = field(default_factory=tuple)
    visual_mappings: Mapping[str, Any] = field(default_factory=dict)
    fallback_state: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "confidence_state": self.confidence_state,
            "headline": self.headline,
            "fallback_state": self.fallback_state,
            "panels": [panel.to_dict() for panel in self.panels],
            "visual_mappings": dict(self.visual_mappings),
        }

