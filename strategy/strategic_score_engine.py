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
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to run strategy/strategic_score_engine.py") from exc


@dataclass(frozen=True)
class StrategicScoreBreakdown:
    """Component-level score breakdown."""

    tau_factor_score: float
    supernode_score: float
    domestic_substitution_score: float
    advanced_packaging_score: float
    order_confirmation_score: float
    advanced_material_score: float


@dataclass(frozen=True)
class StrategicScoreResult:
    """Strategic score output."""

    code: str
    name: str
    theme: str
    strategic_score: float
    factor_breakdown: Mapping[str, float] = field(default_factory=dict)
    score_explanation: str = ""


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
    """Normalize user-provided research factors to a 0-100 scale.

    The engine accepts already-scaled research values or 0-1 placeholders.
    """

    score = float(value)
    if 0.0 <= score <= 1.0:
        score *= 100.0
    return _clamp_0_100(score)


def _derive_order_confirmation_score(factors: Mapping[str, Any]) -> float:
    """Placeholder logic for order confirmation strength.

    The intent is to capture whether a story is moving into earnings
    validation. The score reflects four research dimensions:
    - order landing
    - revenue confirmation
    - customer validation
    - story-to-earnings transition

    No external data sources are used here. Inputs are expected to be
    research-side placeholders or analyst-assigned values.
    """

    order_landing = _normalize_input_score(factors.get("order_landing_score", 0.0))
    revenue_confirmation = _normalize_input_score(factors.get("revenue_confirmation_score", 0.0))
    customer_validation = _normalize_input_score(factors.get("customer_validation_score", 0.0))
    story_to_earnings = _normalize_input_score(factors.get("story_to_earnings_score", 0.0))

    return _clamp_0_100(
        0.35 * order_landing
        + 0.30 * revenue_confirmation
        + 0.20 * customer_validation
        + 0.15 * story_to_earnings
    )


def calculate_strategic_score(
    factor_dict: Mapping[str, Any],
) -> StrategicScoreResult:
    """Calculate the strategic score for a single company or instrument.

    Input:
        factor_dict: A research-side factor dictionary for one company.

    Output:
        StrategicScoreResult containing:
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
    order_confirmation_score = _derive_order_confirmation_score(factor_dict)

    strategic_score = _clamp_0_100(
        tau_factor_score * WEIGHTS["tau_factor_score"]
        + supernode_score * WEIGHTS["supernode_score"]
        + domestic_substitution_score * WEIGHTS["domestic_substitution_score"]
        + advanced_packaging_score * WEIGHTS["advanced_packaging_score"]
        + order_confirmation_score * WEIGHTS["order_confirmation_score"]
        + advanced_material_score * WEIGHTS["advanced_material_score"]
    )

    factor_breakdown = {
        "tau_factor_score": round(tau_factor_score, 2),
        "supernode_score": round(supernode_score, 2),
        "domestic_substitution_score": round(domestic_substitution_score, 2),
        "advanced_packaging_score": round(advanced_packaging_score, 2),
        "order_confirmation_score": round(order_confirmation_score, 2),
        "advanced_material_score": round(advanced_material_score, 2),
    }

    score_explanation = (
        f"{name} ({code}) 属于 {theme} 主题，"
        f"战略评分强调中期产业趋势强度。"
        f" 当前分值由 τ因子、超节点、国产替代、先进封装、订单验证和先进材料共同决定。"
    )

    return StrategicScoreResult(
        code=code,
        name=name,
        theme=theme,
        strategic_score=round(strategic_score, 2),
        factor_breakdown=factor_breakdown,
        score_explanation=score_explanation,
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
    """Create a research-only placeholder factor payload.

    This intentionally avoids external APIs and market data. The values
    are not predictions; they are only deterministic placeholders used to
    exercise the scoring pipeline.
    """

    priority = str(record.get("priority", "C"))
    priority_map = {"A": 88.0, "B": 72.0, "C": 58.0}
    base = priority_map.get(priority, 58.0)
    theme = str(record.get("theme", ""))

    supernode_boost = 8.0 if "昇腾" in theme or "超节点" in theme else 0.0
    domestic_boost = 7.0 if "国产替代" in theme else 0.0
    packaging_boost = 6.0 if "先进封装" in theme else 0.0
    material_boost = 5.0 if "材料" in theme or "玻璃基板" in theme or "人造金刚石" in theme else 0.0
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
        "order_landing_score": 60.0 if priority == "A" else 45.0 if priority == "B" else 35.0,
        "revenue_confirmation_score": 58.0 if priority == "A" else 42.0 if priority == "B" else 32.0,
        "customer_validation_score": 62.0 if priority == "A" else 46.0 if priority == "B" else 34.0,
        "story_to_earnings_score": 55.0 if priority == "A" else 40.0 if priority == "B" else 30.0,
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
    """Build ranking results from the existing core universe.

    The score engine uses deterministic research placeholders instead of
    external market data.
    """

    base_dir = Path(__file__).resolve().parents[1]
    core_universe_path = base_dir / "data" / "watchlists" / "a_share_core_universe.yaml"
    records = _load_core_universe(core_universe_path)
    results = [calculate_strategic_score(_build_demo_factor_payload(record)) for record in records]
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
