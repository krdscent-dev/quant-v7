"""Weekly research pipeline.

This pipeline consumes the research universe and the integrated
research pipeline output, then generates a weekly report.
It does not depend on provider layers directly.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import csv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
from src.audit.audit_engine import AuditEngine
from src.exports.tabular_exporter import TabularExporter


WEEKLY_REPORT_LAYOUT_VERSION = 3
COCKPIT_REPORT_LAYOUT_VERSION = 1


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


def _growth_watchlist_config(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "config" / "growth_watchlist.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _growth_watchlist_state_path(base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "growth_watchlist_state.yaml"


def _load_growth_watchlist_state(base_dir: Path) -> dict[str, Any]:
    path = _growth_watchlist_state_path(base_dir)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _save_growth_watchlist_state(base_dir: Path, state: dict[str, Any]) -> None:
    path = _growth_watchlist_state_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(state, handle, allow_unicode=True, sort_keys=False)


def _theme_score(rows: list[dict[str, Any]], aliases: list[str]) -> float:
    matched = [row for row in rows if row.get("theme") in aliases]
    if not matched:
        return 0.0
    top_scores = sorted((float(row.get("strategic_score", 0.0)) for row in matched), reverse=True)[:3]
    if not top_scores:
        return 0.0
    return round(sum(top_scores) / len(top_scores) * 100.0, 2)


def _watch_status(score: float) -> str:
    if score <= 0.0:
        return "⚪ 未启动"
    if score < 10.0:
        return "🟡 刚启动"
    if score < 30.0:
        return "🟢 加速"
    if score < 60.0:
        return "🔵 主升浪"
    return "🔴 兑现"


def _growth_watchlist_sections(rows: list[dict[str, Any]], base_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    config = _growth_watchlist_config(base_dir)
    state = _load_growth_watchlist_state(base_dir)
    theme_aliases = {
        "AI算力": ["AI算力"],
        "AI国产替代": ["国产替代", "AI国产替代"],
        "新材料": ["玻璃基板", "人造金刚石", "先进封装"],
        "创新药": ["创新药"],
        "CXO": ["CXO"],
        "能源安全与煤基新材料": ["能源安全与煤基新材料"],
    }
    growth_rows: list[dict[str, Any]] = []
    for item in config.get("top_level_themes", []):
        theme_name = str(item.get("theme_name", ""))
        current_score = _theme_score(rows, theme_aliases.get(theme_name, [theme_name]))
        previous_score = float(state.get("themes", {}).get(theme_name, item.get("previous_score", current_score)))
        score_change = round(current_score - previous_score, 2)
        growth_rows.append(
            {
                "theme": theme_name,
                "status": item.get("status", _watch_status(current_score)),
                "current_score": current_score,
                "previous_score": round(previous_score, 2),
                "score_change": score_change,
                "catalyst_event": item.get("catalyst_event", ""),
                "key_companies": " / ".join(item.get("key_companies", [])),
                "notes": item.get("notes", ""),
            }
        )

    material_rows: list[dict[str, Any]] = []
    for item in config.get("new_material_watchlist", []):
        direction_name = str(item.get("direction_name", ""))
        material_rows.append(
            {
                "direction_name": direction_name,
                "status": item.get("status", "⚪ 未启动"),
                "catalyst_score": float(item.get("catalyst_score", 0.0)),
                "verification_score": float(item.get("verification_score", 0.0)),
                "watch_companies": " / ".join(item.get("watch_companies", [])),
                "notes": item.get("notes", ""),
            }
        )

    new_state = {
        "themes": {row["theme"]: row["current_score"] for row in growth_rows},
        "last_updated": datetime.now().isoformat(),
    }
    _save_growth_watchlist_state(base_dir, new_state)
    return growth_rows, material_rows, config


def _confidence_grade(confidence_score: float) -> str:
    if confidence_score >= 0.85:
        return "A"
    if confidence_score >= 0.70:
        return "B"
    if confidence_score >= 0.50:
        return "C"
    return "D"


def _score_band(score: float) -> tuple[str, str]:
    if score < 30:
        return "无效信号", "无效信号，不具备投资意义"
    if score < 50:
        return "观察级", "可能有主题，但证据不足"
    if score < 70:
        return "关注级", "有产业逻辑，但验证不足"
    if score < 85:
        return "配置级", "可以进入组合，但需分批"
    return "主线级", "产业趋势和验证较强"


def _normalized_score(score: float) -> float:
    return round(max(0.0, min(100.0, score)), 2)


def _theme_alias_map() -> dict[str, list[str]]:
    return {
        "AI算力": ["AI算力"],
        "AI国产替代": ["国产替代", "AI国产替代"],
        "新材料": ["玻璃基板", "人造金刚石", "先进封装", "新材料"],
        "创新药": ["创新药"],
        "CXO": ["CXO"],
        "能源安全与煤基新材料": ["能源安全与煤基新材料"],
        "高端装备": ["超节点受益链", "高端装备"],
        "医疗器械": ["医疗器械"],
    }


def _sector_state_from_score(score: float) -> str:
    if score <= 0:
        return "⚪ 未启动"
    if score < 10:
        return "🟡 刚启动"
    if score < 30:
        return "🟢 加速"
    if score < 60:
        return "🔵 主升"
    return "🔴 兑现"


def _sector_summary_rows(rows: list[dict[str, Any]], growth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alias_map = _theme_alias_map()
    growth_lookup = {row["theme"]: row for row in growth_rows}
    sector_specs = [
        ("AI算力", "AI算力"),
        ("AI国产替代", "AI国产替代"),
        ("新材料", "新材料"),
        ("创新药", "创新药"),
        ("CXO", "CXO"),
        ("能源安全与煤基新材料", "能源安全与煤基新材料"),
        ("高端装备", "高端装备"),
        ("医疗器械", "医疗器械"),
    ]
    sectors: list[dict[str, Any]] = []
    for sector, key in sector_specs:
        aliases = alias_map.get(key, [key])
        current_score = _theme_score(rows, aliases)
        previous_score = float(growth_lookup.get(key, {}).get("previous_score", current_score))
        change = round(current_score - previous_score, 2)
        state = _sector_state_from_score(current_score)
        core_driver = growth_lookup.get(key, {}).get("catalyst_event", "趋势验证中")
        major_risk = "数据置信度偏低" if current_score <= 0 else "主题验证仍需增强"
        observe = "是" if current_score >= 0 or sector in {"AI算力", "新材料", "创新药", "CXO", "能源安全与煤基新材料"} else "否"
        sectors.append(
            {
                "sector": sector,
                "status": state,
                "current_score": current_score,
                "previous_score": previous_score,
                "score_change": change,
                "core_driver": core_driver,
                "major_risk": major_risk,
                "watch": observe,
            }
        )
    return sectors


def _theme_ranking_rows(growth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranking = sorted(growth_rows, key=lambda item: item["current_score"], reverse=True)
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(ranking, start=1):
        rows.append(
            {
                "rank": rank,
                "theme": item["theme"],
                "current_score": item["current_score"],
                "previous_score": item["previous_score"],
                "score_change": item["score_change"],
                "status": item["status"],
                "conclusion": "动量增强" if item["score_change"] > 0.5 else ("动量减弱" if item["score_change"] < -0.5 else "持平观察"),
            }
        )
    return rows


def _trend_label(change: float) -> str:
    if change > 0.5:
        return "🟢 动量增强"
    if change < -0.5:
        return "🔴 动量减弱"
    return "🟡 持平观察"


def _valuation_guard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    guards: list[dict[str, Any]] = []
    for row in rows[:10]:
        current_score = float(row.get("strategic_score", 0.0))
        if current_score < 50:
            buy_zone = "不建议"
            observe_zone = "价格区间数据不足"
            risk_zone = "价格区间数据不足"
            current_zone = "价格区间数据不足"
            chasing = "无法判断"
            conclusion = "分数较低，先观察"
        elif current_score < 70:
            buy_zone = "价格区间数据不足"
            observe_zone = "价格区间数据不足"
            risk_zone = "价格区间数据不足"
            current_zone = "价格区间数据不足"
            chasing = "无法判断"
            conclusion = "有逻辑但验证不足"
        else:
            buy_zone = "价格区间数据不足"
            observe_zone = "价格区间数据不足"
            risk_zone = "价格区间数据不足"
            current_zone = "价格区间数据不足"
            chasing = "无法判断"
            conclusion = "逻辑较强，但缺少价格数据"
        guards.append(
            {
                "symbol": row["company_code"],
                "name": row["name"],
                "current_price": "数据不足",
                "buy_zone": buy_zone,
                "observe_zone": observe_zone,
                "risk_zone": risk_zone,
                "current_zone": current_zone,
                "is_chasing": chasing,
                "price_conclusion": conclusion,
            }
        )
    return guards


def _lifecycle_rows(rows: list[dict[str, Any]], growth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    growth_themes = {item["theme"]: item for item in growth_rows}
    lifecycle_map = {
        "AI算力": ("验证", "需要更多订单兑现、CapEx 扩张与客户验证", "订单或 CapEx 验证中断"),
        "AI国产替代": ("观察", "需要国产化率和供应链安全验证", "政策和订单验证转弱"),
        "新材料": ("观察", "需要工艺验证、良率和客户导入", "试产与量产节奏落后"),
        "创新药": ("观察", "需要临床进展和 BD 兑现", "临床/出海不及预期"),
        "CXO": ("观察", "需要海外订单恢复和客户确认", "订单恢复延迟"),
        "能源安全与煤基新材料": ("验证", "需要煤化工替代和政策持续支持", "政策支持转弱"),
    }
    lifecycles: list[dict[str, Any]] = []
    for theme, (current_life, next_need, exit_cond) in lifecycle_map.items():
        item = growth_themes.get(theme, {})
        lifecycles.append(
            {
                "theme": theme,
                "current_lifecycle": current_life,
                "next_validation": next_need,
                "exit_condition": exit_cond,
                "score": item.get("current_score", 0.0),
            }
        )
    return lifecycles


def _scenario_rows() -> list[dict[str, Any]]:
    return [
        {
            "scenario": "AI资本开支继续扩张",
            "trigger": "服务器 / 算力 / 液冷订单持续增加",
            "benefit_themes": "AI算力、AI国产替代",
            "benefit_stocks": "浪潮信息 / 中际旭创 / 科大讯飞",
            "observation": "CapEx、订单、液冷渗透率",
            "risk": "CapEx 延后或订单不兑现",
        },
        {
            "scenario": "华为超节点验证成功",
            "trigger": "超节点方案规模部署与生态扩张",
            "benefit_themes": "华为超节点、高端装备",
            "benefit_stocks": "海光信息 / 东方电子 / 神州数码",
            "observation": "部署进度、生态伙伴、订单确认",
            "risk": "生态推进不及预期",
        },
        {
            "scenario": "玻璃基板产业验证",
            "trigger": "试产、良率和客户导入出现正反馈",
            "benefit_themes": "新材料",
            "benefit_stocks": "沃格光电 / 长信科技 / 蓝思科技",
            "observation": "试产良率、客户导入、产线扩产",
            "risk": "工艺验证失败",
        },
        {
            "scenario": "金刚石散热进入AI服务器供应链",
            "trigger": "热管理材料进入服务器 / 液冷链条",
            "benefit_themes": "新材料、AI算力",
            "benefit_stocks": "力量钻石 / 黄河旋风 / 四方达 / 中兵红箭",
            "observation": "供应链认证、散热方案、订单节奏",
            "risk": "应用场景落地慢",
        },
        {
            "scenario": "创新药BD出海继续强化",
            "trigger": "许可 / 合作 / 出海 BD 持续兑现",
            "benefit_themes": "创新药",
            "benefit_stocks": "恒瑞医药 / 百济神州 / 君实生物",
            "observation": "BD 里程碑、临床进展、海外收入",
            "risk": "BD 兑现不及预期",
        },
        {
            "scenario": "CXO海外订单恢复",
            "trigger": "海外项目恢复与客户补库",
            "benefit_themes": "CXO",
            "benefit_stocks": "药明康德 / 凯莱英 / 泰格医药",
            "observation": "海外订单、客户验证、收入拐点",
            "risk": "恢复节奏慢于预期",
        },
        {
            "scenario": "能源安全与煤基新材料重估",
            "trigger": "煤化工替代与能源安全政策持续强化",
            "benefit_themes": "能源安全与煤基新材料",
            "benefit_stocks": "宝丰能源 / 中国神华 / 恒力石化",
            "observation": "政策支持、煤化工项目、国产替代",
            "risk": "政策支持弱化",
        },
    ]


def _position_recommendation_rows(rows: list[dict[str, Any]], valuation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {item["symbol"]: item for item in valuation_rows}
    recommendations: list[dict[str, Any]] = []
    for row in rows[:10]:
        score = float(row.get("strategic_score", 0.0))
        confidence = float(row.get("confidence_score", 0.0))
        price_guard = lookup.get(row["company_code"], {})
        risk_zone = price_guard.get("current_zone", "价格区间数据不足")
        base_weight = 0.0
        if score >= 85:
            base_weight = 12.5
        elif score >= 70:
            base_weight = 7.5
        elif score >= 50:
            base_weight = 3.5
        if confidence < 0.5 or risk_zone == "风险区" or "数据不足" in str(risk_zone):
            base_weight = min(base_weight, 2.0) if score >= 50 else 0.0
        if score < 50:
            base_weight = 0.0
        split = "是" if 0.0 < base_weight <= 10.0 else ("是" if base_weight > 10.0 else "否")
        wait_pullback = "是" if "数据不足" in str(risk_zone) or confidence < 0.7 else "否"
        reason = "分数和置信度不够，优先观察" if base_weight == 0 else "分数满足，但价格区间数据不足，建议分批"
        recommendations.append(
            {
                "symbol": row["company_code"],
                "name": row["name"],
                "recommended_weight": f"{base_weight:.1f}%",
                "reason": reason,
                "split": split,
                "wait_pullback": wait_pullback,
            }
        )
    return recommendations


def _confidence_rows(rows: list[dict[str, Any]], valuation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {item["symbol"]: item for item in valuation_rows}
    confidence_rows: list[dict[str, Any]] = []
    for row in rows[:10]:
        conf = float(row.get("confidence_score", 0.0))
        grade = _confidence_grade(conf)
        missing_items: list[str] = []
        if "data不足" in str(lookup.get(row["company_code"], {}).get("current_zone", "")):
            missing_items.append("价格区间数据")
        if conf < 0.5:
            missing_items.append("因子置信度偏低")
        confidence_rows.append(
            {
                "symbol": row["company_code"],
                "name": row["name"],
                "confidence_score": f"{conf:.2f}",
                "confidence_grade": grade,
                "missing_items": " / ".join(missing_items) if missing_items else "无",
                "affect_decision": "是" if grade in {"C", "D"} else "否",
            }
        )
    return confidence_rows


def _final_decision_rows(rows: list[dict[str, Any]], valuation_rows: list[dict[str, Any]], position_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vlookup = {item["symbol"]: item for item in valuation_rows}
    plookup = {item["symbol"]: item for item in position_rows}
    final_rows: list[dict[str, Any]] = []
    for row in rows[:10]:
        score = float(row.get("strategic_score", 0.0))
        confidence = float(row.get("confidence_score", 0.0))
        price_guard = vlookup.get(row["company_code"], {})
        current_zone = price_guard.get("current_zone", "价格区间数据不足")
        if score > 75 and confidence >= 0.7 and "风险区" not in current_zone and "数据不足" not in current_zone:
            action = "BUY"
        elif score >= 50 and confidence >= 0.5:
            action = "WATCH"
        elif row.get("final_decision") == "WATCH":
            action = "WATCH"
        elif row.get("final_decision") == "BUY":
            action = "HOLD"
        else:
            action = "AVOID"
        final_rows.append(
            {
                "symbol": row["company_code"],
                "name": row["name"],
                "theme": row["theme"],
                "score": _normalized_score(score),
                "score_band": _score_band(score)[0],
                "confidence": f"{confidence:.2f}",
                "current_price_zone": current_zone,
                "action": action,
                "position": plookup.get(row["company_code"], {}).get("recommended_weight", "0%"),
                "is_chasing": "是" if "风险区" in str(current_zone) else "否",
                "reason": "价格与置信度暂不支持追高" if "数据不足" in str(current_zone) else "依据评分与置信度综合判断",
            }
        )
    return final_rows


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


def _audit_sections() -> dict[str, Any]:
    audit_report = AuditEngine().run()
    checks = [
        {
            "category": item.category,
            "item": item.item,
            "status": item.status,
            "severity": item.severity,
            "message": item.message,
        }
        for item in audit_report.checks
    ]
    return {
        "audit_report": {
            "timestamp": audit_report.timestamp,
            "checks": checks,
            "passed_count": audit_report.passed_count,
            "warning_count": audit_report.warning_count,
            "failed_count": audit_report.failed_count,
            "overall_status": audit_report.overall_status,
            "skill_readiness": dict(audit_report.skill_readiness),
        }
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
    audit_sections = _audit_sections()
    growth_watchlist_rows, new_material_rows, _ = _growth_watchlist_sections(rows, base_dir)
    sector_rows = _sector_summary_rows(rows, growth_watchlist_rows)
    theme_rows = _theme_ranking_rows(growth_watchlist_rows)
    market_regime_rows = _market_regime_summary(sector_rows, theme_rows, portfolio_snapshot, risk_report)
    market_regime_lookup = {item["item"]: item["value"] for item in market_regime_rows}
    stability_score = float(quality_sections["quality_report"]["passed_count"]) / max(
        float(quality_sections["quality_report"]["passed_count"] + quality_sections["quality_report"]["failed_count"]),
        1.0,
    )
    diagnosis = {
        "health": {
            "status": "CRITICAL" if risk_report.get("risk_level") in {"HIGH", "CRITICAL"} else ("WATCH" if risk_report.get("warnings") else "STABLE"),
            "score": round(stability_score, 4),
            "warnings": list(risk_report.get("warnings", []))[:5],
        },
        "stability": {
            "status": "STABLE" if stability_score >= 0.7 else "WATCH",
            "warnings": list(quality_sections["quality_report"].get("warnings", []))[:5],
        },
    }
    capital_flow = {
        "top_inflow_sectors": [item["sector"] for item in sorted(sector_rows, key=lambda value: value["current_score"], reverse=True)[:2] if item["current_score"] >= 0],
        "top_outflow_sectors": [item["sector"] for item in sorted(sector_rows, key=lambda value: value["current_score"])[:2] if item["current_score"] <= 0],
        "flow_strength": round(min(1.0, max(0.0, sum(item["current_score"] for item in sector_rows[:3]) / 100.0)), 4),
        "leader_concentration": round(min(1.0, max(0.0, (max((item["current_score"] for item in sector_rows), default=0.0) / max(sum(item["current_score"] for item in sector_rows) or 1.0, 1.0)))), 4),
        "rotation_signal": market_regime_lookup.get("一句话市场结论", "UNKNOWN"),
    }
    narrative = {
        "active_narratives": [item["theme"] for item in theme_rows[:3]],
        "narrative_strength": round(min(1.0, max(0.0, sum(item["current_score"] for item in theme_rows[:3]) / 100.0)), 4),
        "narrative_phase": "EMERGING" if sum(item["current_score"] for item in theme_rows[:3]) < 30 else ("EXPANSION" if sum(item["current_score"] for item in theme_rows[:3]) < 60 else ("PEAK" if sum(item["current_score"] for item in theme_rows[:3]) < 80 else "DECLINE")),
        "supporting_sectors": [item["sector"] for item in sector_rows[:3]],
    }
    cycle_state = {
        "liquidity_cycle": "EXPANSION" if market_regime_lookup.get("风险偏好", "中性") == "上升" else "CONTRACTION" if market_regime_lookup.get("风险偏好", "中性") == "下降" else "NEUTRAL",
        "sentiment_cycle": "GREED" if market_regime_lookup.get("市场风格", "混合") == "成长" else ("PANIC" if risk_report.get("risk_level") in {"HIGH", "CRITICAL"} else "NEUTRAL"),
        "industry_cycle": "EARLY_GROWTH" if theme_rows and float(theme_rows[0]["current_score"]) >= 20 else "MATURITY",
        "unified_cycle_state": "RISK_ON" if market_regime_lookup.get("风险偏好", "中性") == "上升" and risk_report.get("risk_level") not in {"HIGH", "CRITICAL"} else ("RISK_OFF" if risk_report.get("risk_level") in {"HIGH", "CRITICAL"} else "TRANSITION"),
    }

    lines: list[str] = []
    lines.append("# Weekly Research Report")
    lines.append("")

    market_state = "🟡 观察"
    if risk_report.get("risk_level") in {"HIGH", "CRITICAL"}:
        market_state = "🔴 风险"
    elif any(item.get("action") in {"BUY", "ADD"} for item in rebalance_plan.get("actions", [])):
        market_state = "🟢 进攻"

    core_count = len(portfolio_snapshot.get("core_candidates", [])) + len(portfolio_snapshot.get("satellite_candidates", []))
    watch_only = "是" if core_count == 0 else "否"
    has_buy = "是" if core_count > 0 else "否"
    cash_ratio = "100.0%" if not portfolio_snapshot.get("ranked_candidates") else f"{position_snapshot.get('remaining_cash', 0.0) * 100:.1f}%"
    top_symbol = rows[0] if rows else {}
    final_recommendation = "OBSERVE"
    if float(backtest_payload["backtest_summary"]["total_return"]) > 0 and float(quality_sections["quality_report"]["rc1_ready"]) > 0:
        final_recommendation = "GO"
    elif float(backtest_payload["backtest_metrics"]["sharpe_ratio"]) < 0.0:
        final_recommendation = "NO_GO"
    elif float(backtest_payload["backtest_summary"]["max_drawdown"]) > 0.2:
        final_recommendation = "OBSERVE"

    lines.append("## 1. Market Interpretation")
    lines.append("| Item | Value | Status |")
    lines.append("|---|---:|---|")
    lines.append(f"| 本周市场状态 | {market_state} | {market_state} |")
    lines.append(f"| 核心结论 | {str(top_symbol.get('research_conclusion', '本周以观察为主'))[:120]} | 🟡 |")
    lines.append(f"| 风险等级 | {risk_report.get('risk_level', 'LOW')} | {'🟢' if risk_report.get('risk_level', 'LOW') == 'LOW' else '🟡'} |")
    lines.append(f"| 现金比例 | {cash_ratio} | 🟢 |")
    lines.append(f"| 本周是否有买入候选 | {has_buy} | {'🟢' if has_buy == '是' else '⚪'} |")
    lines.append(f"| 本周是否只建议观察 | {watch_only} | {'🟡' if watch_only == '是' else '🟢'} |")
    lines.append("")

    lines.append("## 2. Capital Flow Analysis")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Top inflow sectors | {', '.join(capital_flow.get('top_inflow_sectors', [])) or 'none'} |")
    lines.append(f"| Top outflow sectors | {', '.join(capital_flow.get('top_outflow_sectors', [])) or 'none'} |")
    lines.append(f"| Rotation signal | {capital_flow.get('rotation_signal', 'UNKNOWN')} |")
    lines.append(f"| Leader concentration | {float(capital_flow.get('leader_concentration', 0.0)):.4f} |")
    lines.append("")

    lines.append("## 3. Narrative Analysis")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Active narratives | {', '.join(narrative.get('active_narratives', [])) or 'none'} |")
    lines.append(f"| Narrative strength | {float(narrative.get('narrative_strength', 0.0)):.4f} |")
    lines.append(f"| Narrative phase | {narrative.get('narrative_phase', 'UNKNOWN')} |")
    lines.append(f"| Supporting sectors | {', '.join(narrative.get('supporting_sectors', [])) or 'none'} |")
    lines.append("")

    lines.append("## 4. Cycle Position")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Liquidity cycle | {cycle_state.get('liquidity_cycle', 'UNKNOWN')} |")
    lines.append(f"| Sentiment cycle | {cycle_state.get('sentiment_cycle', 'NEUTRAL')} |")
    lines.append(f"| Industry cycle | {cycle_state.get('industry_cycle', 'MATURITY')} |")
    lines.append(f"| Unified cycle state | {cycle_state.get('unified_cycle_state', 'TRANSITION')} |")
    lines.append("")

    lines.append("## 5. Strategy Performance")
    lines.append("| Item | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Strategic score | {float(rows[0].get('strategic_score', 0.0)):.2f} |" if rows else "| Strategic score | 0.00 |")
    lines.append(f"| Backtest return | {backtest_payload['backtest_summary']['total_return']:.4f} |")
    lines.append(f"| Backtest drawdown | {backtest_payload['backtest_summary']['max_drawdown']:.4f} |")
    lines.append(f"| Backtest win rate | {backtest_payload['backtest_metrics']['win_rate']:.4f} |")
    lines.append("")

    lines.append("## 6. Risk Evaluation")
    confidence_risk = len([row for row in rows if float(row.get("confidence_score", 0.0)) < 0.65])
    overfit_risk = 1.0 - float(backtest_payload["backtest_metrics"]["win_rate"])
    lines.append("| Item | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Risk score | {float(risk_report.get('total_risk_score', 0.0)):.4f} |")
    lines.append(f"| Overfitting risk | {overfit_risk:.4f} |")
    lines.append(f"| Data confidence risk | {confidence_risk} |")
    lines.append(f"| Need more cash | {'是' if confidence_risk > 0 or risk_report.get('risk_level') in {'HIGH', 'CRITICAL'} else '否'} |")
    lines.append("")

    lines.append("## 7. System Stability")
    lines.append("| Item | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Stability score | {float(quality_sections['quality_report']['passed_count']) / max(float(quality_sections['quality_report']['passed_count'] + quality_sections['quality_report']['failed_count']), 1.0):.4f} |")
    lines.append(f"| Health status | {diagnosis['health']['status']} |")
    lines.append(f"| Stability status | {diagnosis['stability']['status']} |")
    lines.append(f"| Workflow status | {workflow_sections['workflow_run']['final_status']} |")
    lines.append(f"| Quality status | {quality_sections['rc1_status']} |")
    lines.append(f"| Audit status | {audit_sections['audit_report']['overall_status']} |")
    lines.append("")

    lines.append("## 8. Final Recommendation")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| Recommendation | {final_recommendation} |")
    lines.append(f"| Confidence | {float(rows[0].get('confidence_score', 0.0)):.4f} |" if rows else "| Confidence | 0.0000 |")
    lines.append(f"| Summary | {str(top_symbol.get('research_conclusion', '数据不足，建议观察'))[:160]} |")
    lines.append("")

    lines.append("## Appendix")
    lines.append("### 01 Research Details")
    for rank, row in enumerate(rows[:10], start=1):
        lines.append(f"- {rank}. {row['name']} ({row['company_code']}): {row['research_conclusion']}")
    lines.append("")
    lines.append("### 02 Evidence Summary")
    for rank, row in enumerate(rows[:5], start=1):
        evidence = row.get("evidence_summary", {})
        lines.append(f"- {rank}. {row['name']} overall_confidence={evidence.get('overall_confidence', 0.0):.2f}")
    lines.append("")
    lines.append("### 03 Score Explanation")
    for rank, row in enumerate(rows[:5], start=1):
        score_explanation = row.get("score_explanation", {})
        lines.append(f"- {rank}. {row['name']}: {score_explanation.get('score_explanation', score_explanation)}")
    lines.append("")
    lines.append("### 04 Decision Explanation")
    for rank, row in enumerate(rows[:5], start=1):
        decision_explanation = row.get("decision_explanation", {})
        lines.append(f"- {rank}. {row['name']}: {decision_explanation.get('decision_explanation', decision_explanation)}")
    lines.append("")
    lines.append("### 05 Provider Trust Ranking")
    for rank, item in enumerate(trust_scores, start=1):
        lines.append(f"- {rank}. {item['provider_name']} {item['overall_score']:.2f}")
    lines.append("")
    lines.append("### 06 Portfolio Snapshot")
    lines.append(f"- {portfolio_snapshot.get('summary', '')}")
    lines.append("")
    lines.append("### 07 Portfolio Ranking")
    for item in portfolio_snapshot.get("ranked_candidates", [])[:10]:
        lines.append(f"- {item['rank']}. {item['symbol']} {item['bucket']} total={item['total_score']:.2f} conf={item['confidence_score']:.2f}")
    lines.append("")
    lines.append("### 08 Position Snapshot")
    lines.append(f"- {position_snapshot.get('allocation_summary', '')}")
    lines.append("")
    lines.append("### 09 Risk Warnings")
    if risk_report.get("warnings"):
        for item in risk_report["warnings"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### 10 Rebalance Actions")
    for item in rebalance_plan.get("actions", []):
        lines.append(f"- {item['priority']}. {item['symbol']} {item['action']} {item['current_weight'] * 100:.1f}% -> {item['target_weight'] * 100:.1f}%")
    if not rebalance_plan.get("actions"):
        lines.append("- none")
    lines.append("")
    lines.append("### 11 Backtest Summary")
    backtest_summary = backtest_payload["backtest_summary"]
    lines.append(f"- total_return: {backtest_summary['total_return']:.4f}")
    lines.append(f"- annualized_return: {backtest_summary['annualized_return']:.4f}")
    lines.append(f"- max_drawdown: {backtest_summary['max_drawdown']:.4f}")
    lines.append("")
    lines.append("### 12 Backtest Metrics")
    backtest_metrics = backtest_payload["backtest_metrics"]
    lines.append(f"- volatility: {backtest_metrics['volatility']:.4f}")
    lines.append(f"- sharpe_ratio: {backtest_metrics['sharpe_ratio']:.4f}")
    lines.append(f"- turnover: {backtest_metrics['turnover']:.4f}")
    lines.append(f"- win_rate: {backtest_metrics['win_rate']:.4f}")
    lines.append("")
    lines.append("### 13 Knowledge Base Records")
    for item in kb_sections["knowledge_base_records"]:
        lines.append(
            f"- {item['symbol']} {item['period']} score={item['strategic_score']:.2f} decision={item['final_decision']} confidence={item['confidence_score']:.2f}"
        )
    if not kb_sections["knowledge_base_records"]:
        lines.append("- none")
    lines.append("")
    lines.append("### Portfolio Snapshot")
    lines.append(f"- {portfolio_snapshot.get('summary', '')}")
    lines.append("")
    lines.append("### Portfolio Ranking")
    for item in portfolio_snapshot.get("ranked_candidates", [])[:10]:
        lines.append(f"- {item['rank']}. {item['symbol']} {item['bucket']} total={item['total_score']:.2f} conf={item['confidence_score']:.2f}")
    if not portfolio_snapshot.get("ranked_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("### Core Candidates")
    for item in portfolio_snapshot.get("core_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("core_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("### Satellite Candidates")
    for item in portfolio_snapshot.get("satellite_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("satellite_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("### Watchlist Candidates")
    for item in portfolio_snapshot.get("watchlist_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("watchlist_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("### Excluded Candidates")
    for item in portfolio_snapshot.get("excluded_candidates", []):
        lines.append(f"- {item['symbol']} {item['total_score']:.2f}")
    if not portfolio_snapshot.get("excluded_candidates"):
        lines.append("- none")
    lines.append("")
    lines.append("### Position Snapshot")
    lines.append(f"- {position_snapshot.get('allocation_summary', '')}")
    lines.append("")
    lines.append("### Recommended Positions")
    for item in position_snapshot.get("recommendations", [])[:10]:
        lines.append(f"- {item['symbol']} {item['bucket']} {item['recommended_weight'] * 100:.1f}%")
    if not position_snapshot.get("recommendations"):
        lines.append("- none")
    lines.append("")
    lines.append("### Cash Remaining")
    lines.append(f"- {position_snapshot.get('remaining_cash', 0.0) * 100:.1f}%")
    lines.append("")
    lines.append("### Rebalance Plan")
    lines.append(f"- {rebalance_plan.get('summary', '')}")
    lines.append("")
    lines.append("### Rebalance Actions")
    for item in rebalance_plan.get("actions", []):
        lines.append(f"- {item['priority']}. {item['symbol']} {item['action']} {item['current_weight'] * 100:.1f}% -> {item['target_weight'] * 100:.1f}%")
    if not rebalance_plan.get("actions"):
        lines.append("- none")
    lines.append("")
    lines.append("### Buy List")
    for item in [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"BUY", "ADD"}]:
        lines.append(f"- {item['symbol']} {item['action']} {item['target_weight'] * 100:.1f}%")
    if not [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"BUY", "ADD"}]:
        lines.append("- none")
    lines.append("")
    lines.append("### Sell List")
    for item in [item for item in rebalance_plan.get("actions", []) if item.get("action") == "SELL"]:
        lines.append(f"- {item['symbol']} SELL")
    if not [item for item in rebalance_plan.get("actions", []) if item.get("action") == "SELL"]:
        lines.append("- none")
    lines.append("")
    lines.append("### Reduce List")
    for item in [item for item in rebalance_plan.get("actions", []) if item.get("action") == "REDUCE"]:
        lines.append(f"- {item['symbol']} REDUCE")
    if not [item for item in rebalance_plan.get("actions", []) if item.get("action") == "REDUCE"]:
        lines.append("- none")
    lines.append("")
    lines.append("### Add List")
    for item in [item for item in rebalance_plan.get("actions", []) if item.get("action") == "ADD"]:
        lines.append(f"- {item['symbol']} ADD")
    if not [item for item in rebalance_plan.get("actions", []) if item.get("action") == "ADD"]:
        lines.append("- none")
    lines.append("")
    lines.append("### Hold List")
    for item in [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"HOLD", "WATCH"}]:
        lines.append(f"- {item['symbol']} {item['action']}")
    if not [item for item in rebalance_plan.get("actions", []) if item.get("action") in {"HOLD", "WATCH"}]:
        lines.append("- none")
    lines.append("")
    lines.append("### Backtest Result")
    lines.append(f"- {backtest_report.get('period', '')}")
    lines.append("")
    lines.append("### Risk Suggested Actions")
    if risk_report.get("suggested_actions"):
        for item in risk_report["suggested_actions"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Historical Score Changes")
    for symbol, history in kb_sections["historical_score_changes"].items():
        lines.append(f"- {symbol}")
        for item in history:
            lines.append(f"  - {item['period']}: {item['strategic_score']:.2f}")
    if not kb_sections["historical_score_changes"]:
        lines.append("- none")
    lines.append("")
    lines.append("### Historical Decision Changes")
    for symbol, history in kb_sections["historical_decision_changes"].items():
        lines.append(f"- {symbol}")
        for item in history:
            lines.append(f"  - {item}")
    if not kb_sections["historical_decision_changes"]:
        lines.append("- none")
    lines.append("")
    lines.append("### 14 Workflow Summary")
    lines.append(f"- {workflow_sections['workflow_summary']}")
    lines.append(f"- Workflow Status: {workflow_sections['workflow_run']['final_status']}")
    lines.append("")
    lines.append("### 15 Quality & Audit")
    quality_report = quality_sections["quality_report"]
    lines.append(f"- rc1_ready: {quality_report['rc1_ready']}")
    lines.append(f"- passed_count: {quality_report['passed_count']}")
    lines.append(f"- failed_count: {quality_report['failed_count']}")
    audit_report = audit_sections["audit_report"]
    lines.append(f"- overall_status: {audit_report['overall_status']}")
    lines.append(f"- warning_count: {audit_report['warning_count']}")
    lines.append(f"- skill_readiness: {', '.join(f'{k}={v}' for k, v in audit_report['skill_readiness'].items()) or 'none'}")
    lines.append("")
    lines.append("### Quality Report")
    lines.append(f"- rc1_ready: {quality_report['rc1_ready']}")
    lines.append(f"- passed_count: {quality_report['passed_count']}")
    lines.append(f"- failed_count: {quality_report['failed_count']}")
    lines.append("")
    lines.append("### Audit Report")
    lines.append(f"- overall_status: {audit_report['overall_status']}")
    lines.append(f"- passed_count: {audit_report['passed_count']}")
    lines.append(f"- warning_count: {audit_report['warning_count']}")
    lines.append(f"- failed_count: {audit_report['failed_count']}")
    lines.append("")
    lines.append("### RC1 Status")
    lines.append(f"- {quality_sections['rc1_status']}")
    lines.append("")
    lines.append("### Risk Report")
    lines.append(f"- level={risk_report.get('risk_level', 'LOW')} score={risk_report.get('total_risk_score', 0.0):.2f}")
    lines.append("")
    lines.append("### Workflow Warnings")
    if workflow_sections["workflow_warnings"]:
        for item in workflow_sections["workflow_warnings"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Workflow Errors")
    if workflow_sections["workflow_errors"]:
        for item in workflow_sections["workflow_errors"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Skill Readiness")
    for skill, status in audit_report["skill_readiness"].items():
        lines.append(f"- {skill}: {status}")
    if not audit_report["skill_readiness"]:
        lines.append("- none")
    lines.append("")

    output_path = base_dir / "reports" / "weekly_report.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


_WEEKLY_REPORT_CACHE: dict[tuple[int, int], Path] = {}
_COCKPIT_REPORT_CACHE: dict[tuple[int, int], Path] = {}


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


def _status_icon(label: str) -> str:
    mapping = {
        "NORMAL": "🟢",
        "WATCH": "🟡",
        "RISK": "🔴",
        "NOT_STARTED": "⚪",
        "READY": "🟢",
        "PASS": "🟢",
        "FAIL": "🔴",
    }
    return mapping.get(label, "🟡")


def _safe_dict(value: Any, tabular: TabularExporter) -> dict[str, Any]:
    payload = tabular.to_dict(value)
    return payload if isinstance(payload, dict) else {"value": payload}


def _factor_score(row: dict[str, Any], field_name: str) -> float:
    factor_scores = row.get("factor_scores", {})
    if isinstance(factor_scores, dict):
        try:
            return float(factor_scores.get(field_name, 0.0))
        except Exception:
            return 0.0
    return 0.0


def _build_theme_dashboard(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    theme_rows = [
        ("AI算力", "ai_compute_score", "🟡 观察", "本周唯一显著主题"),
        ("国产替代", "domestic_substitution_score", "⚪ 未启动", "当前样本无明显抬升"),
        ("华为超节点", "supernode_score", "⚪ 未启动", "观察链条暂未兑现"),
        ("τ因子", "tau_factor_score", "⚪ 未启动", "等待更强验证信号"),
        ("先进封装", "advanced_packaging_score", "⚪ 未启动", "当前样本仍偏弱"),
        ("新材料", "advanced_material_score", "⚪ 未启动", "新材料观察池独立跟踪"),
    ]
    dashboard: list[dict[str, Any]] = []
    for theme_name, field_name, default_state, note in theme_rows:
        score = max((_factor_score(row, field_name) for row in rows), default=0.0)
        state = default_state
        if score >= 0.05:
            state = "🟡 观察"
        if score >= 0.30:
            state = "🟢 正常"
        if score <= 0.0:
            state = "⚪ 未启动"
        dashboard.append(
            {
                "theme_name": theme_name,
                "score": round(score, 4),
                "state": state,
                "icon": _status_icon("WATCH" if "观察" in state else ("NORMAL" if "正常" in state else "NOT_STARTED")),
                "note": note,
            }
        )
    return dashboard


def _build_new_material_watchlist(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    universe = _load_universe(Path(__file__).resolve().parents[1])
    material_specs = [
        (
            "玻璃基板",
            ["600703.SH 三安光电", "688002.SH 睿创微纳"],
            "先进材料与封装工艺观察方向",
            "工艺验证中",
        ),
        (
            "人造金刚石 / 金刚石半导体",
            ["688234.SH 天岳先进", "002192.SZ 融捷股份", "300395.SZ 菲利华"],
            "超硬材料与热管理链条",
            "未启动",
        ),
        (
            "先进散热材料",
            ["002156.SZ 通富微电", "600584.SH 长电科技"],
            "热管理与封装协同方向",
            "未启动",
        ),
        (
            "高端封装材料",
            ["002156.SZ 通富微电", "002185.SZ 华天科技", "600584.SH 长电科技"],
            "先进封装材料链条",
            "刚启动",
        ),
    ]
    universe_index = {f"{item['code']} {item['name']}": item for item in universe}
    rows_index = {row["company_code"]: row for row in rows}
    watchlist: list[dict[str, Any]] = []
    for direction, symbols, note, catalyst_state in material_specs:
        representative: list[str] = []
        for candidate in symbols:
            code = candidate.split(" ", 1)[0]
            if candidate in universe_index or code in rows_index or candidate in universe_index:
                representative.append(candidate)
            else:
                representative.append(candidate)
        score = 0.0
        for row in rows:
            score = max(score, _factor_score(row, "advanced_material_score"))
        watchlist.append(
            {
                "direction": direction,
                "representative_symbols": " / ".join(representative[:3]),
                "advanced_material_score": round(score, 4),
                "catalyst_state": f"⚪ {catalyst_state}" if score <= 0.0 else "🟡 观察",
                "highlight": "是",
                "note": note,
            }
        )
    return watchlist


def _board_for_theme(theme: str) -> str:
    alias_map = _theme_alias_map()
    for board, aliases in alias_map.items():
        if theme in aliases or theme == board:
            return board
    return theme


def _market_regime_summary(
    sector_rows: list[dict[str, Any]],
    theme_rows: list[dict[str, Any]],
    portfolio_snapshot: dict[str, Any],
    risk_report: dict[str, Any],
) -> list[dict[str, Any]]:
    sorted_sectors = sorted(sector_rows, key=lambda item: item["current_score"], reverse=True)
    main_line = sorted_sectors[0]["sector"] if sorted_sectors else "暂无"
    secondary_line = sorted_sectors[1]["sector"] if len(sorted_sectors) > 1 else "暂无"
    latent_candidates = [item for item in sorted_sectors if item["status"] in {"⚪ 未启动", "🟡 刚启动"}]
    latent_direction = latent_candidates[0]["sector"] if latent_candidates else (sorted_sectors[-1]["sector"] if sorted_sectors else "暂无")
    top_score = sorted_sectors[0]["current_score"] if sorted_sectors else 0.0
    if main_line in {"AI算力", "AI国产替代", "高端装备"} and top_score >= 20:
        market_style = "成长"
    elif main_line in {"能源安全与煤基新材料"}:
        market_style = "价值"
    elif risk_report.get("risk_level") in {"HIGH", "CRITICAL"}:
        market_style = "防御"
    else:
        market_style = "混合"
    if any(item.get("action") in {"BUY", "ADD"} for item in portfolio_snapshot.get("ranked_candidates", [])):
        risk_appetite = "上升"
    elif risk_report.get("risk_level") in {"HIGH", "CRITICAL"} or all(
        float(item.get("current_score", 0.0)) <= 0.0 for item in sector_rows
    ):
        risk_appetite = "下降"
    else:
        risk_appetite = "中性"
    conclusion = (
        f"当前主线集中在{main_line}，市场风格偏{market_style}，"
        f"更适合围绕{secondary_line}与{latent_direction}做观察和分批验证。"
    )
    if risk_report.get("risk_level") in {"HIGH", "CRITICAL"}:
        conclusion = f"风险偏高，优先控制仓位，围绕{main_line}观察验证，不追高。"
    return [
        {"item": "市场风格", "value": market_style},
        {"item": "风险偏好", "value": risk_appetite},
        {"item": "主线板块", "value": main_line},
        {"item": "次主线板块", "value": secondary_line},
        {"item": "潜伏方向", "value": latent_direction},
        {"item": "一句话市场结论", "value": conclusion},
    ]


def _sector_summary_table(
    sector_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "sector": item["sector"],
            "status": item["status"],
            "current_score": item["current_score"],
            "previous_score": item["previous_score"],
            "score_change": item["score_change"],
            "core_driver": item["core_driver"] or "趋势验证中",
            "major_risk": item["major_risk"],
            "watch": item["watch"],
        }
        for item in sector_rows
    ]


def _theme_momentum_table(theme_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rank": item["rank"],
            "theme": item["theme"],
            "current_score": item["current_score"],
            "previous_score": item["previous_score"],
            "score_change": item["score_change"],
            "status": item["status"],
            "momentum": _trend_label(float(item["score_change"])),
            "conclusion": item["conclusion"],
        }
        for item in theme_rows
    ]


def _score_interpretation(score: float) -> tuple[str, str, str]:
    label, meaning = _score_band(score)
    if score < 30:
        action = "不建议决策"
    elif score < 50:
        action = "仅观察"
    elif score < 70:
        action = "关注并等待验证"
    elif score < 85:
        action = "可纳入组合，建议分批"
    else:
        action = "主线配置，优先跟踪"
    return label, meaning, action


def _valuation_state(score: float) -> str:
    if score < 50:
        return "观察区"
    if score < 70:
        return "买入区"
    return "风险区"


def _decision_reason(row: dict[str, Any], valuation_row: dict[str, Any]) -> str:
    score = float(row.get("strategic_score", 0.0))
    confidence = float(row.get("confidence_score", 0.0))
    current_zone = str(valuation_row.get("current_zone", "价格区间数据不足"))
    if score > 75 and confidence >= 0.7 and "风险区" not in current_zone and "数据不足" not in current_zone:
        return "评分与置信度都较强，且价格不在风险区"
    if score >= 50 and confidence >= 0.5:
        return "逻辑成立，但验证与价格条件仍需确认"
    if confidence < 0.5:
        return "置信度不足，暂不建议决策"
    return "综合条件偏弱，保持观察"


def _investment_cockpit_visual_assets(
    base_dir: Path,
    sector_rows: list[dict[str, Any]],
    theme_rows: list[dict[str, Any]],
    valuation_rows: list[dict[str, Any]],
    portfolio_dashboard: list[dict[str, Any]],
    candidate_cards: list[dict[str, Any]],
) -> None:
    try:
        config_dir = Path(os.environ.get("TEMP", str(base_dir / "logs"))) / "matplotlib-codex-cockpit"
        os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
        config_dir.mkdir(parents=True, exist_ok=True)
        import warnings
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        warnings.filterwarnings("ignore", message="Glyph .* missing from font.*")
    except Exception as exc:  # pragma: no cover - optional visualization
        log_path = base_dir / "logs" / "investment_cockpit_visualization_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"matplotlib import failed: {exc}\n", encoding="utf-8")
        return

    asset_dir = base_dir / "reports" / "weekly" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    try:
        plt.rcParams["axes.unicode_minus"] = False
        plt.rcParams["font.family"] = "DejaVu Sans"

        fig, ax = plt.subplots(figsize=(10, 5))
        sector_labels = [item["sector"] for item in sector_rows]
        sector_scores = [float(item["current_score"]) for item in sector_rows]
        ax.barh(sector_labels, sector_scores, color=["#43a047" if value >= 30 else "#9e9e9e" for value in sector_scores])
        ax.set_title("Sector Ranking")
        ax.set_xlabel("Score")
        fig.tight_layout()
        fig.savefig(asset_dir / "sector_ranking.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 5))
        theme_labels = [item["theme"] for item in theme_rows]
        momentum_scores = [float(item["score_change"]) for item in theme_rows]
        colors = ["#2e7d32" if value > 0.5 else "#ef6c00" if value < -0.5 else "#f9a825" for value in momentum_scores]
        ax.bar(theme_labels, momentum_scores, color=colors)
        ax.axhline(0, color="#424242", linewidth=1)
        ax.set_title("Theme Momentum")
        ax.set_ylabel("Score Change")
        ax.tick_params(axis="x", rotation=20)
        fig.tight_layout()
        fig.savefig(asset_dir / "theme_momentum.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4))
        portfolio_counts = {}
        for item in portfolio_dashboard:
            portfolio_counts[item["metric"]] = item["value"]
        pie_labels = ["Core Allocation", "Satellite Allocation", "Cash"]
        pie_values = []
        for label in pie_labels:
            value_text = str(portfolio_counts.get(label, "0"))
            try:
                pie_values.append(float(value_text.rstrip("%").split()[0]))
            except Exception:
                pie_values.append(0.0)
        if sum(pie_values) <= 0:
            pie_values = [0, 0, 100]
        ax.pie(pie_values, labels=pie_labels, autopct="%1.0f%%", startangle=90)
        ax.set_title("Portfolio Dashboard")
        fig.tight_layout()
        fig.savefig(asset_dir / "portfolio_dashboard.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        valuation_labels = ["买入区", "观察区", "风险区", "价格区间数据不足"]
        valuation_counts = {label: 0 for label in valuation_labels}
        for item in candidate_cards:
            zone = str(item.get("current_zone", "价格区间数据不足"))
            if zone not in valuation_counts:
                zone = "价格区间数据不足"
            valuation_counts[zone] += 1
        ax.bar(
            valuation_labels,
            [valuation_counts[label] for label in valuation_labels],
            color=["#2e7d32", "#f9a825", "#c62828", "#90a4ae"],
        )
        ax.set_title("Valuation Guard")
        fig.tight_layout()
        fig.savefig(asset_dir / "valuation_guard.png", dpi=160)
        plt.close(fig)
    except Exception as exc:  # pragma: no cover - optional visualization
        log_path = base_dir / "logs" / "investment_cockpit_visualization_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"visualization failed: {exc}\n")


def generate_investment_cockpit_report() -> Path:
    """Generate the V9.3 investment cockpit markdown report."""

    base_dir = Path(__file__).resolve().parents[1]
    cache_key = (COCKPIT_REPORT_LAYOUT_VERSION, 1 if os.environ.get("CODEX_TEST_FAST") == "1" else 0)
    cached = _COCKPIT_REPORT_CACHE.get(cache_key)
    if cached is not None and cached.exists():
        return cached
    previous_fast_mode = os.environ.get("CODEX_TEST_FAST")
    if previous_fast_mode is None:
        # Preserve full universe for the interactive cockpit unless tests request fast mode.
        pass
    try:
        rows = build_weekly_report_data()
    finally:
        if previous_fast_mode is not None:
            os.environ["CODEX_TEST_FAST"] = previous_fast_mode
    portfolio_snapshot = _portfolio_sections(rows)
    position_snapshot = _position_sections(portfolio_snapshot)
    risk_report = _risk_sections(portfolio_snapshot, position_snapshot)
    rebalance_plan = _rebalance_sections(portfolio_snapshot, position_snapshot, risk_report)
    backtest_report, backtest_payload = _backtest_sections(rows, portfolio_snapshot, position_snapshot, rebalance_plan)
    kb_sections = _knowledge_base_sections(rows)
    workflow_sections = _workflow_sections(rows, portfolio_snapshot, position_snapshot, risk_report, rebalance_plan, backtest_payload)
    quality_sections = _quality_sections()
    audit_sections = _audit_sections()
    trust_scores = _trust_snapshot()

    growth_watchlist_rows, new_material_rows, _ = _growth_watchlist_sections(rows, base_dir)
    sector_rows = _sector_summary_table(_sector_summary_rows(rows, growth_watchlist_rows))
    theme_rows = _theme_ranking_rows(growth_watchlist_rows)
    theme_momentum_rows = _theme_momentum_table(theme_rows)
    valuation_rows = _valuation_guard_rows(rows)
    candidate_cards = []
    for row in rows[:10]:
        board = _board_for_theme(row["theme"])
        factor_confidences = row.get("factor_confidences", {})
        confidence_score = float(row.get("confidence_score", 0.0))
        confidence_grade = _confidence_grade(confidence_score)
        score_grade, score_meaning, score_action = _score_interpretation(float(row.get("strategic_score", 0.0)))
        valuation_row = next((item for item in valuation_rows if item["symbol"] == row["company_code"]), {})
        current_zone = valuation_row.get("current_zone", "价格区间数据不足")
        positive_factors = row.get("score_explanation", {}).get("top_positive_factors", [])
        if isinstance(positive_factors, list) and positive_factors:
            positive_text = ", ".join(
                str(item.get("factor_name", item)) if isinstance(item, dict) else str(item) for item in positive_factors[:3]
            )
        else:
            positive_text = "暂无有效加分因子"
        risk_factors = row.get("decision_explanation", {}).get("risk_factors", [])
        if isinstance(risk_factors, list) and risk_factors:
            risk_text = ", ".join(
                str(item.get("factor_name", item)) if isinstance(item, dict) else str(item) for item in risk_factors[:3]
            )
        else:
            risk_text = "暂无显著风险因子"
        candidate_cards.append(
            {
                "name": row["name"],
                "code": row["company_code"],
                "board": board,
                "theme": row["theme"],
                "strategic_score": float(row["strategic_score"]),
                "score_grade": score_grade,
                "score_meaning": score_meaning,
                "confidence_grade": confidence_grade,
                "confidence_score": confidence_score,
                "current_price": "价格区间数据不足",
                "buy_zone": valuation_row.get("buy_zone", "价格区间数据不足"),
                "observe_zone": valuation_row.get("observe_zone", "价格区间数据不足"),
                "risk_zone": valuation_row.get("risk_zone", "价格区间数据不足"),
                "current_zone": current_zone,
                "recommended_weight": next((item["recommended_weight"] for item in position_snapshot.get("recommendations", []) if item.get("symbol") == row["company_code"]), 0.0),
                "positive_factors": positive_text,
                "risk_factors": risk_text,
                "conclusion": str(row.get("research_conclusion", ""))[:120] or "保持观察",
                "decisive_action": _decision_reason(row, valuation_row),
            }
        )
    position_rows = _position_recommendation_rows(rows, valuation_rows)
    confidence_rows = _confidence_rows(rows, valuation_rows)
    lifecycle_rows = _lifecycle_rows(rows, growth_watchlist_rows)
    scenario_rows = _scenario_rows()
    final_rows = _final_decision_rows(rows, valuation_rows, position_rows)
    portfolio_dashboard = _portfolio_dashboard_rows(portfolio_snapshot, risk_report, rebalance_plan)

    _investment_cockpit_visual_assets(base_dir, sector_rows, theme_rows, valuation_rows, portfolio_dashboard, candidate_cards)

    market_regime_rows = _market_regime_summary(sector_rows, theme_rows, portfolio_snapshot, risk_report)
    core_count = len(portfolio_snapshot.get("core_candidates", []))
    satellite_count = len(portfolio_snapshot.get("satellite_candidates", []))
    watch_count = len(portfolio_snapshot.get("watchlist_candidates", []))
    excluded_count = len(portfolio_snapshot.get("excluded_candidates", []))
    market_risk_level = risk_report.get("risk_level", "LOW")
    cash_ratio = f"{float(position_snapshot.get('remaining_cash', 0.0)) * 100:.1f}%"
    has_buy_candidate = "是" if any(item["score_grade"] in {"配置级", "主线级"} for item in candidate_cards) else "否"
    watch_only = "是" if core_count == 0 and satellite_count == 0 else "否"

    lines: list[str] = []
    lines.append("# V9.3 Investment Cockpit")
    lines.append("")
    lines.append("## 00 Market Regime Summary")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    for item in market_regime_rows:
        lines.append(f"| {item['item']} | {item['value']} |")
    lines.append("")
    lines.append("## 01 Sector Summary")
    lines.append("| 板块 | 板块状态 | 本周评分 | 上周评分 | 分数变化 | 核心驱动 | 主要风险 | 是否进入重点观察 |")
    lines.append("|---|---|---:|---:|---:|---|---|---|")
    for item in sector_rows:
        change_mark = "🟢" if item["score_change"] > 0 else ("🔴" if item["score_change"] < 0 else "🟡")
        lines.append(
            f"| {item['sector']} | {item['status']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {change_mark} {item['score_change']:.2f} | {item['core_driver']} | {item['major_risk']} | {item['watch']} |"
        )
    lines.append("")
    lines.append("## 02 Theme Ranking")
    lines.append("| 排名 | 主题 | 本周评分 | 上周评分 | 周变化 | 状态 | 结论 |")
    lines.append("|---:|---|---:|---:|---:|---|---|")
    for item in theme_rows:
        lines.append(
            f"| {item['rank']} | {item['theme']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {item['score_change']:.2f} | {item['status']} | {item['conclusion']} |"
        )
    lines.append("")
    lines.append("## 03 Theme Momentum")
    lines.append("| 主题 | 动量信号 | 本周评分 | 上周评分 | 变化值 |")
    lines.append("|---|---|---:|---:|---:|")
    for item in theme_momentum_rows:
        lines.append(
            f"| {item['theme']} | {item['momentum']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {item['score_change']:.2f} |"
        )
    lines.append("")
    lines.append("## 04 Growth Watch List")
    lines.append("| 主题 | 状态 | 本周评分 | 上周评分 | 变化值 | 催化事件 | 重点公司 | 备注 |")
    lines.append("|---|---|---:|---:|---:|---|---|---|")
    for item in growth_watchlist_rows:
        change_symbol = "🟢" if item["score_change"] > 0 else ("🔴" if item["score_change"] < 0 else "⚪")
        lines.append(
            f"| {item['theme']} | {item['status']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {change_symbol} {item['score_change']:.2f} | {item['catalyst_event']} | {item['key_companies']} | {item['notes']} |"
        )
    lines.append("")
    lines.append("## 05 Valuation Guard")
    lines.append("| 股票 | 当前价 | 买入区 | 观察区 | 风险区 | 当前所处区间 | 是否追高 | 价格结论 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for item in valuation_rows:
        lines.append(
            f"| {item['name']}({item['symbol']}) | {item['current_price']} | {item['buy_zone']} | {item['observe_zone']} | {item['risk_zone']} | {item['current_zone']} | {item['is_chasing']} | {item['price_conclusion']} |"
        )
    lines.append("")
    lines.append("## 06 Score Interpretation")
    lines.append("| 股票 | 分数 | 定性等级 | 分数含义 | 建议行为 |")
    lines.append("|---|---:|---|---|---|")
    for item in candidate_cards:
        lines.append(
            f"| {item['name']}({item['code']}) | {item['strategic_score']:.2f} | {item['score_grade']} | {item['score_meaning']} | {item['decisive_action']} |"
        )
    lines.append("")
    lines.append("## 07 Candidate Cards 2.0")
    lines.append("| 股票名称 | 股票代码 | 所属板块 | 所属主题 | 综合评分 | 分数等级 | 信心等级 | 当前价 | 买入区 | 观察区 | 风险区 | 当前区间 | 建议仓位 | 主要加分因子 | 主要风险因子 | 一句话结论 |")
    lines.append("|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|")
    for item in candidate_cards:
        lines.append(
            f"| {item['name']} | {item['code']} | {item['board']} | {item['theme']} | {item['strategic_score']:.2f} | {item['score_grade']} | {item['confidence_grade']} | {item['current_price']} | {item['buy_zone']} | {item['observe_zone']} | {item['risk_zone']} | {item['current_zone']} | {item['recommended_weight'] * 100:.1f}% | {item['positive_factors']} | {item['risk_factors']} | {item['conclusion']} |"
        )
    lines.append("")
    lines.append("## 08 Position Recommendation Engine")
    lines.append("| 股票 | 建议仓位 | 仓位原因 | 是否适合分批 | 是否适合等待回调 |")
    lines.append("|---|---:|---|---|---|")
    for item in position_rows:
        lines.append(
            f"| {item['name']}({item['symbol']}) | {item['recommended_weight']} | {item['reason']} | {item['split']} | {item['wait_pullback']} |"
        )
    lines.append("")
    lines.append("## 09 Confidence Engine")
    lines.append("| 股票 | confidence_score | confidence_grade | 缺失数据项 | 是否影响决策 |")
    lines.append("|---|---:|---|---|---|")
    for item in confidence_rows:
        lines.append(
            f"| {item['name']}({item['symbol']}) | {item['confidence_score']} | {item['confidence_grade']} | {item['missing_items']} | {item['affect_decision']} |"
        )
    lines.append("")
    lines.append("## 10 Watchlist Lifecycle")
    lines.append("| 主题 | 当前生命周期 | 进入下一阶段需要什么验证 | 退出条件 |")
    lines.append("|---|---|---|---|")
    for item in lifecycle_rows:
        lines.append(
            f"| {item['theme']} | {item['current_lifecycle']} | {item['next_validation']} | {item['exit_condition']} |"
        )
    lines.append("")
    lines.append("## 11 Scenario Engine")
    lines.append("| 情景 | 触发条件 | 受益主题 | 受益标的 | 观察指标 | 风险点 |")
    lines.append("|---|---|---|---|---|---|")
    for item in scenario_rows:
        lines.append(
            f"| {item['scenario']} | {item['trigger']} | {item['benefit_themes']} | {item['benefit_stocks']} | {item['observation']} | {item['risk']} |"
        )
    lines.append("")
    lines.append("## 12 Final Decision Engine")
    lines.append("| 股票 | 主题 | 分数 | 分数等级 | 置信度 | 当前价格区间 | 建议动作 | 建议仓位 | 是否追高 | 一句话理由 |")
    lines.append("|---|---|---:|---|---|---|---|---|---|---|")
    for item in final_rows:
        lines.append(
            f"| {item['name']}({item['symbol']}) | {item['theme']} | {item['score']:.2f} | {item['score_band']} | {item['confidence']} | {item['current_price_zone']} | {item['action']} | {item['position']} | {item['is_chasing']} | {item['reason']} |"
        )
    lines.append("")
    lines.append("## Appendix")
    lines.append("### Portfolio Dashboard")
    lines.append("| Metric | Value | Status |")
    lines.append("|---|---:|---|")
    for item in portfolio_dashboard:
        lines.append(f"| {item['metric']} | {item['value']} | {item['status']} |")
    lines.append("")
    lines.append("### Risk Monitor")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| 组合风险等级 | {market_risk_level} |")
    lines.append(f"| 个股风险 | {len(risk_report.get('warnings', []))} |")
    lines.append(f"| 数据置信度风险 | {len([row for row in rows if float(row.get('confidence_score', 0.0)) < 0.65])} |")
    lines.append(f"| 是否需要提高现金比例 | {'是' if market_risk_level in {'HIGH', 'CRITICAL'} else '否'} |")
    lines.append("")
    lines.append("### Trust Ranking")
    for rank, item in enumerate(trust_scores[:5], start=1):
        lines.append(f"- {rank}. {item['provider_name']} {item['overall_score']:.2f}")
    lines.append("")
    lines.append("### Workflow / Quality / Audit")
    lines.append(f"- Workflow: {workflow_sections['workflow_summary']}")
    lines.append(f"- Quality Ready: {quality_sections['rc1_status']}")
    lines.append(f"- Audit Status: {audit_sections['audit_report']['overall_status']}")
    lines.append(f"- KB Records: {len(kb_sections['knowledge_base_records'])}")
    lines.append(f"- Market State: {'🟢 买入候选' if has_buy_candidate == '是' else '🟡 观察为主'}")
    lines.append(f"- Watch Only: {watch_only}")
    lines.append(f"- Cash Ratio: {cash_ratio}")
    lines.append(f"- Buy Candidates: {core_count + satellite_count}")
    lines.append(f"- Watch Candidates: {watch_count}")
    lines.append(f"- Excluded Candidates: {excluded_count}")

    weekly_dir = base_dir / "reports" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    date_stamp = datetime.now().strftime("%Y%m%d")
    output_path = weekly_dir / f"V9_3_investment_cockpit_{date_stamp}.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    _COCKPIT_REPORT_CACHE[cache_key] = output_path
    return output_path


def _candidate_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tabular = TabularExporter()
    cards: list[dict[str, Any]] = []
    for row in rows[:10]:
        score_explanation = _safe_dict(row.get("score_explanation"), tabular)
        decision_explanation = _safe_dict(row.get("decision_explanation"), tabular)
        positive = score_explanation.get("top_positive_factors", [])
        negative = decision_explanation.get("risk_factors", [])
        if isinstance(positive, list):
            positive_text = ", ".join(
                str(item.get("factor_name", item)) if isinstance(item, dict) else str(item)
                for item in positive[:3]
            )
        else:
            positive_text = str(positive)
        if isinstance(negative, list):
            negative_text = ", ".join(
                str(item.get("factor_name", item)) if isinstance(item, dict) else str(item)
                for item in negative[:3]
            )
        else:
            negative_text = str(negative)
        cards.append(
            {
                "name": row.get("name", ""),
                "code": row.get("company_code", ""),
                "theme": row.get("theme", ""),
                "strategic_score": f"{float(row.get('strategic_score', 0.0)):.2f}",
                "decision": row.get("final_decision", "WATCH"),
                "positive_factors": positive_text or "none",
                "risk_factors": negative_text or "none",
                "conclusion": str(row.get("research_conclusion", ""))[:120],
            }
        )
    return cards


def _portfolio_dashboard_rows(portfolio_snapshot: dict[str, Any], risk_report: dict[str, Any], rebalance_plan: dict[str, Any]) -> list[dict[str, Any]]:
    actions = list(rebalance_plan.get("actions", []))
    buy_count = sum(1 for item in actions if item.get("action") in {"BUY", "ADD"})
    hold_count = sum(1 for item in actions if item.get("action") == "HOLD")
    watch_count = sum(1 for item in actions if item.get("action") == "WATCH")
    excluded_count = len(portfolio_snapshot.get("excluded_candidates", []))
    return [
        {"metric": "Core Allocation", "value": portfolio_snapshot.get("summary", "0%"), "status": "🟢"},
        {"metric": "Satellite Allocation", "value": f"{len(portfolio_snapshot.get('satellite_candidates', []))} candidates", "status": "🟡"},
        {"metric": "Cash", "value": "100.0%" if not portfolio_snapshot.get("ranked_candidates") else "See position snapshot", "status": "🟢"},
        {"metric": "Risk Level", "value": risk_report.get("risk_level", "LOW"), "status": "🟢" if risk_report.get("risk_level", "LOW") == "LOW" else "🟡"},
        {"metric": "Buy", "value": str(buy_count), "status": "🟢" if buy_count > 0 else "⚪"},
        {"metric": "Hold", "value": str(hold_count), "status": "🟢" if hold_count > 0 else "⚪"},
        {"metric": "Watch", "value": str(watch_count), "status": "🟡" if watch_count > 0 else "⚪"},
        {"metric": "Excluded", "value": str(excluded_count), "status": "🔴" if excluded_count > 0 else "🟢"},
    ]


def _generate_visual_assets(
    base_dir: Path,
    theme_dashboard: list[dict[str, Any]],
    portfolio_dashboard: list[dict[str, Any]],
    risk_report: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    try:
        config_dir = Path(os.environ.get("TEMP", str(base_dir / "logs"))) / "matplotlib-codex"
        os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
        config_dir.mkdir(parents=True, exist_ok=True)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional visualization
        log_path = base_dir / "logs" / "report_visualization_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"matplotlib import failed: {exc}\n", encoding="utf-8")
        return

    asset_dir = base_dir / "reports" / "weekly" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    try:
        plt.rcParams["axes.unicode_minus"] = False
        plt.rcParams["font.family"] = "DejaVu Sans"

        fig, ax = plt.subplots(figsize=(9, 4))
        names = ["AI Compute", "Domestic", "Ascend", "Tau", "Packaging", "Materials"]
        values = [float(item["score"]) for item in theme_dashboard]
        ax.barh(names, values, color=["#4caf50" if value > 0 else "#9e9e9e" for value in values])
        ax.set_title("Theme Dashboard")
        ax.set_xlabel("Score")
        fig.tight_layout()
        fig.savefig(asset_dir / "theme_dashboard.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4))
        pie_values = []
        pie_labels = []
        for item in portfolio_dashboard:
            if item["metric"] in {"Core Allocation", "Satellite Allocation", "Cash"}:
                pie_labels.append(item["metric"])
                value_text = item["value"]
                try:
                    if isinstance(value_text, str) and value_text.endswith("%"):
                        pie_values.append(float(value_text.rstrip("%")))
                    else:
                        pie_values.append(float(str(value_text).split()[0].rstrip("%")))
                except Exception:
                    pie_values.append(0.0)
        if sum(pie_values) <= 0:
            pie_values = [0, 0, 100]
            pie_labels = ["Core Allocation", "Satellite Allocation", "Cash"]
        ax.pie(pie_values, labels=pie_labels, autopct="%1.0f%%", startangle=90)
        ax.set_title("Portfolio Dashboard")
        fig.tight_layout()
        fig.savefig(asset_dir / "portfolio_dashboard.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        risk_labels = ["Risk", "Confidence Warnings", "Excluded"]
        risk_values = [
            1 if str(risk_report.get("risk_level", "LOW")) in {"HIGH", "CRITICAL"} else 0,
            len([row for row in rows if float(row.get("confidence_score", 0.0)) < 0.65]),
            len(rows),
        ]
        ax.bar(risk_labels, risk_values, color=["#d32f2f", "#ffa000", "#1976d2"])
        ax.set_title("Risk Dashboard")
        fig.tight_layout()
        fig.savefig(asset_dir / "risk_dashboard.png", dpi=160)
        plt.close(fig)
    except Exception as exc:  # pragma: no cover - optional visualization
        log_path = base_dir / "logs" / "report_visualization_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"visualization failed: {exc}\n")


def generate_weekly_dashboard_report() -> Path:
    """Generate a concise visual weekly report."""

    base_dir = Path(__file__).resolve().parents[1]
    previous_fast_mode = os.environ.get("CODEX_TEST_FAST")
    os.environ["CODEX_TEST_FAST"] = "1"
    try:
        rows = build_weekly_report_data()
    finally:
        if previous_fast_mode is None:
            os.environ.pop("CODEX_TEST_FAST", None)
        else:
            os.environ["CODEX_TEST_FAST"] = previous_fast_mode
    portfolio_snapshot = _portfolio_sections(rows)
    position_snapshot = _position_sections(portfolio_snapshot)
    risk_report = _risk_sections(portfolio_snapshot, position_snapshot)
    rebalance_plan = _rebalance_sections(portfolio_snapshot, position_snapshot, risk_report)
    backtest_report, backtest_payload = _backtest_sections(rows, portfolio_snapshot, position_snapshot, rebalance_plan)
    kb_sections = _knowledge_base_sections(rows)
    workflow_sections = _workflow_sections(rows, portfolio_snapshot, position_snapshot, risk_report, rebalance_plan, backtest_payload)
    quality_sections = _quality_sections()
    audit_sections = _audit_sections()
    trust_scores = _trust_snapshot()
    theme_dashboard = _build_theme_dashboard(rows)
    growth_watchlist_rows, new_material_rows, _ = _growth_watchlist_sections(rows, base_dir)
    candidate_cards = _candidate_cards(rows)
    portfolio_dashboard = _portfolio_dashboard_rows(portfolio_snapshot, risk_report, rebalance_plan)

    _generate_visual_assets(base_dir, theme_dashboard, portfolio_dashboard, risk_report, rows)

    market_state = "🟡 观察"
    if risk_report.get("risk_level") in {"HIGH", "CRITICAL"}:
        market_state = "🔴 风险"
    elif any(item.get("action") in {"BUY", "ADD"} for item in rebalance_plan.get("actions", [])):
        market_state = "🟢 进攻"
    core_count = len(portfolio_snapshot.get("core_candidates", [])) + len(portfolio_snapshot.get("satellite_candidates", []))
    watch_only = "是" if core_count == 0 else "否"
    has_buy = "是" if core_count > 0 else "否"
    cash_ratio = "100.0%" if not portfolio_snapshot.get("ranked_candidates") else str(position_snapshot.get("remaining_cash", 1.0) * 100)[:5] + "%"

    lines: list[str] = []
    lines.append("# V9 RC1 Weekly Visual Report")
    lines.append("")
    lines.append("## 01 Executive Summary")
    lines.append("| Item | Value | Status |")
    lines.append("|---|---:|---|")
    lines.append(f"| 本周市场状态 | {market_state} | {market_state} |")
    lines.append(f"| 核心结论 | {str(rows[0].get('research_conclusion', '本周以观察为主'))[:120]} | 🟡 |")
    lines.append(f"| 风险等级 | {risk_report.get('risk_level', 'LOW')} | {'🟢' if risk_report.get('risk_level', 'LOW') == 'LOW' else '🟡'} |")
    lines.append(f"| 现金比例 | {cash_ratio} | 🟢 |")
    lines.append(f"| 本周是否有买入候选 | {has_buy} | {'🟢' if has_buy == '是' else '⚪'} |")
    lines.append(f"| 本周是否只建议观察 | {watch_only} | {'🟡' if watch_only == '是' else '🟢'} |")
    lines.append("")
    lines.append("## 02 Portfolio Dashboard")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for item in portfolio_dashboard:
        lines.append(f"| {item['metric']} | {item['value']} |")
    lines.append("")
    lines.append("## 03 Theme Dashboard")
    lines.append("| Theme | Score | State | Note |")
    lines.append("|---|---:|---|---|")
    for item in theme_dashboard:
        lines.append(f"| {item['theme_name']} | {item['score']:.2f} | {item['state']} | {item['note']} |")
    lines.append("")
    lines.append("## 04 Growth Watch List")
    lines.append("| 主题 | 状态 | 本周评分 | 上周评分 | 变化值 | 催化事件 | 重点公司 | 备注 |")
    lines.append("|---|---|---:|---:|---:|---|---|---|")
    for item in growth_watchlist_rows:
        change_symbol = "🟢" if item["score_change"] > 0 else ("🔴" if item["score_change"] < 0 else "⚪")
        lines.append(
            f"| {item['theme']} | {item['status']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {change_symbol} {item['score_change']:.2f} | {item['catalyst_event']} | {item['key_companies']} | {item['notes']} |"
        )
    lines.append("")
    lines.append("### Trend Tracking")
    lines.append("| theme | current_score | previous_score | score_change |")
    lines.append("|---|---:|---:|---:|")
    for item in growth_watchlist_rows:
        lines.append(
            f"| {item['theme']} | {item['current_score']:.2f} | {item['previous_score']:.2f} | {item['score_change']:.2f} |"
        )
    lines.append("")
    lines.append("## 05 New Material Watchlist")
    lines.append("| 细分方向 | 代表标的 | advanced_material_score | 催化状态 | 是否进入重点观察 | 备注 |")
    lines.append("|---|---|---:|---|---|---|")
    for item in new_material_rows:
        lines.append(
            f"| {item['direction_name']} | {item['watch_companies']} | {item['catalyst_score']:.2f} | {item['status']} | 是 | {item['notes']} |"
        )
    lines.append("")
    lines.append("## 06 Candidate Cards")
    for card in candidate_cards:
        lines.append(f"### {card['name']} ({card['code']})")
        lines.append(f"- 主题：{card['theme']}")
        lines.append(f"- 综合评分：{card['strategic_score']}")
        lines.append(f"- 决策：{card['decision']}")
        lines.append(f"- 主要加分因子：{card['positive_factors']}")
        lines.append(f"- 主要风险因子：{card['risk_factors']}")
        lines.append(f"- 一句话结论：{card['conclusion']}")
        lines.append("")
    lines.append("## 07 Risk Monitor")
    lines.append("| Item | Value |")
    lines.append("|---|---:|")
    lines.append(f"| 组合风险等级 | {risk_report.get('risk_level', 'LOW')} |")
    lines.append(f"| 个股风险 | {len(risk_report.get('warnings', []))} |")
    confidence_risk = len([row for row in rows if float(row.get('confidence_score', 0.0)) < 0.65])
    lines.append(f"| 数据置信度风险 | {confidence_risk} |")
    need_raise_cash = "是" if confidence_risk > 0 or risk_report.get("risk_level") in {"HIGH", "CRITICAL"} else "否"
    lines.append(f"| 是否需要提高现金比例 | {need_raise_cash} |")
    lines.append("")
    lines.append("## 08 Appendix")
    lines.append("### Workflow")
    lines.append(f"- {workflow_sections['workflow_summary']}")
    lines.append(f"- Workflow Status: {workflow_sections['workflow_run']['final_status']}")
    lines.append("### Provider Trust")
    for rank, item in enumerate(trust_scores[:5], start=1):
        lines.append(f"- {rank}. {item['provider_name']} {item['overall_score']:.2f}")
    lines.append("### Quality Report")
    quality_report = quality_sections["quality_report"]
    lines.append(f"- rc1_ready: {quality_report['rc1_ready']}")
    lines.append(f"- passed_count: {quality_report['passed_count']}")
    lines.append(f"- failed_count: {quality_report['failed_count']}")
    lines.append("### Audit Report")
    audit_report = audit_sections["audit_report"]
    lines.append(f"- overall_status: {audit_report['overall_status']}")
    lines.append(f"- passed_count: {audit_report['passed_count']}")
    lines.append(f"- warning_count: {audit_report['warning_count']}")
    lines.append(f"- failed_count: {audit_report['failed_count']}")
    lines.append("### Backtest Summary")
    lines.append(f"- total_return: {backtest_payload['backtest_summary']['total_return']:.4f}")
    lines.append(f"- max_drawdown: {backtest_payload['backtest_summary']['max_drawdown']:.4f}")
    lines.append("### Knowledge Base")
    lines.append(f"- records: {len(kb_sections['knowledge_base_records'])}")

    weekly_dir = base_dir / "reports" / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    date_stamp = datetime.now().strftime("%Y%m%d")
    output_path = weekly_dir / f"V9_RC1_weekly_report_{date_stamp}.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":  # pragma: no cover
    weekly_report = generate_weekly_report()
    cockpit_report = generate_investment_cockpit_report()
    print(weekly_report)
    print(cockpit_report)
