"""事件研究分析脚本。

读取公司事件模板或用户输入内容，生成研究分析样例报告。
当前仅实现规则框架，不接入外部 API。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import sys


@dataclass(frozen=True)
class EventAnalysisResult:
    """事件分析结果。"""

    event_summary: str
    related_themes: list[str]
    related_companies: list[str]
    industry_chain_impact: str
    catalyst_strength: str
    order_confirmation_level: str
    risk_points: list[str]
    research_conclusion: str
    is_key_watch: bool


def analyze_event_text(event_text: str) -> EventAnalysisResult:
    """基于规则框架分析事件文本。

    当前版本仅做模板级规则分类，不做外部检索。
    """

    text = event_text.lower()
    related_themes: list[str] = []
    related_companies: list[str] = []
    risk_points: list[str] = []

    if "昇腾" in event_text or "华为" in event_text:
        related_themes.extend(["华为昇腾生态", "超节点受益链"])
        related_companies.extend(["神州数码", "东尼电子", "海光信息"])
    if "半导体" in event_text or "芯片" in event_text or "封装" in event_text:
        related_themes.extend(["国产替代", "先进封装"])
        related_companies.extend(["北方华创", "中微公司", "通富微电"])
    if "ai" in text or "算力" in event_text:
        related_themes.extend(["AI算力"])
        related_companies.extend(["浪潮信息", "中际旭创", "工业富联"])
    if "材料" in event_text or "基板" in event_text:
        related_themes.extend(["先进材料", "玻璃基板"])
        related_companies.extend(["天岳先进", "三安光电"])

    if not related_themes:
        related_themes.append("待识别")
    if not related_companies:
        related_companies.append("待识别")

    catalyst_strength = "中"
    order_confirmation_level = "低"
    research_conclusion = "事件具备研究价值，但当前仅为规则框架判断。"
    is_key_watch = False
    industry_chain_impact = "事件可能影响产业链的主题关注度和验证节奏。"

    if "订单" in event_text or "收入" in event_text or "客户" in event_text:
        catalyst_strength = "高"
        order_confirmation_level = "中"
        research_conclusion = "事件可能进入订单或收入验证阶段，适合重点跟踪。"
        is_key_watch = True
    if "公告" in event_text or "发布" in event_text:
        catalyst_strength = "中高"
    if "验证" in event_text or "落地" in event_text:
        order_confirmation_level = "高"
        is_key_watch = True
    if "风险" in event_text or "延迟" in event_text or "放缓" in event_text:
        risk_points.append("事件中存在执行或节奏风险")

    if not risk_points:
        risk_points = [
            "订单兑现仍需进一步验证",
            "主题热度可能快于基本面",
        ]

    event_summary = event_text.strip().splitlines()[0][:120] if event_text.strip() else "未提供事件内容"
    return EventAnalysisResult(
        event_summary=event_summary,
        related_themes=sorted(set(related_themes)),
        related_companies=sorted(set(related_companies)),
        industry_chain_impact=industry_chain_impact,
        catalyst_strength=catalyst_strength,
        order_confirmation_level=order_confirmation_level,
        risk_points=risk_points,
        research_conclusion=research_conclusion,
        is_key_watch=is_key_watch,
    )


def render_result(result: EventAnalysisResult) -> str:
    """Render the analysis result as Markdown."""

    lines = [
        "# 事件研究分析样例",
        "",
        "## 事件摘要",
        f"- {result.event_summary}",
        "",
        "## 涉及主题",
        *[f"- {theme}" for theme in result.related_themes],
        "",
        "## 相关公司",
        *[f"- {company}" for company in result.related_companies],
        "",
        "## 产业链影响",
        f"- {result.industry_chain_impact}",
        "",
        "## 催化剂强度",
        f"- {result.catalyst_strength}",
        "",
        "## 订单验证程度",
        f"- {result.order_confirmation_level}",
        "",
        "## 风险点",
        *[f"- {item}" for item in result.risk_points],
        "",
        "## 研究结论",
        f"- {result.research_conclusion}",
        f"- 是否进入重点观察：{'是' if result.is_key_watch else '否'}",
        "",
        "## 说明",
        "- 本分析不输出买卖建议。",
        "- 本分析不预测股价。",
        "- 当前仅为规则框架样例。",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _load_template_or_default() -> str:
    """Load a template sample if available, otherwise return a default event string."""

    template_path = Path(__file__).resolve().parents[1] / "templates" / "company_event_template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "华为昇腾生态合作发布，涉及订单与客户验证进展。"


def main() -> None:
    """脚本入口。"""

    base_dir = Path(__file__).resolve().parents[1]
    event_text = _load_template_or_default()
    result = analyze_event_text(event_text)
    output_path = base_dir / "reports" / "event_analysis_sample.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_result(result), encoding="utf-8")
    print(f"Wrote event analysis sample -> {output_path}")


if __name__ == "__main__":
    main()
