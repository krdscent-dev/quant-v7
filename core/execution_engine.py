"""Execution layer for approved V10 proposals only."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
import json

from core.proposal_schema import Proposal
from core.v10_audit_engine import V10AuditEngine
from core.v10_change_tracker import V10ChangeTracker
from core.v10_self_learning_engine import V10SelfLearningEngine


class ExecutionEngine:
    """Apply approved proposals to learning state."""

    def __init__(self, state_path: Path | None = None, audit_engine: V10AuditEngine | None = None) -> None:
        self.learning_engine = V10SelfLearningEngine(state_path)
        self.audit_engine = audit_engine
        self.change_tracker = V10ChangeTracker()

    def apply_approved(self, proposals: Iterable[Proposal]) -> dict[str, Any]:
        """Apply only APPROVED proposals. Rejected/pending proposals are ignored."""

        approved = [proposal for proposal in proposals if proposal.status == "APPROVED"]
        if not approved:
            if self.audit_engine:
                self.audit_engine.log_event(
                    "EXECUTION_SKIPPED",
                    {"reason": "no_approved_proposals", "approved_count": 0},
                )
            return {
                "applied_count": 0,
                "applied_updates": [],
                "state_changed": False,
                "model_bias_detection": self.learning_engine.detect_model_bias(),
            }

        state = self.learning_engine.state
        updates: list[dict[str, Any]] = []
        for proposal in approved:
            if proposal.proposal_type == "FACTOR_WEIGHT_CHANGE":
                state.factor_weights[proposal.target] = proposal.proposed_value
            elif proposal.proposal_type == "CONFIDENCE_BIAS_CHANGE":
                state.confidence_bias = proposal.proposed_value
            elif proposal.proposal_type == "CONFIDENCE_SENSITIVITY_CHANGE":
                state.confidence_sensitivity = proposal.proposed_value
            else:
                continue
            updates.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "type": proposal.proposal_type,
                    "target": proposal.target,
                    "before": proposal.current_value,
                    "after": proposal.proposed_value,
                    "reason": proposal.reason,
                }
            )

        state.factor_weights = self.learning_engine._normalize_weights(state.factor_weights)
        state.confidence_bias = max(-0.20, min(0.20, state.confidence_bias))
        state.confidence_sensitivity = max(0.50, min(1.50, state.confidence_sensitivity))
        state.model_bias = self.learning_engine.detect_model_bias()
        state.last_updates = updates[-20:]
        state.updated_at = datetime.now().isoformat()
        self._save_state()
        change_records = self.change_tracker.from_execution_updates(updates)
        if self.audit_engine:
            for record in change_records:
                self.audit_engine.log_event(
                    "SYSTEM_CHANGE_APPLIED",
                    {
                        "change_id": record.change_id,
                        "target": record.target,
                        "before": record.before,
                        "after": record.after,
                        "proposal_id": record.proposal_id,
                        "reason": record.reason,
                    },
                )
        return {
            "applied_count": len(updates),
            "applied_updates": updates,
            "change_records": [record.__dict__ for record in change_records],
            "state_changed": bool(updates),
            "model_bias_detection": state.model_bias,
        }

    def _save_state(self) -> None:
        path = self.learning_engine.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        state = self.learning_engine.state
        path.write_text(
            json.dumps(
                {
                    "factor_weights": state.factor_weights,
                    "confidence_bias": state.confidence_bias,
                    "confidence_sensitivity": state.confidence_sensitivity,
                    "model_bias": state.model_bias,
                    "last_updates": state.last_updates,
                    "updated_at": state.updated_at,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
