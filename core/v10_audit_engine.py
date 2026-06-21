"""V10 audit engine.

All proposal, approval, governance, and execution events are written as JSONL
records so model changes remain traceable.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import json


class V10AuditEngine:
    """Append-only audit logger."""

    def __init__(self, audit_path: Path | None = None) -> None:
        self.audit_path = audit_path or Path("reports/audit/v10_audit_log.jsonl")

    def log_event(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        severity: str = "INFO",
    ) -> dict[str, Any]:
        """Log one audit event and return the written record."""

        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": str(event_type),
            "severity": str(severity),
            "payload": dict(payload),
        }
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def read_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Read recent audit events."""

        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def summary(self, limit: int = 50) -> dict[str, Any]:
        """Return a compact audit summary."""

        records = self.read_recent(limit)
        counts: dict[str, int] = {}
        risk_events = []
        for record in records:
            event_type = str(record.get("event_type", "UNKNOWN"))
            counts[event_type] = counts.get(event_type, 0) + 1
            if str(record.get("severity", "")).upper() in {"WARNING", "ERROR", "CRITICAL"}:
                risk_events.append(record)
        return {
            "total_recent_events": len(records),
            "event_counts": counts,
            "risk_events": risk_events,
        }
