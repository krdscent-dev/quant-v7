"""V10 proposal engine.

Self-learning observations are converted into pending proposals. Nothing is
applied here; execution is delegated to the approval + execution layers.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from core.proposal_schema import Proposal, create_proposal


class V10ProposalEngine:
    """Generate learning proposals from performance logs."""

    STEP = 0.005
    CONFIDENCE_STEP = 0.01
    MIN_FACTOR_WEIGHT = 0.07
    MAX_FACTOR_WEIGHT = 0.28

    def generate_proposals(
        self,
        performance_log: Iterable[Mapping[str, object]],
        current_state: Mapping[str, object],
    ) -> list[Proposal]:
        """Create pending proposals without modifying model state."""

        weights = dict(current_state.get("factor_weights", {}))
        confidence_bias = float(current_state.get("confidence_bias", 0.0) or 0.0)
        confidence_sensitivity = float(current_state.get("confidence_sensitivity", 1.0) or 1.0)
        proposals: list[Proposal] = []
        touched: set[tuple[str, str]] = set()

        for record in performance_log:
            outcome = str(record.get("outcome", "")).upper()
            if outcome not in {"WIN", "LOSS"}:
                continue
            symbol = str(record.get("symbol", "UNKNOWN"))
            confidence = float(record.get("confidence", 0.0) or 0.0)
            direction = self.STEP if outcome == "WIN" else -self.STEP

            for factor in [str(item) for item in record.get("contributing_factors", [])]:
                if factor not in weights:
                    continue
                key = (symbol, factor)
                if key in touched:
                    continue
                touched.add(key)
                current = float(weights[factor])
                proposed = max(self.MIN_FACTOR_WEIGHT, min(self.MAX_FACTOR_WEIGHT, current + direction))
                if proposed == current:
                    continue
                proposals.append(
                    create_proposal(
                        proposal_type="FACTOR_WEIGHT_CHANGE",
                        target=factor,
                        current_value=current,
                        proposed_value=proposed,
                        reason=f"{outcome} case suggests {'increase' if outcome == 'WIN' else 'decrease'} for {factor}.",
                        source_symbol=symbol,
                        outcome=outcome,
                    )
                )

            if confidence >= 0.65 and outcome == "LOSS":
                proposals.append(
                    create_proposal(
                        proposal_type="CONFIDENCE_BIAS_CHANGE",
                        target="confidence_bias",
                        current_value=confidence_bias,
                        proposed_value=max(-0.20, confidence_bias - self.CONFIDENCE_STEP),
                        reason="High-confidence loss suggests reducing confidence bias.",
                        source_symbol=symbol,
                        outcome=outcome,
                    )
                )
                proposals.append(
                    create_proposal(
                        proposal_type="CONFIDENCE_SENSITIVITY_CHANGE",
                        target="confidence_sensitivity",
                        current_value=confidence_sensitivity,
                        proposed_value=max(0.50, confidence_sensitivity - self.CONFIDENCE_STEP),
                        reason="High-confidence loss suggests lower confidence sensitivity.",
                        source_symbol=symbol,
                        outcome=outcome,
                    )
                )
            elif confidence <= 0.35 and outcome == "WIN":
                proposals.append(
                    create_proposal(
                        proposal_type="CONFIDENCE_BIAS_CHANGE",
                        target="confidence_bias",
                        current_value=confidence_bias,
                        proposed_value=min(0.20, confidence_bias + self.CONFIDENCE_STEP),
                        reason="Low-confidence win suggests increasing confidence bias.",
                        source_symbol=symbol,
                        outcome=outcome,
                    )
                )
                proposals.append(
                    create_proposal(
                        proposal_type="CONFIDENCE_SENSITIVITY_CHANGE",
                        target="confidence_sensitivity",
                        current_value=confidence_sensitivity,
                        proposed_value=min(1.50, confidence_sensitivity + self.CONFIDENCE_STEP),
                        reason="Low-confidence win suggests higher confidence sensitivity.",
                        source_symbol=symbol,
                        outcome=outcome,
                    )
                )

        return proposals
