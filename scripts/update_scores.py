"""生成当前观察池研究摘要。

读取 `data/watchlists/a_share_core_universe.yaml`，生成
`reports/current_watchlist.md`。

注意:
- 不接入外部 API
- 不做自动打分
- 仅汇总现有观察池内容
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to run scripts/update_scores.py") from exc


@dataclass(frozen=True)
class WatchItem:
    """单个观察标的。"""

    code: str
    name: str
    theme: str
    investment_thesis: str
    key_catalysts: list[str]
    risk_factors: list[str]
    watch_priority: str


def load_core_universe(path: str | Path) -> list[dict[str, Any]]:
    """读取核心观察池 YAML。"""

    universe_path = Path(path)
    with universe_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return list(payload.get("themes", []))


def flatten_watch_items(themes: list[dict[str, Any]]) -> list[WatchItem]:
    """将按主题分组的配置展平成标的列表。"""

    items: list[WatchItem] = []
    for theme_entry in themes:
        theme_name = str(theme_entry.get("theme_name", ""))
        for raw_item in theme_entry.get("items", []):
            items.append(
                WatchItem(
                    code=str(raw_item.get("code", "")),
                    name=str(raw_item.get("name", "")),
                    theme=str(raw_item.get("theme", theme_name)),
                    investment_thesis=str(raw_item.get("investment_thesis", "")),
                    key_catalysts=[str(x) for x in raw_item.get("key_catalysts", [])],
                    risk_factors=[str(x) for x in raw_item.get("risk_factors", [])],
                    watch_priority=str(raw_item.get("watch_priority", "")),
                )
            )
    return items


def build_current_watchlist_markdown(items: list[WatchItem]) -> str:
    """生成当前观察池 Markdown。"""

    grouped: dict[str, list[WatchItem]] = {}
    for item in items:
        grouped.setdefault(item.theme, []).append(item)

    lines: list[str] = []
    lines.append("# V7 当前观察池")
    lines.append("")
    lines.append("## 当前观察池")
    for item in items:
        lines.append(f"- {item.code} {item.name} | {item.theme} | 观察优先级: {item.watch_priority}")

    lines.append("")
    lines.append("## 主题分类")
    for theme_name, theme_items in grouped.items():
        lines.append(f"### {theme_name}")
        for item in theme_items:
            lines.append(f"- {item.code} {item.name}")

    lines.append("")
    lines.append("## 催化剂")
    for item in items:
        catalysts = "、".join(item.key_catalysts) if item.key_catalysts else "暂无"
        lines.append(f"- {item.name}：{catalysts}")

    lines.append("")
    lines.append("## 风险")
    for item in items:
        risks = "、".join(item.risk_factors) if item.risk_factors else "暂无"
        lines.append(f"- {item.name}：{risks}")

    lines.append("")
    lines.append("## 观察优先级")
    for priority in ("A", "B", "C"):
        lines.append(f"### {priority}")
        for item in items:
            if item.watch_priority == priority:
                lines.append(f"- {item.code} {item.name} ({item.theme})")

    return "\n".join(lines).rstrip() + "\n"


def write_current_watchlist_report(
    core_universe_path: str | Path,
    output_path: str | Path,
) -> Path:
    """生成当前观察池 Markdown 文件。"""

    themes = load_core_universe(core_universe_path)
    items = flatten_watch_items(themes)
    markdown = build_current_watchlist_markdown(items)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return output


def main() -> None:
    """脚本入口。"""

    base_dir = Path(__file__).resolve().parents[1]
    core_universe_path = base_dir / "data" / "watchlists" / "a_share_core_universe.yaml"
    output_path = base_dir / "reports" / "current_watchlist.md"
    result = write_current_watchlist_report(core_universe_path, output_path)
    print(f"Wrote current watchlist report -> {result}")


if __name__ == "__main__":
    main()
