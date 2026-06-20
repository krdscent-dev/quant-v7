"""V8 Strategic Score Engine.

This module implements a research-oriented strategic scoring engine.
It ranks companies or instruments based on medium-term industrial trend
strength over the next 12-24 months.

The engine is intentionally not a trading signal generator. It is a
research sorting tool designed for:
- comparing themes
- prioritizing research coverage
- tracking industrial trend strength
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
import csv

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to run strategy/strategic_score_engine.py") from exc

from core.data_mapping import DataMappingLayer
from src.evidence.evidence_chain_builder import EvidenceChainBuilder
from data_sources.mock_provider import MockDataProvider
from factors.order_confirmation_factor import calculate_order_confirmation_score


@dataclass(frozen=True)
class StrategicScoreResult:
    """Strategic score output."""

    code: str
    name: str
    theme: str
    strategic_score: float
    factor_breakdown: Mapping[str, float] = field(default_factory=dict)
    score_explanation: str = ""
    evidence_refs: Mapping[str, Any] = field(default_factory=dict)


WEIGHTS: Mapping[str, float] = {
    "tau_factor_score": 0.20,
    "supernode_score": 0.20,
    "domestic_substitution_score": 0.20,
    "advanced_packaging_score": 0.15,
    "order_confirmation_score": 0.15,
    "advanced_material_score": 0.10,
}


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _normalize_input_score(value: Any) -> float:
    score = float(value)
    if 0.0 <= score <= 1.0:
        score *= 100.0
    return _clamp_0_100(score)


def _confidence_multiplier(value: Any) -> float:
    score = float(value) if value is not None else 1.0
    if score <= 0.0:
        return 0.0
    if score <= 1.0:
        return score
    return _clamp_0_100(score) / 100.0


def _factor_confidence(factor_dict: Mapping[str, Any], factor_name: str) -> float:
    candidate_keys = (
        f"{factor_name}_confidence_score",
        f"{factor_name}_confidence",
        "confidence_score",
    )
    for key in candidate_keys:
        if key in factor_dict:
            return _confidence_multiplier(factor_dict.get(key))
    return 1.0


def calculate_strategic_score(factor_dict: Mapping[str, Any]) -> StrategicScoreResult:
    """Calculate the strategic score for a single company or instrument.

    Output:
    - strategic_score
    - factor_breakdown
    - score_explanation

    Notes:
    - This is a research ranking tool, not a buy/sell recommendation.
    - The score is constrained to the 0-100 range.
    - The engine intentionally uses a medium-term horizon (12-24 months).
    """

    code = str(factor_dict.get("code", "UNKNOWN"))
    name = str(factor_dict.get("name", "UNKNOWN"))
    theme = str(factor_dict.get("theme", "UNKNOWN"))

    tau_factor_score = _normalize_input_score(factor_dict.get("tau_factor_score", 0.0))
    supernode_score = _normalize_input_score(factor_dict.get("supernode_score", 0.0))
    domestic_substitution_score = _normalize_input_score(factor_dict.get("domestic_substitution_score", 0.0))
    advanced_packaging_score = _normalize_input_score(factor_dict.get("advanced_packaging_score", 0.0))
    advanced_material_score = _normalize_input_score(factor_dict.get("advanced_material_score", 0.0))
    confidence_score = _factor_confidence(factor_dict, "confidence")

    order_confirmation_result = calculate_order_confirmation_score(
        {
            "new_orders": factor_dict.get("new_orders", 0.0),
            "capacity_expansion": factor_dict.get("capacity_expansion", 0.0),
            "management_guidance": factor_dict.get("management_guidance", 0.0),
            "customer_verification": factor_dict.get("customer_verification", 0.0),
            "revenue_acceleration": factor_dict.get("revenue_acceleration", 0.0),
        }
    )
    order_confirmation_score = order_confirmation_result.order_confirmation_score

    strategic_score = _clamp_0_100(
        (
            tau_factor_score * WEIGHTS["tau_factor_score"]
            + supernode_score * WEIGHTS["supernode_score"]
            + domestic_substitution_score * WEIGHTS["domestic_substitution_score"]
            + advanced_packaging_score * WEIGHTS["advanced_packaging_score"]
            + order_confirmation_score * WEIGHTS["order_confirmation_score"]
            + advanced_material_score * WEIGHTS["advanced_material_score"]
        )
        * confidence_score
    )

    factor_breakdown = {
        "tau_factor_score": round(tau_factor_score, 2),
        "supernode_score": round(supernode_score, 2),
        "domestic_substitution_score": round(domestic_substitution_score, 2),
        "advanced_packaging_score": round(advanced_packaging_score, 2),
        "order_confirmation_score": round(order_confirmation_score, 2),
        "advanced_material_score": round(advanced_material_score, 2),
        "confidence_score": round(confidence_score, 2),
    }

    score_explanation = (
        f"{name} ({code}) 属于 {theme} 主题，战略评分强调中期产业趋势强度。"
        f" 当前分值由 τ因子、超节点、国产替代、先进封装、订单验证和先进材料共同决定。"
    )
    evidence_refs = {}
    if "evidence_chain" in factor_dict:
        evidence_refs = {"evidence_chain": factor_dict.get("evidence_chain")}
    elif "evidence_refs" in factor_dict:
        evidence_refs = dict(factor_dict.get("evidence_refs", {}))

    return StrategicScoreResult(
        code=code,
        name=name,
        theme=theme,
        strategic_score=round(strategic_score, 2),
        factor_breakdown=factor_breakdown,
        score_explanation=score_explanation,
        evidence_refs=evidence_refs,
    )


def _load_core_universe(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    themes = payload.get("themes", [])
    records: list[dict[str, Any]] = []
    for theme_entry in themes:
        theme_name = str(theme_entry.get("theme_name", ""))
        for item in theme_entry.get("items", []):
            records.append(
                {
                    "code": str(item.get("code", "")),
                    "name": str(item.get("name", "")),
                    "theme": str(item.get("theme", theme_name)),
                    "priority": str(item.get("watch_priority", "")),
                }
            )
    return records


def _build_demo_factor_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Create a research-only placeholder factor payload."""

    priority = str(record.get("priority", "C"))
    priority_map = {"A": 88.0, "B": 72.0, "C": 58.0}
    base = priority_map.get(priority, 58.0)
    theme = str(record.get("theme", ""))

    supernode_boost = 8.0 if ("昇腾" in theme or "超节点" in theme) else 0.0
    domestic_boost = 7.0 if "国产替代" in theme else 0.0
    packaging_boost = 6.0 if "先进封装" in theme else 0.0
    material_boost = 5.0 if ("材料" in theme or "玻璃基板" in theme or "人造金刚石" in theme) else 0.0
    tau_boost = 4.0 if "AI算力" in theme else 0.0

    return {
        "code": record.get("code", ""),
        "name": record.get("name", ""),
        "theme": theme,
        "tau_factor_score": _clamp_0_100(base + tau_boost),
        "supernode_score": _clamp_0_100(base + supernode_boost),
        "domestic_substitution_score": _clamp_0_100(base + domestic_boost),
        "advanced_packaging_score": _clamp_0_100(base + packaging_boost),
        "advanced_material_score": _clamp_0_100(base + material_boost),
        "new_orders": 60.0 if priority == "A" else 45.0 if priority == "B" else 35.0,
        "capacity_expansion": 55.0 if priority == "A" else 42.0 if priority == "B" else 30.0,
        "management_guidance": 58.0 if priority == "A" else 40.0 if priority == "B" else 28.0,
        "customer_verification": 62.0 if priority == "A" else 46.0 if priority == "B" else 34.0,
        "revenue_acceleration": 57.0 if priority == "A" else 41.0 if priority == "B" else 29.0,
    }


def _write_csv(path: Path, results: list[StrategicScoreResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "code",
                "name",
                "theme",
                "strategic_score",
                "tau_factor_score",
                "supernode_score",
                "domestic_substitution_score",
                "advanced_packaging_score",
                "order_confirmation_score",
                "advanced_material_score",
            ]
        )
        for rank, item in enumerate(results, start=1):
            breakdown = item.factor_breakdown
            writer.writerow(
                [
                    rank,
                    item.code,
                    item.name,
                    item.theme,
                    f"{item.strategic_score:.2f}",
                    f"{breakdown['tau_factor_score']:.2f}",
                    f"{breakdown['supernode_score']:.2f}",
                    f"{breakdown['domestic_substitution_score']:.2f}",
                    f"{breakdown['advanced_packaging_score']:.2f}",
                    f"{breakdown['order_confirmation_score']:.2f}",
                    f"{breakdown['advanced_material_score']:.2f}",
                ]
            )


def _write_markdown(path: Path, results: list[StrategicScoreResult]) -> None:
    lines: list[str] = []
    lines.append("# Strategic Ranking")
    lines.append("")
    lines.append("> 说明：战略评分是研究排序工具，不是直接买卖建议。")
    lines.append("")
    lines.append("## 排名结果")
    for rank, item in enumerate(results, start=1):
        lines.append(f"### {rank}. {item.name} ({item.code})")
        lines.append(f"- 主题：{item.theme}")
        lines.append(f"- Strategic Score：{item.strategic_score:.2f}")
        lines.append(f"- 因子拆解：{item.factor_breakdown}")
        lines.append(f"- 解释：{item.score_explanation}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_rankings() -> list[StrategicScoreResult]:
    """Build ranking results from the existing core universe."""

    base_dir = Path(__file__).resolve().parents[1]
    core_universe_path = base_dir / "data" / "watchlists" / "a_share_core_universe.yaml"
    records = _load_core_universe(core_universe_path)
    provider = MockDataProvider()
    mapping_layer = DataMappingLayer(provider)

    results: list[StrategicScoreResult] = []
    for record in records:
        payload = mapping_layer.build_strategic_score_payload(
            code=record["code"],
            name=record["name"],
            theme=record["theme"],
        )
        payload.update(_build_demo_factor_payload(record))
        results.append(calculate_strategic_score(payload))

    return sorted(results, key=lambda item: item.strategic_score, reverse=True)


def main() -> None:
    """Script entry point."""

    base_dir = Path(__file__).resolve().parents[1]
    results = build_rankings()
    _write_csv(base_dir / "reports" / "strategic_ranking.csv", results)
    _write_markdown(base_dir / "reports" / "strategic_ranking.md", results)
    print(f"Wrote {len(results)} ranked records to reports/strategic_ranking.csv and reports/strategic_ranking.md")


if __name__ == "__main__":
    main()
