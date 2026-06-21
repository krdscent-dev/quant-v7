"""V12.2 capital flow intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SectorFlowInput:
    sector: str
    trading_volume: float
    capital_inflow: float
    capital_outflow: float
    leader_stock_volume: float


@dataclass(frozen=True)
class SectorFlowSignal:
    sector: str
    flow_score: float
    rank: int
    direction: str
    net_inflow: float
    volume_score: float
    leader_concentration: float
    flow_strength: str


@dataclass(frozen=True)
class CapitalFlowAnalysis:
    top_inflow_sectors: list[SectorFlowSignal]
    outflow_sectors: list[SectorFlowSignal]
    flow_strength: str
    leader_concentration: float
    rotation_path: list[str]
    ranked_flows: list[SectorFlowSignal]


class V122CapitalFlowEngine:
    """Analyze sector inflow, leader concentration, and rotation path."""

    def analyze_sector_flows(
        self,
        sector_trading_volume: Mapping[str, float],
        capital_inflow: Mapping[str, float],
        capital_outflow: Mapping[str, float],
        leader_stock_volume: Mapping[str, float],
    ) -> CapitalFlowAnalysis:
        sectors = sorted(
            set(sector_trading_volume)
            | set(capital_inflow)
            | set(capital_outflow)
            | set(leader_stock_volume)
        )
        if not sectors:
            return CapitalFlowAnalysis([], [], "WEAK", 0.0, [], [])

        max_volume = max([float(sector_trading_volume.get(sector, 0.0) or 0.0) for sector in sectors] + [1.0])
        raw_rows: list[dict[str, float | str]] = []
        for sector in sectors:
            volume = max(0.0, float(sector_trading_volume.get(sector, 0.0) or 0.0))
            inflow = max(0.0, float(capital_inflow.get(sector, 0.0) or 0.0))
            outflow = max(0.0, float(capital_outflow.get(sector, 0.0) or 0.0))
            leader_volume = max(0.0, float(leader_stock_volume.get(sector, 0.0) or 0.0))
            net = inflow - outflow
            total_flow = inflow + outflow or 1.0
            net_ratio = max(-1.0, min(1.0, net / total_flow))
            volume_score = volume / max_volume if max_volume else 0.0
            concentration = self.detect_leader_flow(volume, leader_volume)
            score = 0.50 + 0.30 * net_ratio + 0.20 * volume_score + 0.15 * concentration
            raw_rows.append(
                {
                    "sector": sector,
                    "score": max(0.0, min(1.0, score)),
                    "net": net,
                    "volume_score": volume_score,
                    "concentration": concentration,
                }
            )

        ranked_raw = sorted(raw_rows, key=lambda item: float(item["score"]), reverse=True)
        ranked: list[SectorFlowSignal] = []
        for index, row in enumerate(ranked_raw, start=1):
            score = float(row["score"])
            if score >= 0.70:
                direction = "INFLOW"
            elif score >= 0.45:
                direction = "ROTATION"
            else:
                direction = "OUTFLOW"
            ranked.append(
                SectorFlowSignal(
                    sector=str(row["sector"]),
                    flow_score=round(score, 4),
                    rank=index,
                    direction=direction,
                    net_inflow=round(float(row["net"]), 4),
                    volume_score=round(float(row["volume_score"]), 4),
                    leader_concentration=round(float(row["concentration"]), 4),
                    flow_strength=self._flow_strength(score),
                )
            )

        top_inflows = [item for item in ranked if item.direction == "INFLOW"]
        outflows = [item for item in ranked if item.direction == "OUTFLOW"]
        leader_concentration = self.detect_leader_flow(
            sum(sector_trading_volume.values()),
            sum(leader_stock_volume.values()),
        )
        rotation_path = self.detect_rotation_path(ranked)
        overall_strength = self._flow_strength(sum(item.flow_score for item in ranked[:3]) / max(len(ranked[:3]), 1))
        return CapitalFlowAnalysis(
            top_inflow_sectors=top_inflows,
            outflow_sectors=outflows,
            flow_strength=overall_strength,
            leader_concentration=round(leader_concentration, 4),
            rotation_path=rotation_path,
            ranked_flows=ranked,
        )

    def detect_leader_flow(self, sector_trading_volume: float, leader_stock_volume: float) -> float:
        """Return leader volume concentration in a sector."""

        volume = max(0.0, float(sector_trading_volume or 0.0))
        leader_volume = max(0.0, float(leader_stock_volume or 0.0))
        if volume <= 0.0:
            return 0.0
        return round(max(0.0, min(1.0, leader_volume / volume)), 4)

    def detect_rotation_path(self, ranked_flows: list[SectorFlowSignal]) -> list[str]:
        """Return sector rotation sequence from strongest inflow to weakest flow."""

        return [item.sector for item in sorted(ranked_flows, key=lambda row: row.flow_score, reverse=True)]

    @staticmethod
    def _flow_strength(score: float) -> str:
        if score >= 0.75:
            return "STRONG"
        if score >= 0.55:
            return "MEDIUM"
        return "WEAK"
