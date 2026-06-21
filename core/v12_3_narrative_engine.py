"""Deterministic narrative intelligence for the V12 system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class NarrativeResult:
    active_narratives: list[str]
    narrative_strength: float
    narrative_phase: str
    supporting_sectors: list[str]
    sector_narrative_mapping: dict[str, list[str]]


class NarrativeEngine:
    """Interpret sector flow into market narratives."""

    def extract_market_theme(self, market_data: Mapping[str, Any]) -> dict[str, Any]:
        sectors = self._normalize_sectors(market_data.get("sectors"))
        flow_strength = self._to_float(market_data.get("flow_strength"), default=0.5)
        sector_flows = market_data.get("sector_flows") or {}
        news_keywords = self._normalize_keywords(market_data.get("news_keywords"))

        if not sectors and not sector_flows and not news_keywords:
            return {
                "active_narratives": [],
                "narrative_strength": 0.5,
                "narrative_phase": "UNKNOWN",
                "supporting_sectors": [],
                "sector_narrative_mapping": {},
            }

        mapping = self._build_mapping(sectors, sector_flows, news_keywords)
        active_narratives = sorted(mapping.keys())
        supporting_sectors = sorted({sector for sectors_list in mapping.values() for sector in sectors_list})
        strength = self.evaluate_narrative_strength(active_narratives, flow_strength, sectors, supporting_sectors)
        phase = self.detect_narrative_phase(strength)

        return {
            "active_narratives": active_narratives,
            "narrative_strength": round(strength, 4),
            "narrative_phase": phase,
            "supporting_sectors": supporting_sectors,
            "sector_narrative_mapping": mapping,
        }

    def evaluate_narrative_strength(
        self,
        active_narratives: Sequence[str],
        flow_strength: float,
        sectors: Sequence[str],
        supporting_sectors: Sequence[str],
    ) -> float:
        narrative_count = len(active_narratives)
        sector_breadth_factor = len(set(supporting_sectors)) / max(len(set(sectors)) or 1, 1)
        strength = (narrative_count * 0.3) + (flow_strength * 0.5) + (sector_breadth_factor * 0.2)
        return self._clamp(strength)

    def detect_narrative_phase(self, narrative_strength: float) -> str:
        if narrative_strength < 0.3:
            return "EMERGING"
        if narrative_strength < 0.6:
            return "EXPANSION"
        if narrative_strength < 0.8:
            return "PEAK"
        return "DECLINE"

    def _build_mapping(
        self,
        sectors: Sequence[str],
        sector_flows: Any,
        news_keywords: Sequence[str],
    ) -> dict[str, list[str]]:
        narrative_map: dict[str, list[str]] = {}
        sector_set = {self._normalize_name(sector) for sector in sectors}
        keyword_set = {self._normalize_name(keyword) for keyword in news_keywords}
        flow_keys = self._normalize_sector_flows(sector_flows)
        all_tokens = sector_set | keyword_set | flow_keys

        def add_narrative(name: str, supporting: Sequence[str]) -> None:
            filtered = [sector for sector in supporting if self._normalize_name(sector) in sector_set or self._normalize_name(sector) in flow_keys]
            if filtered:
                narrative_map[name] = sorted(set(filtered))

        if any(
            token in all_tokens
            for token in {
                "ai_computing",
                "ai_compute",
                "ai",
                "compute",
                "compute_infrastructure",
                "ai_capex",
            }
        ) or ("ai" in "".join(sorted(all_tokens)) and "compute" in "".join(sorted(all_tokens))):
            add_narrative("AI EXPANSION", ["AI Computing", "AI", "Compute"])
        if any("packag" in token for token in all_tokens):
            add_narrative("CHIPLET CYCLE", ["Advanced Packaging", "Packaging"])
        if any(
            token in all_tokens
            for token in {
                "domestic_substitution",
                "localization",
                "localization_trend",
                "domestic",
                "substitution",
            }
        ) or any("local" in token or "substitut" in token for token in all_tokens):
            add_narrative("LOCALIZATION TREND", ["Domestic Substitution", "Localization"])
        tech_signals = sum(
            1
            for item in all_tokens
            if any(token in item for token in ["ai", "compute", "semiconductor", "chip", "packag", "material", "technology"])
        )
        if tech_signals >= 2:
            add_narrative("TECH CYCLE EXPANSION", list(sectors) or list(flow_keys))

        return narrative_map

    def _normalize_sectors(self, sectors: Any) -> list[str]:
        if not isinstance(sectors, Sequence) or isinstance(sectors, (str, bytes)):
            return []
        result: list[str] = []
        for sector in sectors:
            try:
                result.append(str(sector))
            except Exception:
                continue
        return result

    def _normalize_keywords(self, keywords: Any) -> list[str]:
        if not isinstance(keywords, Sequence) or isinstance(keywords, (str, bytes)):
            return []
        result: list[str] = []
        for keyword in keywords:
            try:
                result.append(str(keyword))
            except Exception:
                continue
        return result

    def _normalize_sector_flows(self, sector_flows: Any) -> set[str]:
        keys: set[str] = set()
        if isinstance(sector_flows, Mapping):
            for key in sector_flows.keys():
                keys.add(self._normalize_name(str(key)))
            return keys
        if isinstance(sector_flows, Sequence) and not isinstance(sector_flows, (str, bytes)):
            for item in sector_flows:
                if isinstance(item, Mapping):
                    for key in item.keys():
                        keys.add(self._normalize_name(str(key)))
        return keys

    @staticmethod
    def _normalize_name(value: str) -> str:
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


def extract_market_theme(market_data: Mapping[str, Any]) -> dict[str, Any]:
    return NarrativeEngine().extract_market_theme(market_data)
