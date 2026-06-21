"""V10 governance validation for proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.proposal_schema import Proposal


@dataclass(frozen=True)
class GovernanceResult:
    """Proposal governance validation result."""

    valid_proposals: list[Proposal]
    rejected_proposals: list[Proposal]
    warnings: list[str]
    errors: list[str]


class V10Governance:
    """Validate proposals before execution."""

    ALLOWED_TYPES = {
        "FACTOR_WEIGHT_CHANGE",
        "CONFIDENCE_BIAS_CHANGE",
        "CONFIDENCE_SENSITIVITY_CHANGE",
    }
    MIN_FACTOR_WEIGHT = 0.07
    MAX_FACTOR_WEIGHT = 0.28

    def validate(self, proposals: Iterable[Proposal]) -> GovernanceResult:
        """Return executable proposals and governance findings."""

        valid: list[Proposal] = []
        rejected: list[Proposal] = []
        warnings: list[str] = []
        errors: list[str] = []

        for proposal in proposals:
            proposal_errors = self._validate_one(proposal)
            if proposal_errors:
                rejected.append(proposal)
                errors.extend(proposal_errors)
            elif proposal.status == "APPROVED":
                valid.append(proposal)
            else:
                rejected.append(proposal)
                warnings.append(f"{proposal.proposal_id} not approved; execution blocked.")

        return GovernanceResult(
            valid_proposals=valid,
            rejected_proposals=rejected,
            warnings=warnings,
            errors=errors,
        )

    def _validate_one(self, proposal: Proposal) -> list[str]:
        errors: list[str] = []
        if proposal.proposal_type not in self.ALLOWED_TYPES:
            errors.append(f"{proposal.proposal_id} invalid proposal type: {proposal.proposal_type}")
        if proposal.status != "APPROVED":
            return errors
        if proposal.proposal_type == "FACTOR_WEIGHT_CHANGE":
            if not (self.MIN_FACTOR_WEIGHT <= proposal.proposed_value <= self.MAX_FACTOR_WEIGHT):
                errors.append(f"{proposal.proposal_id} factor weight outside governance bounds.")
            if abs(proposal.delta) > 0.02:
                errors.append(f"{proposal.proposal_id} factor change too large.")
        elif proposal.proposal_type == "CONFIDENCE_BIAS_CHANGE":
            if not (-0.20 <= proposal.proposed_value <= 0.20):
                errors.append(f"{proposal.proposal_id} confidence bias outside bounds.")
        elif proposal.proposal_type == "CONFIDENCE_SENSITIVITY_CHANGE":
            if not (0.50 <= proposal.proposed_value <= 1.50):
                errors.append(f"{proposal.proposal_id} confidence sensitivity outside bounds.")
        return errors
