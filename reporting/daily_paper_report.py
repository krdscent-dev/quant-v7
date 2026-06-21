"""Daily paper trading report generator."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def _fmt_pct(value: float) -> str:
    return f"{float(value) * 100.0:.2f}%"


def _fmt_num(value: float) -> str:
    return f"{float(value):,.2f}"


class DailyPaperReport:
    """Render a structured markdown report for the paper trading run."""

    def __init__(self, output_dir: Path | str) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, report_payload: Mapping[str, Any]) -> str:
        timestamp = str(report_payload.get("timestamp", datetime.now().isoformat()))
        source_status = str(report_payload.get("source_status", "UNKNOWN"))
        portfolio_snapshot = dict(report_payload.get("portfolio_snapshot", {}) or {})
        decisions = list(report_payload.get("decisions", []) or [])
        trades = list(report_payload.get("trade_records", []) or [])
        market_state = dict(report_payload.get("market_state", {}) or {})
        capital_state = dict(report_payload.get("capital_state", {}) or {})
        warnings = list(report_payload.get("warnings", []) or [])

        action_counts = Counter(str(item.get("action", "OBSERVE")) for item in decisions)
        lines: list[str] = []
        lines.append("# Daily Paper Trading Report")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append(f"- Timestamp: {timestamp}")
        lines.append(f"- Data status: {source_status}")
        lines.append(f"- Current portfolio value: {_fmt_num(portfolio_snapshot.get('portfolio_value', 0.0))}")
        lines.append(f"- Daily PnL: {_fmt_num(portfolio_snapshot.get('daily_pnl', 0.0))}")
        lines.append(f"- Drawdown: {_fmt_pct(portfolio_snapshot.get('drawdown', 0.0))}")
        lines.append(f"- Cash: {_fmt_num(portfolio_snapshot.get('cash', 0.0))}")
        lines.append(f"- Active positions: {len(portfolio_snapshot.get('positions', []))}")
        lines.append(f"- Decisions: {dict(action_counts)}")
        if warnings:
            lines.append(f"- Warnings: {', '.join(str(item) for item in warnings)}")
        lines.append("")

        if market_state:
            structure = market_state.get("structure", {})
            cycle = market_state.get("cycle", {})
            narrative = market_state.get("narrative", {})
            capital_flow = market_state.get("capital_flow", {})
            lines.append("## Market Brain")
            lines.append(f"- Regime: {structure.get('regime', 'UNKNOWN')}")
            lines.append(f"- Trend score: {float(structure.get('trend_score', 0.0)):.4f}")
            lines.append(f"- Volatility state: {structure.get('volatility_state', 'UNKNOWN')}")
            lines.append(f"- Structure strength: {float(structure.get('structure_strength', 0.0)):.4f}")
            lines.append(f"- Flow strength: {float(capital_flow.get('flow_strength', 0.0)):.4f}")
            lines.append(f"- Narrative phase: {narrative.get('narrative_phase', 'UNKNOWN')}")
            lines.append(f"- Cycle state: {cycle.get('unified_cycle_state', 'UNKNOWN')}")
            lines.append("")

        if capital_state:
            lines.append("## Capital Control")
            lines.append(f"- Risk mode: {capital_state.get('risk_mode', 'UNKNOWN')}")
            lines.append(f"- Position multiplier: {float(capital_state.get('position_multiplier', 1.0)):.4f}")
            lines.append(f"- Risk budget: {float(capital_state.get('risk_budget', 0.0)):.4f}")
            lines.append(f"- Exposure limit: {float(capital_state.get('exposure_limit', 0.0)):.4f}")
            lines.append(f"- Leverage adjustment: {float(capital_state.get('leverage_adjustment', 1.0)):.4f}")
            lines.append("")

        positions = list(portfolio_snapshot.get("positions", []) or [])
        lines.append("## Active Positions")
        if positions:
            lines.append("| symbol | quantity | avg cost | last price | market value | unrealized pnl |")
            lines.append("|---|---:|---:|---:|---:|---:|")
            for item in positions:
                lines.append(
                    f"| {item.get('symbol', '')} | {float(item.get('quantity', 0.0)):.4f} | "
                    f"{float(item.get('average_cost', 0.0)):.4f} | {float(item.get('last_price', 0.0)):.4f} | "
                    f"{float(item.get('market_value', 0.0)):.4f} | {float(item.get('unrealized_pnl', 0.0)):.4f} |"
                )
        else:
            lines.append("- No active positions.")
        lines.append("")

        lines.append("## System Decisions")
        if decisions:
            lines.append("| symbol | sector | action | confidence | alpha score | reason | status |")
            lines.append("|---|---|---|---:|---:|---|---|")
            for item in decisions:
                lines.append(
                    f"| {item.get('symbol', '')} | {item.get('sector', '')} | {item.get('action', '')} | "
                    f"{float(item.get('confidence', 0.0)):.4f} | {float(item.get('alpha_score', 0.0)):.4f} | "
                    f"{item.get('reason', '')} | {item.get('data_status', '')} |"
                )
        else:
            lines.append("- No decisions generated.")
        lines.append("")

        lines.append("## Trades")
        if trades:
            lines.append("| timestamp | symbol | action | requested | filled | fill ratio | fill prob | status |")
            lines.append("|---|---|---|---:|---:|---:|---:|---|")
            for item in trades:
                lines.append(
                    f"| {item.get('timestamp', '')} | {item.get('symbol', '')} | {item.get('action', '')} | "
                    f"{float(item.get('requested_notional', 0.0)):.4f} | {float(item.get('filled_notional', 0.0)):.4f} | "
                    f"{float(item.get('fill_ratio', 0.0)):.4f} | {float(item.get('fill_probability', 0.0)):.4f} | "
                    f"{item.get('status', '')} |"
                )
        else:
            lines.append("- No trade records.")
        lines.append("")

        lines.append("## Risk Notes")
        lines.append(f"- Total PnL: {_fmt_num(portfolio_snapshot.get('total_pnl', 0.0))}")
        lines.append(f"- Drawdown limit check: {'PASS' if float(portfolio_snapshot.get('drawdown', 0.0)) < 0.2 else 'CHECK'}")
        lines.append(f"- Trading mode: {source_status}")
        lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def write(self, report_payload: Mapping[str, Any]) -> Path:
        timestamp = str(report_payload.get("timestamp", datetime.now().isoformat()))
        file_date = timestamp[:10].replace("-", "")
        output_path = self.output_dir / f"daily_paper_report_{file_date}.md"
        output_path.write_text(self.render(report_payload), encoding="utf-8")
        return output_path
