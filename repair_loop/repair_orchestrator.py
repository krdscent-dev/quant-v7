"""Coordinate diagnosis, approval, repair, and revalidation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import copy
import hashlib

from backtest.v12_6_backtest_engine import V126BacktestEngine, V126BacktestResult
from diagnosis.bias_detector import BiasFinding
from diagnosis.repair_engine import RepairSuggestion
from diagnosis.v12_7_health_monitor import HealthAssessment

from .human_approval_gate import ApprovalDecision, HumanApprovalGate
from .patch_executor import AppliedPatch, PatchExecutor


@dataclass(frozen=True)
class RepairLoopReport:
    """Summary of the semi-automated repair loop."""

    health: HealthAssessment
    biases: list[BiasFinding]
    suggestions: list[RepairSuggestion]
    approval: ApprovalDecision
    applied_patches: list[AppliedPatch]
    pre_fix_backtest: V126BacktestResult
    post_fix_backtest: V126BacktestResult | None
    comparison: dict[str, Any]
    warnings: list[str]


class RepairOrchestrator:
    """Run the full repair loop with mandatory human approval."""

    def __init__(
        self,
        approval_gate: HumanApprovalGate | None = None,
        patch_executor: PatchExecutor | None = None,
        backtest_engine: V126BacktestEngine | None = None,
    ) -> None:
        self.approval_gate = approval_gate or HumanApprovalGate()
        self.patch_executor = patch_executor or PatchExecutor()
        self.backtest_engine = backtest_engine or V126BacktestEngine()

    def _build_patch_proposals(
        self,
        health: HealthAssessment,
        biases: list[BiasFinding],
        suggestions: list[RepairSuggestion],
        current_state: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        capital_state = dict(current_state.get("capital_state", {}) or {})
        learning_context = dict(current_state.get("learning_context", {}) or {})
        proposals: list[dict[str, Any]] = []

        for suggestion in suggestions:
            patch_id = hashlib.sha1(
                f"{suggestion.priority}:{suggestion.title}:{suggestion.action}".encode("utf-8")
            ).hexdigest()[:16]
            if "risk-agent" in suggestion.action.lower() or "risk-agent" in suggestion.title.lower():
                proposals.append(
                    {
                        "patch_id": f"patch_{patch_id}",
                        "target": "agent_weights",
                        "before_value": dict(current_state.get("agent_weights", {})),
                        "proposed_value": self._tuned_agent_weights(current_state),
                        "reason": suggestion.rationale,
                    }
                )
            elif "confidence" in suggestion.action.lower() or "confidence" in suggestion.title.lower():
                proposals.append(
                    {
                        "patch_id": f"patch_{patch_id}",
                        "target": "learning_context",
                        "before_value": dict(learning_context),
                        "proposed_value": self._tuned_learning_context(learning_context),
                        "reason": suggestion.rationale,
                    }
                )
            else:
                proposals.append(
                    {
                        "patch_id": f"patch_{patch_id}",
                        "target": "capital_state",
                        "before_value": dict(capital_state),
                        "proposed_value": self._tuned_capital_state(capital_state, health, biases),
                        "reason": suggestion.rationale,
                    }
                )
        return proposals

    def run(
        self,
        health: HealthAssessment,
        biases: list[BiasFinding],
        suggestions: list[RepairSuggestion],
        current_state: Mapping[str, Any],
        pre_fix_backtest: V126BacktestResult,
    ) -> RepairLoopReport:
        proposals = self._build_patch_proposals(health, biases, suggestions, current_state)
        approval = self.approval_gate.request_approval(proposals)
        applied_patches: list[AppliedPatch] = []
        post_fix_backtest: V126BacktestResult | None = None
        warnings: list[str] = []

        if approval.status == "APPROVED":
            overlay_state, applied_patches = self.patch_executor.apply(proposals, current_state)
            repaired_market_state = copy.deepcopy(dict(current_state.get("market_state", {}) or {}))
            repaired_capital_state = dict(overlay_state.get("capital_state", current_state.get("capital_state", {})))
            repaired_learning = dict(overlay_state.get("learning_context", current_state.get("learning_context", {})))
            decisions = list(current_state.get("decisions", []))
            v11_decisions = list(current_state.get("v11_decisions", []))
            post_fix_backtest = self.backtest_engine.simulate(
                market_state=repaired_market_state,
                capital_state=repaired_capital_state,
                decisions=decisions,
                v11_decisions=v11_decisions,
            )
            if repaired_learning:
                warnings.append("learning_context_overlay_applied")
        else:
            warnings.append("repair_waiting_for_approval")

        comparison = self._compare(pre_fix_backtest, post_fix_backtest)
        return RepairLoopReport(
            health=health,
            biases=biases,
            suggestions=suggestions,
            approval=approval,
            applied_patches=applied_patches,
            pre_fix_backtest=pre_fix_backtest,
            post_fix_backtest=post_fix_backtest,
            comparison=comparison,
            warnings=warnings,
        )

    @staticmethod
    def _tuned_capital_state(
        capital_state: Mapping[str, Any],
        health: HealthAssessment,
        biases: list[BiasFinding],
    ) -> dict[str, Any]:
        overlay = dict(capital_state)
        overlay["risk_score"] = max(0.0, float(overlay.get("risk_score", 0.0) or 0.0) - 0.03)
        if health.status == "CRITICAL":
            overlay["capital_bias"] = "DEFENSIVE"
            overlay["allocation_ceiling"] = min(float(overlay.get("allocation_ceiling", 0.1) or 0.1), 0.05)
        elif any(item.bias_name == "risk_overweight" for item in biases):
            overlay["capital_bias"] = "BALANCED"
        return overlay

    @staticmethod
    def _tuned_learning_context(learning_context: Mapping[str, Any]) -> dict[str, Any]:
        overlay = dict(learning_context)
        overlay["confidence_bias"] = max(-0.05, float(overlay.get("confidence_bias", 0.0) or 0.0) - 0.01)
        overlay["confidence_sensitivity"] = min(1.25, float(overlay.get("confidence_sensitivity", 1.0) or 1.0) + 0.02)
        return overlay

    @staticmethod
    def _tuned_agent_weights(current_state: Mapping[str, Any]) -> dict[str, float]:
        weights = dict(current_state.get("agent_weights", {}) or {})
        risk = float(weights.get("RiskAgent", 0.0) or 0.0)
        alpha = float(weights.get("AlphaAgent", 0.0) or 0.0)
        weights["RiskAgent"] = max(0.15, risk - 0.02)
        weights["AlphaAgent"] = min(0.40, alpha + 0.02)
        return weights

    @staticmethod
    def _compare(
        pre_fix: V126BacktestResult,
        post_fix: V126BacktestResult | None,
    ) -> dict[str, Any]:
        if post_fix is None:
            return {
                "status": "PENDING_APPROVAL",
                "pre_total_return": pre_fix.total_return,
                "post_total_return": None,
                "pre_max_drawdown": pre_fix.max_drawdown,
                "post_max_drawdown": None,
                "delta_total_return": None,
                "delta_max_drawdown": None,
            }
        return {
            "status": "REPAIRED",
            "pre_total_return": pre_fix.total_return,
            "post_total_return": post_fix.total_return,
            "pre_max_drawdown": pre_fix.max_drawdown,
            "post_max_drawdown": post_fix.max_drawdown,
            "delta_total_return": round(post_fix.total_return - pre_fix.total_return, 6),
            "delta_max_drawdown": round(post_fix.max_drawdown - pre_fix.max_drawdown, 6),
        }

