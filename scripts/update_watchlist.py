"""更新主题周报的脚本。

读取 `config/theme_watchlist.yaml`，生成 `reports/weekly_watchlist.md`。
输出内容包括：
- 本周观察重点
- 潜在催化剂
- 风险提示
- 因子变化记录
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to run scripts/update_watchlist.py") from exc


@dataclass(frozen=True)
class ThemeEntry:
    """主题条目。"""

    theme_name: str
    thesis: str
    key_companies: list[str]
    observation_signals: list[str]
    quarterly_checks: list[str]
    risk_signals: list[str]


def load_theme_watchlist(path: str | Path) -> list[ThemeEntry]:
    """读取主题观察清单。"""

    watchlist_path = Path(path)
    with watchlist_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    themes = payload.get("themes", [])
    entries: list[ThemeEntry] = []
    for item in themes:
        entries.append(
            ThemeEntry(
                theme_name=str(item.get("theme_name", "")),
                thesis=str(item.get("thesis", "")),
                key_companies=[str(x) for x in item.get("key_companies", [])],
                observation_signals=[str(x) for x in item.get("observation_signals", [])],
                quarterly_checks=[str(x) for x in item.get("quarterly_checks", [])],
                risk_signals=[str(x) for x in item.get("risk_signals", [])],
            )
        )
    return entries


def build_weekly_watchlist_markdown(themes: list[ThemeEntry]) -> str:
    """生成周报 Markdown。"""

    lines: list[str] = []
    lines.append("# V7 主题周度观察清单")
    lines.append("")
    lines.append(f"- 生成日期：{date.today().isoformat()}")
    lines.append(f"- 主题数量：{len(themes)}")
    lines.append("")
    lines.append("## 本周观察重点")
    for theme in themes:
        companies = "、".join(theme.key_companies[:4]) if theme.key_companies else "暂无"
        signals = "、".join(theme.observation_signals[:4]) if theme.observation_signals else "暂无"
        lines.append(f"### {theme.theme_name}")
        lines.append(f"- 主题论点：{theme.thesis}")
        lines.append(f"- 重点公司：{companies}")
        lines.append(f"- 重点信号：{signals}")
        lines.append("")

    lines.append("## 潜在催化剂")
    for theme in themes:
        catalysts = "、".join(theme.quarterly_checks[:3]) if theme.quarterly_checks else "暂无"
        lines.append(f"- {theme.theme_name}：{catalysts}")

    lines.append("")
    lines.append("## 风险提示")
    for theme in themes:
        risks = "、".join(theme.risk_signals[:3]) if theme.risk_signals else "暂无"
        lines.append(f"- {theme.theme_name}：{risks}")

    lines.append("")
    lines.append("## 因子变化记录")
    for theme in themes:
        lines.append(f"### {theme.theme_name}")
        lines.append("- 观察结论：待更新")
        lines.append("- 因子变化：待更新")
        lines.append("- 需要验证：待更新")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_weekly_watchlist_report(
    theme_watchlist_path: str | Path,
    output_path: str | Path,
) -> Path:
    """读取主题清单并输出周报文件。"""

    themes = load_theme_watchlist(theme_watchlist_path)
    markdown = build_weekly_watchlist_markdown(themes)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return output


def main() -> None:
    """脚本入口。"""

    base_dir = Path(__file__).resolve().parents[1]
    theme_watchlist_path = base_dir / "config" / "theme_watchlist.yaml"
    output_path = base_dir / "reports" / "weekly_watchlist.md"
    result = write_weekly_watchlist_report(theme_watchlist_path, output_path)
    print(f"Wrote weekly watchlist report -> {result}")


if __name__ == "__main__":
    main()
