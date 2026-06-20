"""Weekly research pipeline.

This pipeline consumes the research universe and the integrated
research pipeline output, then generates a weekly report.
It does not depend on provider layers directly.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import csv

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to run the weekly pipeline") from exc

from core.research_engine import run_research_pipeline
from core.provider_router import ProviderRouter
from src.portfolio.portfolio_scoring_engine import PortfolioScoringEngine
from src.position.position_sizing_engine import PositionSizingEngine
from src.provider_trust.trust_report import format_trust_ranking


@dataclass(frozen=True)
class WeeklyReportRow:
    company_code: str
    name: str
    theme: str
    strategic_score: float
    catalyst_strength: float
    order_confirmation_level: float
    risk_summary: str
    research_conclusion: str


def _load_universe(base_dir: Path) -> list[dict[str, Any]]:
    path = base_dir / "data" / "watchlists" / "a_share_core_universe.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    records: list[dict[str, Any]] = []
    for theme_entry in payload.get("themes", []):
        theme_name = str(theme_entry.get("theme_name", ""))
        for item in theme_entry.get("items", []):
            records.append(
                {
                    "code": str(item.get("code", "")),
                    "name": str(item.get("name", "")),
                    "theme": str(item.get("theme", theme_name)),
                    "watch_priority": str(item.get("watch_priority", "C")),
                }
            )
    return records


def build_weekly_report_data() -> list[dict[str, Any]]:
    """Run research pipeline for the core universe and collect results."""

    base_dir = Path(__file__).resolve().parents[1]
    universe = _load_universe(base_dir)
    rows: list[dict[str, Any]] = []
    for record in universe:
        result = run_research_pipeline(record["code"])
        factor_confidences = result.get("factor_confidences", {})
        confidence_values = [
            float(item.get("final_confidence", 0.0))
            for item in factor_confidences.values()
            if isinstance(item, dict)
        ]
        confidence_score = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        if confidence_score >= 0.75 and float(result["strategic_score"]) >= 75:
            final_decision = "BUY"
        elif confidence_score < 0.50:
            final_decision = "AVOID"
        elif float(result["strategic_score"]) >= 60:
            final_decision = "WATCH"
        else:
            final_decision = "REVIEW"
        rows.append(
            {
                "company_code": record["code"],
                "name": record["name"],
                "theme": record["theme"],
                "watch_priority": record["watch_priority"],
                "period": "TTM",
                "strategic_score": float(result["strategic_score"]),
                "confidence_score": confidence_score,
                "final_decision": final_decision,
                "catalyst_strength": float(result["catalyst_strength"]),
                "order_confirmation_level": float(result["order_confirmation_level"]),
                "risk_summary": str(result["risk_summary"]),
                "research_conclusion": str(result["research_conclusion"]),
                "factor_input_summary": result["factor_input_summary"],
                "factor_scores": result["factor_scores"],
                "theme_exposure": result["theme_exposure"],
                "evidence_summary": result.get("evidence_summary", {}),
                "score_explanation": result.get("score_explanation", {}),
                "decision_explanation": result.get("decision_explanation", {}),
                "factor_confidences": result.get("factor_confidences", {}),
                "evidence_refs": result.get("evidence_refs", {}),
            }
        )
    return sorted(rows, key=lambda row: row["strategic_score"], reverse=True)


def build_portfolio_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    engine = PortfolioScoringEngine()
    candidates = [
        {
            "symbol": row["company_code"],
            "period": row.get("period", "TTM"),
            "strategic_score": row["strategic_score"],
            "confidence_score": row.get("confidence_score", 0.0),
            "final_decision": row.get("final_decision", "WATCH"),
            "risk_score": min(1.0, max(0.0, 1.0 - min(float(row["strategic_score"]), 100.0) / 100.0)),
            "evidence_refs": row.get("evidence_refs", {}),
            "explanation": row.get("research_conclusion", ""),
        }
        for row in rows
    ]
    snapshot = engine.build_snapshot(candidates, period="TTM")
    return engine.snapshot_to_dict(snapshot)


def _trust_snapshot() -> list[dict[str, Any]]:
    router = ProviderRouter()
    return router.get_provider_trust_scores()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "company_code",
                "name",
                "theme",
                "strategic_score",
                "catalyst_strength",
                "order_confirmation_level",
                "watch_priority",
            ]
        )
        for rank, row in enumerate(rows, start=1):
            writer.writerow(
                [
                    rank,
                    row["company_code"],
                    row["name"],
                    row["theme"],
                    f"{row['strategic_score']:.2f}",
                    f"{row['catalyst_strength']:.2f}",
                    f"{row['order_confirmation_level']:.2f}",
                    row["watch_priority"],
                ]
            )


def _theme_focus(rows: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counter = Counter(row["theme"] for row in rows[:10])
    return counter.most_common(5)


def _risk_alerts(rows: list[dict[str, Any]]) -> list[str]:
    alerts: list[str] = []
    for row in rows[:10]:
        if row["order_confirmation_level"] < 45:
            alerts.append(f"{row['name']} 订单验证偏弱")
        if row["catalyst_strength"] < 45:
            alerts.append(f"{row['name']} 催化强度偏弱")
    return alerts[:8]


def _confidence_sections(rows: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    scored: list[tuple[str, float]] = []
    warnings: list[str] = []
    for row in rows[:10]:
        factor_confidences = row.get("factor_confidences", {})
        if isinstance(factor_confidences, dict):
            for factor_name, item in factor_confidences.items():
                if not isinstance(item, dict):
                    continue
                final_conf = float(item.get("final_confidence", 0.0))
                scored.append((f"{row['name']}::{factor_name}", final_conf))
                if final_conf < 0.65:
                    warnings.append(f"{row['name']} {factor_name} 置信度偏低 {final_conf:.2f}")
    scored_sorted = sorted(scored, key=lambda item: item[1], reverse=True)
    top_conf = [f"- {name} {score:.2f}" for name, score in scored_sorted[:5]]
    low_conf = [f"- {name} {score:.2f}" for name, score in sorted(scored, key=lambda item: item[1])[:5]]
    return top_conf, low_conf, warnings[:8]


def _changes_summary(rows: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    catalyst_changes: list[str] = []
    order_changes: list[str] = []
    watchlist_changes: list[str] = []
    for row in rows[:5]:
        if row["catalyst_strength"] >= 60:
            catalyst_changes.append(f"{row['name']} 催化强度较强")
        if row["order_confirmation_level"] >= 60:
            order_changes.append(f"{row['name']} 订单验证较强")
        if row["watch_priority"] == "A":
            watchlist_changes.append(f"{row['name']} 保持重点观察")
    return catalyst_changes, order_changes, watchlist_changes


def _portfolio_sections(rows: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = build_portfolio_snapshot(rows)
    return snapshot


def _position_sections(portfolio_snapshot: dict[str, Any]) -> dict[str, Any]:
    engine = PositionSizingEngine()
    candidates = []
    for item in portfolio_snapshot.get("ranked_candidates", [])[:10]:
        candidates.append(
            {
                "symbol": item.get("symbol", "UNKNOWN"),
                "bucket": item.get("bucket", "WATCHLIST"),
                "strategic_score": item.get("strategic_score", 0.0),
                "confidence_score": item.get("confidence_score", 0.0),
                "risk_score": min(1.0, max(0.0, 1.0 - float(item.get("total_score", 0.0)) / 100.0)),
                "evidence_refs": {},
            }
        )
    snapshot = engine.build_snapshot(candidates, period="TTM")
    return engine.snapshot_to_dict(snapshot)


def generate_weekly_report() -> Path:
    """Generate weekly report markdown and companion CSV."""

    base_dir = Path(__file__).resolve().parents[1]
    rows = build_weekly_report_data()
    trust_scores = _trust_snapshot()
    _write_csv(base_dir / "reports" / "weekly_report.csv", rows)

    focus = _theme_focus(rows)
    catalyst_changes, order_changes, watchlist_changes = _changes_summary(rows)
    risk_alerts = _risk_alerts(rows)
    top_confidence, low_confidence, confidence_warnings = _confidence_sections(rows)
    portfolio_snapshot = _portfolio_sections(rows)
    position_snapshot = _position_sections(portfolio_snapshot)

    lines: list[str] = []
    lines.append("# Weekly Research Report")
    lines.append("")
    lines.append("## 1. 本周重点主题")
    for theme, count in focus:
        lines.append(f"- {theme} ({count})")
    lines.append("")
    lines.append("## 2. Strategic Score Top10")
    for rank, row in enumerate(rows[:10], start=1):
        lines.append(
            f"{rank}. {row['name']} ({row['company_code']}) - {row['theme']} - {row['strategic_score']:.2f}"
        )
    lines.append("")
    lines.append("## 3. Catalyst Changes")
    if catalyst_changes:
        for item in catalyst_changes:
            lines.append(f"- {item}")
    else:
        lines.append("- 本周未见显著催化变化")
    lines.append("")
    lines.append("## 4. Order Confirmation Changes")
    if order_changes:
        for item in order_changes:
            lines.append(f"- {item}")
    else:
        lines.append("- 本周未见显著订单验证变化")
    lines.append("")
    lines.append("## 5. Risk Alerts")
    if risk_alerts:
        for item in risk_alerts:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无显著风险提示")
    lines.append("")
    lines.append("## 6. Watchlist Changes")
    if watchlist_changes:
        for item in watchlist_changes:
            lines.append(f"- {item}")
    else:
        lines.append("- 重点观察池保持稳定")
    lines.append("")
    lines.append("## 7. Research Conclusions")
    for rank, row in enumerate(rows[:10], start=1):
        lines.append(f"- {rank}. {row['name']}: {row['research_conclusion']}")
    lines.append("")
    lines.append("## 8. Evidence Summary")
    for rank, row in enumerate(rows[:5], start=1):
        evidence = row.get("evidence_summary", {})
        lines.append(f"- {rank}. {row['name']} overall_confidence={evidence.get('overall_confidence', 0.0):.2f}")
    lines.append("")
    lines.append("## 9. Score Explanation")
    for rank, row in enumerate(rows[:5], start=1):
        score_explanation = row.get("score_explanation", {})
        lines.append(f"- {rank}. {row['name']}: {score_explanation.get('score_explanation', score_explanation)}")
    lines.append("")
    lines.append("## 10. Decision Explanation")
    for rank, row in enumerate(rows[:5], start=1):
        decision_explanation = row.get("decision_explanation", {})
        lines.append(f"- {rank}. {row['name']}: {decision_explanation.get('decision_explanation', decision_explanation)}")
    lines.append("")
    lines.append("## 11. Provider Trust Ranking")
    for rank, item in enumerate(trust_scores, start=1):
        lines.append(f"- {rank}. {item['provider_name']} {item['overall_score']:.2f}")
    lines.append("")
    lines.append("## 12. Trust Warnings")
    trust_warnings = [f"{item['provider_name']} trust={item['overall_score']:.2f}" for item in trust_scores if item["overall_score"] < 0.9]
    if trust_warnings:
        for item in trust_warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 13. Top Confidence Factors")
    if top_confidence:
        lines.extend(top_confidence)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 14. Lowest Confidence Factors")
    if low_confidence:
        lines.extend(low_confidence)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 15. Confidence Warnings")
    if confidence_warnings:
        lines.extend(confidence_warnings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 16. Portfolio Snapshot")
    lines.append(f"- {portfolio_snapshot.get('summary', '')}")
    lines.append("")
    lines.append("## 17. Portfolio Ranking")
    for item in portfolio_snapshot.get("ranked_candidates", [])[:10]:
        lines.append(
            f"- {item['rank']}. {item['symbol']} {item['bucket']} total={item['total_score']:.2f} conf={item['confidence_score']:.2f}"
        )
    lines.append("")
    lines.append("## 18. Core Candidates")
    for item in portfolio_snapshot.get("core_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("core_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("## 19. Satellite Candidates")
    for item in portfolio_snapshot.get("satellite_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("satellite_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("## 20. Watchlist Candidates")
    for item in portfolio_snapshot.get("watchlist_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("watchlist_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("## 21. Excluded Candidates")
    for item in portfolio_snapshot.get("excluded_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("excluded_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("## 22. Position Snapshot")
    lines.append(f"- {position_snapshot.get('allocation_summary', '')}")
    lines.append("")
    lines.append("## 23. Recommended Positions")
    for item in position_snapshot.get("recommendations", [])[:10]:
        lines.append(
            f"- {item['symbol']} {item['bucket']} {item['recommended_weight'] * 100:.1f}%"
        )
    if not position_snapshot.get("recommendations"):
        lines.append("- none")
    lines.append("")
    lines.append("## 24. Top Allocations")
    top_allocations = sorted(position_snapshot.get("recommendations", []), key=lambda item: item.get("recommended_weight", 0.0), reverse=True)[:5]
    for item in top_allocations:
        lines.append(f"- {item['symbol']} {item['recommended_weight'] * 100:.1f}%")
    if not top_allocations:
        lines.append("- none")
    lines.append("")
    lines.append("## 25. Cash Remaining")
    lines.append(f"- {position_snapshot.get('remaining_cash', 0.0) * 100:.1f}%")
    lines.append("")

    output_path = base_dir / "reports" / "weekly_report.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
