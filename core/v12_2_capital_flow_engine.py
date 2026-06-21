"""Deterministic capital flow engine for the V12 system.

This module interprets sector-level capital rotation without trading logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CapitalFlowResult:
    top_inflow_sectors: list[str]
    top_outflow_sectors: list[str]
    flow_strength: float
    leader_concentration: float
    rotation_signal: str


class CapitalFlowEngine:
    """Classify sector inflow, outflow, leader concentration, and rotation."""

    def analyze_capital_flow(self, market_data: Mapping[str, Any]) -> dict[str, Any]:
        sector_data = self._normalize_sector_data(market_data.get("sector_data"))
        stock_data = self._normalize_stock_data(market_data.get("stock_data"))

        if not sector_data:
            return {
                "top_inflow_sectors": [],
                "top_outflow_sectors": [],
                "flow_strength": 0.5,
                "leader_concentration": 0.0,
                "rotation_signal": "UNKNOWN",
            }

        sector_scores = self._sector_scores(sector_data)
        ranked = sorted(sector_scores.items(), key=lambda item: item[1], reverse=True)
        top_inflow = [sector for sector, _ in ranked[:3]]
        top_outflow = [sector for sector, _ in sorted(sector_scores.items(), key=lambda item: item[1])[:3]]
        flow_strength = self._flow_strength(sector_scores.values())
        leader_concentration = self._leader_concentration(stock_data)
        rotation_signal = self._rotation_signal(sector_scores)

        return {
            "top_inflow_sectors": top_inflow,
            "top_outflow_sectors": top_outflow,
            "flow_strength": round(flow_strength, 4),
            "leader_concentration": round(leader_concentration, 4),
            "rotation_signal": rotation_signal,
        }

    def _sector_scores(self, sector_data: Mapping[str, float]) -> dict[str, float]:
        values = [max(0.0, float(value or 0.0)) for value in sector_data.values()]
        max_volume = max(values) if values else 1.0
        min_volume = min(values) if values else 0.0
        span = max(max_volume - min_volume, 1e-9)

        scores: dict[str, float] = {}
        for sector, value in sector_data.items():
            volume = max(0.0, float(value or 0.0))
            normalized = (volume - min_volume) / span if span else 0.5
            scores[sector] = max(0.0, min(1.0, 0.25 + 0.75 * normalized))
        return scores

    def _flow_strength(self, sector_scores: Any) -> float:
        scores = [max(0.0, min(1.0, float(score))) for score in sector_scores]
        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _leader_concentration(self, stock_data: Mapping[str, Mapping[str, Any]]) -> float:
        total_volume = 0.0
        leader_volume = 0.0
        for stock in stock_data.values():
            volume = max(0.0, float(stock.get("volume", 0.0) or 0.0))
            total_volume += volume
            if bool(stock.get("is_leader", False)):
                leader_volume += volume
        if total_volume <= 0.0:
            return 0.0
        return leader_volume / total_volume

    def _rotation_signal(self, sector_scores: Mapping[str, float]) -> str:
        normalized_keys = {self._normalize_sector_name(name): name for name in sector_scores}
        ranked_sectors = sorted(sector_scores.items(), key=lambda item: item[1], reverse=True)
        top_sector = ranked_sectors[0][0]
        top_key = self._normalize_sector_name(top_sector)

        if top_key == "ai":
            return "AI_LEAD_ROTATION"

        chip_keywords = {"semiconductor", "semis", "packaging", "advanced_packaging", "chip", "chip_package"}
        material_keywords = {"materials", "material", "equipment", "mid_late_cycle"}
        if {"semiconductor", "packaging"} & set(normalized_keys):
            if sector_scores.get(normalized_keys.get("semiconductor", ""), 0.0) >= 0.55 and sector_scores.get(normalized_keys.get("packaging", ""), 0.0) >= 0.55:
                return "CHIP_CYCLE_EXPANSION"
        if any(key in top_key for key in material_keywords) or any(key in top_key for key in chip_keywords):
            return "MID_LATE_CYCLE_ROTATION"
        if len(ranked_sectors) >= 2 and ranked_sectors[0][1] - ranked_sectors[1][1] < 0.08:
            return "NO_CLEAR_ROTATION"
        return "NO_CLEAR_ROTATION"

    def _normalize_sector_data(self, sector_data: Any) -> dict[str, float]:
        if not isinstance(sector_data, Mapping):
            return {}
        normalized: dict[str, float] = {}
        for key, value in sector_data.items():
            try:
                normalized[str(key)] = max(0.0, float(value))
            except Exception:
                continue
        return normalized

    def _normalize_stock_data(self, stock_data: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(stock_data, Mapping):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for symbol, payload in stock_data.items():
            if not isinstance(payload, Mapping):
                continue
            normalized[str(symbol)] = {
                "volume": max(0.0, float(payload.get("volume", 0.0) or 0.0)),
                "price_change": float(payload.get("price_change", 0.0) or 0.0),
                "is_leader": bool(payload.get("is_leader", False)),
            }
        return normalized

    @staticmethod
    def _normalize_sector_name(name: str) -> str:
        return str(name).strip().lower().replace(" ", "_")


def analyze_capital_flow(market_data: Mapping[str, Any]) -> dict[str, Any]:
    """Functional helper for convenience."""

    return CapitalFlowEngine().analyze_capital_flow(market_data)

