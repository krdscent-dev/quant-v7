"""Human approval gate for V10 proposals."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

from core.proposal_schema import Proposal


class HumanApprovalEngine:
    """Approve or reject proposals from explicit user decisions."""

    def review(
        self,
        proposals: Iterable[Proposal],
        approvals: Mapping[str, bool] | None = None,
    ) -> list[Proposal]:
        """Return proposals marked APPROVED or REJECTED.

        Missing approvals are rejected by default. This prevents automatic
        execution when the system runs unattended.
        """

        approval_map = dict(approvals or {})
        reviewed: list[Proposal] = []
        for proposal in proposals:
            status = "APPROVED" if approval_map.get(proposal.proposal_id, False) else "REJECTED"
            reviewed.append(replace(proposal, status=status))
        return reviewed

    def pending_summary(self, proposals: Iterable[Proposal]) -> list[dict[str, object]]:
        """Return a human-readable pending proposal summary."""

        return [
            {
                "proposal_id": proposal.proposal_id,
                "type": proposal.proposal_type,
                "target": proposal.target,
                "current": proposal.current_value,
                "proposed": proposal.proposed_value,
                "reason": proposal.reason,
                "status": proposal.status,
            }
            for proposal in proposals
        ]
