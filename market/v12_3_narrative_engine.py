"""V12.3 narrative intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

from market.v12_1_structure_engine import MarketStructureV121
from market.v12_2_capital_flow_engine import CapitalFlowAnalysis, SectorFlowSignal


@dataclass(frozen=True)
class NarrativeSignal:
    narrative: str
    narrative_strength: float
    narrative_phase: str
    supporting_sectors: list[str]
    capital_flow_support: float
    sector_breadth: float


@dataclass(frozen=True)
class NarrativeAnalysis:
    active_narratives: list[NarrativeSignal]
    dominant_narrative: str
    narrative_strength: float
    narrative_phase: str
    supporting_sectors: list[str]
    supporting_themes: list[str]
    consistency: str
    reason: str


class V123NarrativeEngine:
    """Identify market narratives and filter weak stories without flow support."""

    def extract_market_theme(
        self,
        sector_data: Mapping[str, float],
        capital_flow_data: CapitalFlowAnalysis,
        market_structure: MarketStructureV121,
    ) -> NarrativeAnalysis:
        candidates: list[NarrativeSignal] = []
        flows = list(capital_flow_data.ranked_flows)
        for narrative, sectors in self._narrative_map().items():
            supporting_flows = [flow for flow in flows if flow.sector in sectors]
            if not supporting_flows:
                continue
            strength = self.evaluate_narrative_strength(
                sectors=sectors,
                sector_data=sector_data,
                supporting_flows=supporting_flows,
            )
            if strength < 0.55:
                continue
            phase = self.detect_narrative_phase(
                strength,
                capital_flow_data.flow_strength,
                market_structure.regime,
            )
            candidates.append(
                NarrativeSignal(
                    narrative=narrative,
                    narrative_strength=strength,
                    narrative_phase=phase,
                    supporting_sectors=[flow.sector for flow in supporting_flows],
                    capital_flow_support=round(sum(flow.flow_score for flow in supporting_flows) / len(supporting_flows), 4),
                    sector_breadth=round(len(supporting_flows) / max(len(sector_data), 1), 4),
                )
            )

        candidates = sorted(candidates, key=lambda item: item.narrative_strength, reverse=True)
        if not candidates:
            return NarrativeAnalysis(
                active_narratives=[],
                dominant_narrative="No confirmed narrative",
                narrative_strength=0.0,
                narrative_phase="DECLINE",
                supporting_sectors=[],
                supporting_themes=[],
                consistency="LOW",
                reason="Weak narratives were ignored because capital-flow support was insufficient.",
            )

        dominant = candidates[0]
        consistency = "HIGH" if dominant.narrative_strength >= 0.75 else "MEDIUM"
        return NarrativeAnalysis(
            active_narratives=candidates,
            dominant_narrative=dominant.narrative,
            narrative_strength=dominant.narrative_strength,
            narrative_phase=dominant.narrative_phase,
            supporting_sectors=dominant.supporting_sectors,
            supporting_themes=dominant.supporting_sectors,
            consistency=consistency,
            reason=(
                f"{dominant.narrative} is supported by "
                f"{', '.join(dominant.supporting_sectors)} with {dominant.narrative_phase} phase."
            ),
        )

    def evaluate_narrative_strength(
        self,
        sectors: Iterable[str],
        sector_data: Mapping[str, float],
        supporting_flows: Iterable[SectorFlowSignal],
    ) -> float:
        sector_list = list(sectors)
        flow_list = list(supporting_flows)
        if not sector_list or not flow_list:
            return 0.0
        breadth = len(flow_list) / max(len(sector_data), 1)
        avg_sector_strength = sum(float(sector_data.get(sector, 0.0) or 0.0) for sector in sector_list) / len(sector_list)
        avg_flow = sum(flow.flow_score for flow in flow_list) / len(flow_list)
        leader_support = sum(flow.leader_concentration for flow in flow_list) / len(flow_list)
        strength = 0.35 * avg_sector_strength + 0.40 * avg_flow + 0.15 * leader_support + 0.10 * breadth
        return round(max(0.0, min(1.0, strength)), 4)

    def detect_narrative_phase(
        self,
        narrative_strength: float,
        flow_strength: str,
        market_regime: str,
    ) -> str:
        if narrative_strength >= 0.85 and flow_strength == "STRONG":
            return "PEAK" if market_regime == "BULL" else "EXPANSION"
        if narrative_strength >= 0.70:
            return "EXPANSION"
        if narrative_strength >= 0.55:
            return "EMERGING"
        return "DECLINE"

    @staticmethod
    def _narrative_map() -> dict[str, list[str]]:
        return {
            "AI capital expenditure and compute infrastructure": [
                "AI Computing",
                "Huawei Ascend Ecosystem",
                "Advanced Packaging",
            ],
            "Semiconductor localization": [
                "Domestic Substitution",
                "Huawei Ascend Ecosystem",
                "Advanced Packaging",
            ],
            "New materials validation": [
                "Advanced Materials",
                "Advanced Packaging",
            ],
        }
