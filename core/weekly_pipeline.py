"""Weekly research pipeline.

This pipeline consumes the research universe and the integrated
research pipeline output, then generates a weekly report.
It does not depend on provider layers directly.
"""

from __future__ import annotations

import os
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
from src.agent_workflow.workflow_report import WorkflowReport
from src.agent_workflow.workflow_steps import build_default_workflow_engine
from src.backtest.backtest_contract import BacktestConfig
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.backtest_report import BacktestReport
from src.knowledge_base.kb_query import KBQuery
from src.knowledge_base.kb_summary import KBSummary
from src.knowledge_base.kb_store import DEFAULT_KB_STORE
from src.portfolio.portfolio_scoring_engine import PortfolioScoringEngine
from src.position.position_sizing_engine import PositionSizingEngine
from src.rebalancing.rebalance_contract import CurrentHolding
from src.rebalancing.rebalance_engine import RebalanceEngine
from src.risk.risk_management_engine import RiskManagementEngine
from src.provider_trust.trust_report import format_trust_ranking


WEEKLY_REPORT_LAYOUT_VERSION = 2


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
    if os.environ.get("CODEX_TEST_FAST") == "1":
        return records[:2]
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


def _risk_sections(portfolio_snapshot: dict[str, Any], position_snapshot: dict[str, Any]) -> dict[str, Any]:
    engine = RiskManagementEngine()
    report = engine.evaluate(position_snapshot, portfolio_snapshot, period="TTM")
    return engine.report_to_dict(report)


def _synthetic_current_holdings(position_snapshot: dict[str, Any]) -> list[CurrentHolding]:
    holdings: list[CurrentHolding] = []
    for index, item in enumerate(position_snapshot.get("recommendations", [])[:8]):
        symbol = str(item.get("symbol", "UNKNOWN"))
        target_weight = float(item.get("recommended_weight", 0.0))
        if index % 3 == 0:
            current_weight = 0.0
        elif index % 3 == 1:
            current_weight = min(target_weight * 1.25, 0.15)
        else:
            current_weight = max(0.0, target_weight * 0.85)
        market_value = round(current_weight * 1_000_000, 2)
        cost_basis = round(market_value / 1.05, 2) if market_value > 0 else 0.0
        unrealized_return = round((market_value - cost_basis) / cost_basis, 4) if cost_basis > 0 else 0.0
        holdings.append(
            CurrentHolding(
                symbol=symbol,
                current_weight=round(current_weight, 4),
                market_value=market_value,
                cost_basis=cost_basis,
                unrealized_return=unrealized_return,
            )
        )
    return holdings


def _rebalance_sections(
    portfolio_snapshot: dict[str, Any],
    position_snapshot: dict[str, Any],
    risk_report: dict[str, Any],
) -> dict[str, Any]:
    engine = RebalanceEngine()
    current_holdings = _synthetic_current_holdings(position_snapshot)
    plan = engine.build_plan(position_snapshot, risk_report, portfolio_snapshot, current_holdings, period="TTM")
    return engine.plan_to_dict(plan)


def _synthetic_backtest_prices(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    symbols = rows[:5]
    dates = [f"2026-06-{day:02d}" for day in range(1, 7)]
    price_data: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(symbols, start=1):
        base_price = 10.0 + index * 2.0
        drift = 0.002 + float(row["strategic_score"]) / 10000.0 + float(row.get("confidence_score", 0.0)) / 2000.0
        series: list[dict[str, Any]] = []
        for day_index, date in enumerate(dates):
            price = round(base_price * (1.0 + drift * day_index), 4)
            series.append({"date": date, "close": price})
        price_data[row["company_code"]] = series
    return price_data


def _backtest_sections(
    rows: list[dict[str, Any]],
    portfolio_snapshot: dict[str, Any],
    position_snapshot: dict[str, Any],
    rebalance_plan: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    engine = BacktestEngine()
    report = BacktestReport()
    config = BacktestConfig(
        start_date="2026-06-01",
        end_date="2026-06-06",
        initial_cash=1_000_000.0,
        rebalance_frequency="W",
        transaction_cost=0.001,
        slippage=0.001,
    )
    price_data = _synthetic_backtest_prices(rows)
    actions = [
        {
            "symbol": str(item.get("symbol", "UNKNOWN")),
            "target_weight": float(item.get("recommended_weight", 0.0)),
            "delta_weight": float(item.get("recommended_weight", 0.0)),
        }
        for item in position_snapshot.get("recommendations", [])[:5]
    ]
    historical_plans = [
        {
            "date": "2026-06-01",
            "actions": actions,
        }
    ]
    result = engine.run(price_data, historical_plans, config)
    summary = report.to_dict(result, config, rebalance_count=len(historical_plans))
    return summary, {
        "backtest_result": summary,
        "backtest_summary": {
            "period": summary["period"],
            "total_return": summary["metrics"]["total_return"],
            "annualized_return": summary["metrics"]["annualized_return"],
            "max_drawdown": summary["metrics"]["max_drawdown"],
        },
        "backtest_metrics": summary["metrics"],
    }


def _knowledge_base_sections(rows: list[dict[str, Any]]) -> dict[str, Any]:
    query = KBQuery()
    summary = KBSummary(query)
    latest_records = [query.store.get_latest_by_symbol(row["company_code"]) for row in rows[:5]]
    latest_records = [record for record in latest_records if record is not None]
    symbol_list = [row["company_code"] for row in rows[:3]]
    return {
        "knowledge_base_records": [
            {
                "record_id": record.record_id,
                "symbol": record.symbol,
                "period": record.period,
                "strategic_score": record.strategic_score,
                "final_decision": record.final_decision,
                "confidence_score": record.confidence_score,
                "portfolio_bucket": record.portfolio_bucket,
                "recommended_weight": record.recommended_weight,
                "risk_level": record.risk_level,
                "rebalance_action": record.rebalance_action,
                "created_at": record.created_at,
            }
            for record in latest_records
        ],
        "historical_score_changes": {
            symbol: summary.score_trend(symbol)
            for symbol in symbol_list
        },
        "historical_decision_changes": {
            symbol: summary.decision_history(symbol)
            for symbol in symbol_list
        },
    }


def _workflow_sections(
    rows: list[dict[str, Any]],
    portfolio_snapshot: dict[str, Any],
    position_snapshot: dict[str, Any],
    risk_report: dict[str, Any],
    rebalance_plan: dict[str, Any],
    backtest_payload: dict[str, Any],
) -> dict[str, Any]:
    symbols = [row["company_code"] for row in rows[:3]]
    workflow_engine = build_default_workflow_engine()
    workflow_run = workflow_engine.run_workflow(
        period="TTM",
        symbols=symbols,
        context={
            "rows": rows,
            "portfolio_snapshot": portfolio_snapshot,
            "position_snapshot": position_snapshot,
            "risk_report": risk_report,
            "rebalance_plan": rebalance_plan,
            "backtest_result": backtest_payload,
        },
    )
    workflow_report = WorkflowReport()
    workflow_dict = workflow_report.to_dict(workflow_run)
    return {
        "workflow_run": workflow_dict,
        "workflow_summary": workflow_dict["summary"],
        "workflow_errors": workflow_dict["error_summary"],
        "workflow_warnings": workflow_dict["warning_summary"],
    }


def _quality_sections() -> dict[str, Any]:
    from src.quality.quality_gate import QualityGate

    report = QualityGate().run()
    checks = [
        {
            "check_name": item.check_name,
            "status": item.status,
            "message": item.message,
            "severity": item.severity,
        }
        for item in report.checks
    ]
    return {
        "quality_report": {
            "timestamp": report.timestamp,
            "checks": checks,
            "passed_count": report.passed_count,
            "failed_count": report.failed_count,
            "warnings": list(report.warnings),
            "rc1_ready": report.rc1_ready,
        },
        "rc1_status": "READY" if report.rc1_ready else "NOT_READY",
    }


def _generate_weekly_report(base_dir: Path) -> Path:
    rows = build_weekly_report_data()
    trust_scores = _trust_snapshot()
    _write_csv(base_dir / "reports" / "weekly_report.csv", rows)

    focus = _theme_focus(rows)
    catalyst_changes, order_changes, watchlist_changes = _changes_summary(rows)
    risk_alerts = _risk_alerts(rows)
    top_confidence, low_confidence, confidence_warnings = _confidence_sections(rows)
    portfolio_snapshot = _portfolio_sections(rows)
    position_snapshot = _position_sections(portfolio_snapshot)
    risk_report = _risk_sections(portfolio_snapshot, position_snapshot)
    rebalance_plan = _rebalance_sections(portfolio_snapshot, position_snapshot, risk_report)
    backtest_report, backtest_payload = _backtest_sections(rows, portfolio_snapshot, position_snapshot, rebalance_plan)
    kb_sections = _knowledge_base_sections(rows)
    workflow_sections = _workflow_sections(rows, portfolio_snapshot, position_snapshot, risk_report, rebalance_plan, backtest_payload)
    quality_sections = _quality_sections()

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
    lines.append("## 26. Risk Report")
    lines.append(f"- level={risk_report.get('risk_level', 'LOW')} score={risk_report.get('total_risk_score', 0.0):.2f}")
    lines.append("")
    lines.append("## 27. Risk Warnings")
    for item in risk_report.get("warnings", []):
        lines.append(f"- {item}")
    if not risk_report.get("warnings"):
        lines.append("- none")
    lines.append("")
    lines.append("## 28. Risk Suggested Actions")
    for item in risk_report.get("suggested_actions", []):
        lines.append(f"- {item}")
    if not risk_report.get("suggested_actions"):
        lines.append("- none")
    lines.append("")
    lines.append("## 29. Rebalance Plan")
    lines.append(f"- {rebalance_plan.get('summary', '')}")
    lines.append("")
    lines.append("## 30. Rebalance Actions")
    for item in rebalance_plan.get("actions", []):
        lines.append(
            f"- {item['priority']}. {item['symbol']} {item['action']} {item['current_weight'] * 100:.1f}% -> {item['target_weight'] * 100:.1f}%"
        )
    if not rebalance_plan.get("actions"):
        lines.append("- none")
    lines.append("")
    lines.append("## 31. Buy List")
    buy_list = [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"BUY", "ADD"}]
    for item in buy_list:
        lines.append(f"- {item['symbol']} {item['action']} {item['target_weight'] * 100:.1f}%")
    if not buy_list:
        lines.append("- none")
    lines.append("")
    lines.append("## 32. Sell List")
    sell_list = [item for item in rebalance_plan.get("actions", []) if item.get("action") == "SELL"]
    for item in sell_list:
        lines.append(f"- {item['symbol']} SELL")
    if not sell_list:
        lines.append("- none")
    lines.append("")
    lines.append("## 33. Reduce List")
    reduce_list = [item for item in rebalance_plan.get("actions", []) if item.get("action") == "REDUCE"]
    for item in reduce_list:
        lines.append(f"- {item['symbol']} REDUCE")
    if not reduce_list:
        lines.append("- none")
    lines.append("")
    lines.append("## 34. Add List")
    add_list = [item for item in rebalance_plan.get("actions", []) if item.get("action") == "ADD"]
    for item in add_list:
        lines.append(f"- {item['symbol']} ADD")
    if not add_list:
        lines.append("- none")
    lines.append("")
    lines.append("## 35. Hold List")
    hold_list = [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"HOLD", "WATCH"}]
    for item in hold_list:
        lines.append(f"- {item['symbol']} {item['action']}")
    if not hold_list:
        lines.append("- none")
    lines.append("")
    lines.append("## 36. Backtest Result")
    lines.append(f"- {backtest_report.get('period', '')}")
    lines.append("")
    lines.append("## 37. Backtest Summary")
    backtest_summary = backtest_payload["backtest_summary"]
    lines.append(f"- total_return: {backtest_summary['total_return']:.4f}")
    lines.append(f"- annualized_return: {backtest_summary['annualized_return']:.4f}")
    lines.append(f"- max_drawdown: {backtest_summary['max_drawdown']:.4f}")
    lines.append("")
    lines.append("## 38. Backtest Metrics")
    backtest_metrics = backtest_payload["backtest_metrics"]
    lines.append(f"- volatility: {backtest_metrics['volatility']:.4f}")
    lines.append(f"- sharpe_ratio: {backtest_metrics['sharpe_ratio']:.4f}")
    lines.append(f"- turnover: {backtest_metrics['turnover']:.4f}")
    lines.append(f"- win_rate: {backtest_metrics['win_rate']:.4f}")
    lines.append("")
    lines.append("## 39. Backtest Warnings")
    if backtest_report.get("warnings"):
        for item in backtest_report["warnings"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 40. Knowledge Base Records")
    for item in kb_sections["knowledge_base_records"]:
        lines.append(
            f"- {item['symbol']} {item['period']} score={item['strategic_score']:.2f} "
            f"decision={item['final_decision']} confidence={item['confidence_score']:.2f}"
        )
    if not kb_sections["knowledge_base_records"]:
        lines.append("- none")
    lines.append("")
    lines.append("## 41. Historical Score Changes")
    for symbol, history in kb_sections["historical_score_changes"].items():
        lines.append(f"- {symbol}")
        for item in history:
            lines.append(f"  - {item['period']}: {item['strategic_score']:.2f}")
    if not kb_sections["historical_score_changes"]:
        lines.append("- none")
    lines.append("")
    lines.append("## 42. Historical Decision Changes")
    for symbol, history in kb_sections["historical_decision_changes"].items():
        lines.append(f"- {symbol}")
        for item in history:
            lines.append(f"  - {item}")
    if not kb_sections["historical_decision_changes"]:
        lines.append("- none")
    lines.append("")
    lines.append("## 43. Workflow Summary")
    lines.append(f"- {workflow_sections['workflow_summary']}")
    lines.append("")
    lines.append("## 44. Workflow Status")
    lines.append(f"- {workflow_sections['workflow_run']['final_status']}")
    lines.append("")
    lines.append("## 45. Workflow Warnings")
    if workflow_sections["workflow_warnings"]:
        for item in workflow_sections["workflow_warnings"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 46. Workflow Errors")
    if workflow_sections["workflow_errors"]:
        for item in workflow_sections["workflow_errors"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## 47. Quality Report")
    quality_report = quality_sections["quality_report"]
    lines.append(f"- rc1_ready: {quality_report['rc1_ready']}")
    lines.append(f"- passed_count: {quality_report['passed_count']}")
    lines.append(f"- failed_count: {quality_report['failed_count']}")
    lines.append("")
    lines.append("## 48. RC1 Status")
    lines.append(f"- {quality_sections['rc1_status']}")
    lines.append("")

    output_path = base_dir / "reports" / "weekly_report.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


_WEEKLY_REPORT_CACHE: dict[tuple[int, int], Path] = {}


def generate_weekly_report() -> Path:
    """Generate weekly report markdown and companion CSV."""

    base_dir = Path(__file__).resolve().parents[1]
    cache_key = (DEFAULT_KB_STORE.kb.version, WEEKLY_REPORT_LAYOUT_VERSION)
    cached = _WEEKLY_REPORT_CACHE.get(cache_key)
    if cached is not None and cached.exists():
        return cached
    path = _generate_weekly_report(base_dir)
    _WEEKLY_REPORT_CACHE[cache_key] = path
    return path
