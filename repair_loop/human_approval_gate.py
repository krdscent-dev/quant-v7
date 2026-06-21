"""Human approval gate for repair proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping
import os


@dataclass(frozen=True)
class ApprovalDecision:
    """Result of a human approval request."""

    status: str
    approved_patch_ids: list[str]
    rejected_patch_ids: list[str]
    reason: str


class HumanApprovalGate:
    """Require explicit human approval before applying any patch."""

    def request_approval(self, patches: Iterable[Mapping[str, object]]) -> ApprovalDecision:
        approved_flag = os.environ.get("V12_8_REPAIR_APPROVAL", "").strip().upper()
        patch_ids = [str(patch.get("patch_id", "")) for patch in patches if patch.get("patch_id")]
        if approved_flag in {"1", "TRUE", "YES", "APPROVE", "APPROVED"}:
            return ApprovalDecision(
                status="APPROVED",
                approved_patch_ids=patch_ids,
                rejected_patch_ids=[],
                reason="Manual approval flag detected from environment.",
            )
        if approved_flag in {"0", "FALSE", "NO", "REJECT", "REJECTED"}:
            return ApprovalDecision(
                status="REJECTED",
                approved_patch_ids=[],
                rejected_patch_ids=patch_ids,
                reason="Manual rejection flag detected from environment.",
            )
        return ApprovalDecision(
            status="PENDING",
            approved_patch_ids=[],
            rejected_patch_ids=patch_ids,
            reason="Waiting for explicit human approval.",
        )

