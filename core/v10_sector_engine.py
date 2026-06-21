"""V10.3 sector intelligence layer.

This module adds a sector-level alpha view without changing the V9 scoring
formula. Sector strength is a relative rotation signal derived from current
ranking outputs, so it can identify leadership even when absolute scores are
low in a defensive regime.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class SectorSignal:
    """Sector context attached to a single symbol decision."""

    symbol: str
    sector: str
    sector_strength: float
    leader_flag: bool
    sector_rank: int
    rotation_signal: str


class V10SectorEngine:
    """Classify symbols into sectors and derive relative sector leadership."""

    THEME_TO_SECTOR = {
        "AI算力": "AI Computing",
        "AI国产替代": "AI Domestic Substitution",
        "华为昇腾生态": "Huawei Ascend Ecosystem",
        "华为超节点": "Huawei Ascend Ecosystem",
        "超节点受益链": "Huawei Ascend Ecosystem",
        "国产替代": "Domestic Substitution",
        "玻璃基板": "Advanced Materials",
        "人造金刚石": "Advanced Materials",
        "新材料": "Advanced Materials",
        "先进封装": "Advanced Packaging",
    }

    def __init__(self, ranked_results: Iterable[Any] | None = None) -> None:
        self._records = [self._to_record(item) for item in ranked_results or []]
        self._symbol_to_sector = {
            str(record["symbol"]): str(record["sector"]) for record in self._records
        }
        self._sector_scores = self._calculate_sector_scores(self._records)
        self._sector_rotation = self.rotation_signal(self._sector_scores)
        self._signals = self._build_signals(self._records)

    @classmethod
    def from_results(cls, ranked_results: Iterable[Any]) -> "V10SectorEngine":
        return cls(ranked_results)

    @property
    def sector_scores(self) -> dict[str, float]:
        return dict(self._sector_scores)

    @property
    def sector_rotation(self) -> dict[str, str]:
        return dict(self._sector_rotation)

    def classify(self, symbol: str) -> str:
        """Return the sector assigned to a symbol."""

        return self._symbol_to_sector.get(str(symbol), "UNKNOWN")

    def sector_strength(self, sector: str) -> float:
        """Return relative strength for one sector in the current universe."""

        return round(float(self._sector_scores.get(str(sector), 0.0)), 2)

    def detect_leader(self, sector_stocks: Iterable[Any]) -> str | None:
        """Return the highest-scoring symbol inside a sector."""

        records = [self._to_record(item) for item in sector_stocks]
        if not records:
            return None
        return str(max(records, key=lambda item: float(item["score"]))["symbol"])

    def rotation_signal(self, sector_scores: Mapping[str, float]) -> dict[str, str]:
        """Classify sector rotation state from relative sector strength."""

        if not sector_scores:
            return {}
        max_strength = max(float(value) for value in sector_scores.values())
        min_strength = min(float(value) for value in sector_scores.values())
        spread = max_strength - min_strength
        signals: dict[str, str] = {}
        for sector, strength in sector_scores.items():
            value = float(strength)
            if value >= 0.75 and spread >= 0.15:
                signals[sector] = "LEADER_CONCENTRATION"
            elif value >= 0.50:
                signals[sector] = "ROTATION_CANDIDATE"
            else:
                signals[sector] = "WEAK_ROTATION"
        return signals

    def build_sector_context(self) -> dict[str, dict[str, Any]]:
        """Return decision-ready sector context keyed by symbol."""

        return {
            symbol: {
                "sector": signal.sector,
                "sector_strength": signal.sector_strength,
                "sector_leader_flag": signal.leader_flag,
                "leader_flag": signal.leader_flag,
                "sector_rank": signal.sector_rank,
                "rotation_signal": signal.rotation_signal,
            }
            for symbol, signal in self._signals.items()
        }

    def sector_dashboard(self) -> list[dict[str, Any]]:
        """Return sector ranking rows for CLI/report output."""

        leaders = self._leaders_by_sector()
        rows = []
        for sector, strength in sorted(
            self._sector_scores.items(), key=lambda item: item[1], reverse=True
        ):
            rows.append(
                {
                    "sector": sector,
                    "sector_strength": round(float(strength), 2),
                    "rotation_signal": self._sector_rotation.get(sector, "UNKNOWN"),
                    "leader": leaders.get(sector, "UNKNOWN"),
                }
            )
        return rows

    def _to_record(self, item: Any) -> dict[str, Any]:
        if isinstance(item, Mapping):
            symbol = item.get("code", item.get("symbol", "UNKNOWN"))
            theme = item.get("theme", "UNKNOWN")
            score = item.get("strategic_score", item.get("score", 0.0))
            name = item.get("name", symbol)
        else:
            symbol = getattr(item, "code", getattr(item, "symbol", "UNKNOWN"))
            theme = getattr(item, "theme", "UNKNOWN")
            score = getattr(item, "strategic_score", getattr(item, "score", 0.0))
            name = getattr(item, "name", symbol)
        sector = self.THEME_TO_SECTOR.get(str(theme), str(theme) if theme else "UNKNOWN")
        return {
            "symbol": str(symbol),
            "name": str(name),
            "theme": str(theme),
            "sector": sector,
            "score": float(score or 0.0),
        }

    def _calculate_sector_scores(self, records: list[dict[str, Any]]) -> dict[str, float]:
        if not records:
            return {}
        grouped: dict[str, list[float]] = {}
        for record in records:
            grouped.setdefault(str(record["sector"]), []).append(float(record["score"]))

        sector_avg = {sector: mean(scores) for sector, scores in grouped.items()}
        max_avg = max(sector_avg.values()) or 1.0
        max_score = max((max(scores) for scores in grouped.values()), default=1.0) or 1.0

        scores: dict[str, float] = {}
        for sector, values in grouped.items():
            relative_avg = sector_avg[sector] / max_avg
            relative_leader = max(values) / max_score
            breadth_bonus = min(len(values), 5) * 0.01
            # Keep this relative, not absolute, so sector leadership is visible
            # even when the whole market is in a low-score defensive regime.
            strength = 0.35 + 0.45 * relative_avg + 0.15 * relative_leader + breadth_bonus
            scores[sector] = round(max(0.0, min(1.0, strength)), 2)
        return scores

    def _leaders_by_sector(self) -> dict[str, str]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in self._records:
            grouped.setdefault(str(record["sector"]), []).append(record)
        return {
            sector: str(max(records, key=lambda item: float(item["score"]))["symbol"])
            for sector, records in grouped.items()
        }

    def _build_signals(self, records: list[dict[str, Any]]) -> dict[str, SectorSignal]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(str(record["sector"]), []).append(record)

        signals: dict[str, SectorSignal] = {}
        for sector, sector_records in grouped.items():
            ranked = sorted(sector_records, key=lambda item: float(item["score"]), reverse=True)
            strength = self.sector_strength(sector)
            rotation = self._sector_rotation.get(sector, "UNKNOWN")
            for index, record in enumerate(ranked, start=1):
                symbol = str(record["symbol"])
                signals[symbol] = SectorSignal(
                    symbol=symbol,
                    sector=sector,
                    sector_strength=strength,
                    leader_flag=index == 1,
                    sector_rank=index,
                    rotation_signal=rotation,
                )
        return signals
