"""V10 change tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class ChangeRecord:
    """Before/after record for one model or decision change."""

    change_id: str
    target: str
    before: Any
    after: Any
    reason: str
    proposal_id: str
    changed_at: str


class V10ChangeTracker:
    """Build before/after records from approved execution updates."""

    def track_change(
        self,
        target: str,
        before: Any,
        after: Any,
        reason: str,
        proposal_id: str,
    ) -> ChangeRecord:
        return ChangeRecord(
            change_id=f"chg_{proposal_id}",
            target=target,
            before=before,
            after=after,
            reason=reason,
            proposal_id=proposal_id,
            changed_at=datetime.now().isoformat(),
        )

    def from_execution_updates(self, updates: list[Mapping[str, Any]]) -> list[ChangeRecord]:
        """Convert execution updates to change records."""

        records: list[ChangeRecord] = []
        for item in updates:
            records.append(
                self.track_change(
                    target=str(item.get("target", "UNKNOWN")),
                    before=item.get("before"),
                    after=item.get("after"),
                    reason=str(item.get("reason", "")),
                    proposal_id=str(item.get("proposal_id", "UNKNOWN")),
                )
            )
        return records
