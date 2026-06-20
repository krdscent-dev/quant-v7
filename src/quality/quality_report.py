"""Quality report helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .quality_contract import QualityReport


class QualityReportRenderer:
    def to_dict(self, report: QualityReport) -> dict[str, Any]:
        total = len(report.checks)
        return {
            "timestamp": report.timestamp,
            "checks": [asdict(item) for item in report.checks],
            "total_checks": total,
            "passed_count": report.passed_count,
            "failed_count": report.failed_count,
            "warning_count": len(report.warnings),
            "warnings": list(report.warnings),
            "rc1_ready": report.rc1_ready,
        }

    def render_markdown(self, report: QualityReport) -> str:
        summary = self.to_dict(report)
        lines: list[str] = []
        lines.append("## Quality Gate")
        lines.append(f"- timestamp: {summary['timestamp']}")
        lines.append(f"- total_checks: {summary['total_checks']}")
        lines.append(f"- passed_count: {summary['passed_count']}")
        lines.append(f"- failed_count: {summary['failed_count']}")
        lines.append(f"- warning_count: {summary['warning_count']}")
        lines.append(f"- rc1_ready: {summary['rc1_ready']}")
        lines.append("")
        lines.append("### Checks")
        for item in summary["checks"]:
            lines.append(f"- {item['check_name']} [{item['status']}] {item['message']}")
        if not summary["checks"]:
            lines.append("- none")
        lines.append("")
        lines.append("### Warnings")
        if summary["warnings"]:
            for item in summary["warnings"]:
                lines.append(f"- {item}")
        else:
            lines.append("- none")
        return "\n".join(lines)

