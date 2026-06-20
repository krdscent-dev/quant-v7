"""Audit report rendering helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .audit_contract import AuditReport


class AuditReportRenderer:
    def to_dict(self, report: AuditReport) -> dict[str, Any]:
        return {
            "timestamp": report.timestamp,
            "checks": [asdict(item) for item in report.checks],
            "passed_count": report.passed_count,
            "warning_count": report.warning_count,
            "failed_count": report.failed_count,
            "overall_status": report.overall_status,
            "skill_readiness": dict(report.skill_readiness),
        }

    def render_markdown(self, report: AuditReport) -> str:
        summary = self.to_dict(report)
        lines: list[str] = []
        lines.append("## V9 RC1 Audit")
        lines.append(f"- timestamp: {summary['timestamp']}")
        lines.append(f"- overall_status: {summary['overall_status']}")
        lines.append(f"- passed_count: {summary['passed_count']}")
        lines.append(f"- warning_count: {summary['warning_count']}")
        lines.append(f"- failed_count: {summary['failed_count']}")
        lines.append("")
        lines.append("### Checks")
        for item in summary["checks"]:
            lines.append(
                f"- [{item['category']}] {item['item']} {item['status']} "
                f"({item['severity']}): {item['message']}"
            )
        if not summary["checks"]:
            lines.append("- none")
        lines.append("")
        lines.append("### Skill Readiness")
        for skill, status in summary["skill_readiness"].items():
            lines.append(f"- {skill}: {status}")
        if not summary["skill_readiness"]:
            lines.append("- none")
        return "\n".join(lines)

