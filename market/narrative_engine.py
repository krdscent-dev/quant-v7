"""Extract dominant market narrative from sector and theme signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from market.capital_flow_engine import CapitalFlowSignal


@dataclass(frozen=True)
class MarketNarrative:
    dominant_narrative: str
    supporting_themes: list[str]
    consistency: str
    reason: str


class NarrativeEngine:
    """Infer the dominant market story from leading sectors."""

    def extract(
        self,
        capital_flows: Iterable[CapitalFlowSignal],
        ranked_results: Iterable[Any] | None = None,
    ) -> MarketNarrative:
        flows = list(capital_flows)
        leading = [item for item in flows if item.rank <= 3]
        supporting = [item.sector for item in leading]
        top_sector = supporting[0] if supporting else "UNKNOWN"
        narrative = self._sector_to_narrative(top_sector)
        consistency = "HIGH" if len([item for item in leading if item.flow_score >= 0.75]) >= 2 else "MEDIUM"
        if not supporting:
            consistency = "LOW"
        return MarketNarrative(
            dominant_narrative=narrative,
            supporting_themes=supporting,
            consistency=consistency,
            reason=f"Top sector flow points to {top_sector}; narrative consistency is {consistency}.",
        )

    @staticmethod
    def _sector_to_narrative(sector: str) -> str:
        mapping = {
            "AI Computing": "AI capital expenditure and compute infrastructure",
            "Huawei Ascend Ecosystem": "Huawei Ascend domestic AI infrastructure",
            "Domestic Substitution": "Semiconductor localization",
            "Advanced Packaging": "Advanced packaging capacity upgrade",
            "Advanced Materials": "New materials validation",
        }
        return mapping.get(sector, "Theme rotation without a single dominant story")

