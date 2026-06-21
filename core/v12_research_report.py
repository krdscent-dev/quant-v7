"""Research report renderer for the V12 evaluation engine."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


class V12ResearchReport:
    """Render the pure research evaluation output to markdown and JSON."""

    def __init__(self, output_dir: Path | str | None = None) -> None:
        self.output_dir = Path(output_dir or (Path("reports") / "research"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self, result: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "system_type": "RESEARCH_AND_EVALUATION_ONLY",
            "report": dict(result),
        }

    def render_markdown(self, result: Mapping[str, Any]) -> str:
        payload = self.to_dict(result)
        report = payload["report"]
        lines: list[str] = []
        lines.append("# V12 Research & Evaluation Report")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append(f"- System type: {payload['system_type']}")
        lines.append(f"- Generated at: {payload['generated_at']}")
        lines.append(f"- Recommendation: {report.get('recommendation', 'NEED_OPTIMIZATION')}")
        lines.append(f"- Strategy score: {float(report.get('strategy_score', 0.0)):.2f}")
        lines.append(f"- Stability score: {float(report.get('stability_score', 0.0)):.4f}")
        lines.append(f"- Risk score: {float(report.get('risk_score', 0.0)):.4f}")
        lines.append("")

        lines.append("## Market Regime")
        market_regime = report.get("market_regime", {})
        structure = market_regime.get("structure", {})
        capital_flow = market_regime.get("capital_flow", {})
        narrative = market_regime.get("narrative", {})
        cycle_state = market_regime.get("cycle_state", {})
        lines.append(f"- Regime: {structure.get('regime', 'UNKNOWN')}")
        lines.append(f"- Trend score: {float(structure.get('trend_score', 0.0)):.4f}")
        lines.append(f"- Flow strength: {float(capital_flow.get('flow_strength', 0.0)):.4f}")
        lines.append(f"- Narrative phase: {narrative.get('narrative_phase', 'UNKNOWN')}")
        lines.append(f"- Cycle state: {cycle_state.get('unified_cycle_state', 'TRANSITION')}")
        lines.append("")

        lines.append("## Backtest")
        backtest = report.get("backtest_result", {})
        lines.append(f"- Return: {float(backtest.get('return', 0.0)):.4f}")
        lines.append(f"- Drawdown: {float(backtest.get('drawdown', 0.0)):.4f}")
        lines.append(f"- Win rate: {float(backtest.get('win_rate', 0.0)):.4f}")
        lines.append("")

        lines.append("## Diagnosis")
        diagnosis = report.get("diagnosis", {})
        health = diagnosis.get("health", {})
        lines.append(f"- Health status: {health.get('status', 'UNKNOWN')}")
        lines.append(f"- Health score: {float(health.get('score', 0.0)):.4f}")
        lines.append(f"- Warnings: {', '.join(health.get('warnings', [])) or 'none'}")
        biases = diagnosis.get("biases", [])
        if biases:
            for item in biases[:5]:
                lines.append(f"- Bias: {item.get('bias_name', '')} / {item.get('severity', '')}")
        repairs = diagnosis.get("repairs", [])
        if repairs:
            lines.append("")
            lines.append("### Repair Suggestions")
            for item in repairs[:5]:
                lines.append(f"- {item.get('title', '')}: {item.get('action', '')}")
        lines.append("")

        lines.append("## Decision")
        lines.append(f"- Evaluation summary: {report.get('evaluation_summary', '')}")
        if report.get("research_details"):
            lines.append("")
            lines.append("### Research Details")
            for item in report["research_details"][:5]:
                lines.append(
                    f"- {item.get('symbol', '')}: strategic_score={item.get('strategic_score', 0.0):.2f}, "
                    f"confidence={float(item.get('confidence', 0.0)):.2f}"
                )
        return "\n".join(lines).rstrip() + "\n"

    def write(self, result: Mapping[str, Any]) -> dict[str, str]:
        stamp = datetime.now().strftime("%Y%m%d")
        markdown_path = self.output_dir / f"v12_research_report_{stamp}.md"
        json_path = self.output_dir / f"v12_research_report_{stamp}.json"
        markdown_path.write_text(self.render_markdown(result), encoding="utf-8")
        json_path.write_text(json.dumps(self.to_dict(result), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"markdown": str(markdown_path), "json": str(json_path)}
