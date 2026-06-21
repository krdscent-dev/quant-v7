"""V10.6 human-in-the-loop self-learning layer.

The engine evaluates decisions and exposes adaptive context. It does not apply
learning updates directly; updates must go through Proposal -> Human Review ->
Execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
import json


DEFAULT_FACTOR_WEIGHTS: dict[str, float] = {
    "tau_factor_score": 0.20,
    "supernode_score": 0.20,
    "domestic_substitution_score": 0.20,
    "advanced_packaging_score": 0.15,
    "order_confirmation_score": 0.15,
    "advanced_material_score": 0.10,
}


@dataclass
class LearningState:
    """Persisted adaptive model state."""

    factor_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_FACTOR_WEIGHTS))
    confidence_bias: float = 0.0
    confidence_sensitivity: float = 1.0
    model_bias: dict[str, str] = field(default_factory=dict)
    last_updates: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = ""


class V10SelfLearningEngine:
    """Update adaptive weights and confidence calibration from outcomes."""

    STEP = 0.005
    CONFIDENCE_STEP = 0.01
    MIN_FACTOR_WEIGHT = 0.07
    MAX_FACTOR_WEIGHT = 0.28

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or Path("reports/cache/v10_learning_state.json")
        self.state = self._load_state()

    def update_weights(self, performance_log: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        """Deprecated direct update API.

        Direct mutation is disabled. Use V10ProposalEngine to generate
        proposals and ExecutionEngine to apply approved proposals.
        """

        return {
            "factor_weight_changes": [],
            "confidence_bias": round(self.state.confidence_bias, 4),
            "confidence_sensitivity": round(self.state.confidence_sensitivity, 4),
            "model_bias_detection": self.state.model_bias,
            "direct_update_blocked": True,
            "message": "Direct self-learning updates are disabled; approval is required.",
        }

    def stabilize_state(self) -> dict[str, Any]:
        """Clamp existing state to anti-drift bounds."""

        self.state.factor_weights = self._normalize_weights(self.state.factor_weights)
        self.state.confidence_bias = max(-0.20, min(0.20, self.state.confidence_bias))
        self.state.confidence_sensitivity = max(0.50, min(1.50, self.state.confidence_sensitivity))
        self.state.model_bias = self.detect_model_bias()
        self.state.updated_at = datetime.now().isoformat()
        self._save_state()
        return self.adaptive_context()

    def evaluate_decision(self, decision_log: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Convert decision logs into learning records.

        In live use this should be replaced with realized performance outcomes.
        For now it creates a conservative paper-feedback signal from causal
        strength, portfolio constraints, and final action quality.
        """

        records: list[dict[str, Any]] = []
        for decision in decision_log:
            action = str(decision.get("action", "")).upper()
            confidence = float(decision.get("confidence", 0.0) or 0.0)
            risk = float(decision.get("risk_score", 0.0) or 0.0)
            chain = list(decision.get("causal_chain", []))
            sector = str(decision.get("sector", ""))
            factors = self._infer_contributing_factors(sector, chain)
            if not factors:
                continue

            if action in {"SMALL_ADD", "ADD", "HOLD"} and len(chain) >= 4 and risk <= 0.70:
                outcome = "WIN"
            elif action in {"SMALL_ADD", "ADD"} and risk > 0.70:
                outcome = "LOSS"
            elif action in {"REDUCE"} and len(chain) >= 4:
                outcome = "LOSS"
            else:
                outcome = "NEUTRAL"

            records.append(
                {
                    "symbol": decision.get("symbol", "UNKNOWN"),
                    "outcome": outcome,
                    "confidence": confidence,
                    "contributing_factors": factors,
                    "note": "paper_feedback_until_realized_performance_available",
                }
            )
        return records

    def detect_model_bias(self) -> dict[str, str]:
        """Detect simple model biases from adaptive state."""

        weights = self.state.factor_weights
        max_factor = max(weights, key=weights.get)
        min_factor = min(weights, key=weights.get)
        result = {
            "dominant_factor": max_factor,
            "weakest_factor": min_factor,
            "confidence_bias": "neutral",
        }
        if self.state.confidence_bias > 0.05:
            result["confidence_bias"] = "underconfidence_bias_detected"
        elif self.state.confidence_bias < -0.05:
            result["confidence_bias"] = "overconfidence_bias_detected"
        if weights[max_factor] - weights[min_factor] > 0.20:
            result["factor_concentration_bias"] = "high"
        else:
            result["factor_concentration_bias"] = "normal"
        return result

    def adaptive_context(self) -> dict[str, Any]:
        """Return context that downstream engines can consume next run."""

        return {
            "adaptive_factor_weights": dict(self.state.factor_weights),
            "confidence_bias": self.state.confidence_bias,
            "confidence_sensitivity": self.state.confidence_sensitivity,
            "model_bias": dict(self.state.model_bias),
        }

    def _infer_contributing_factors(self, sector: str, chain: list[Any]) -> list[str]:
        text = " ".join([sector, *[str(item) for item in chain]])
        factors: list[str] = []
        if "AI" in text or "CapEx" in text:
            factors.append("tau_factor_score")
        if "Ascend" in text or "Supernode" in text:
            factors.append("supernode_score")
        if "Domestic" in text or "Localization" in text:
            factors.append("domestic_substitution_score")
        if "Packaging" in text or "Chiplet" in text:
            factors.append("advanced_packaging_score")
        if "Order" in text or "Revenue" in text or "Customer" in text:
            factors.append("order_confirmation_score")
        if "Material" in text or "Glass" in text or "Diamond" in text:
            factors.append("advanced_material_score")
        return factors

    def _normalize_weights(self, weights: Mapping[str, float]) -> dict[str, float]:
        clamped = {
            factor: max(self.MIN_FACTOR_WEIGHT, min(self.MAX_FACTOR_WEIGHT, float(value)))
            for factor, value in weights.items()
        }
        total = sum(max(0.0, float(value)) for value in clamped.values())
        if total <= 0:
            return dict(DEFAULT_FACTOR_WEIGHTS)
        normalized = {
            factor: max(self.MIN_FACTOR_WEIGHT, min(self.MAX_FACTOR_WEIGHT, float(value) / total))
            for factor, value in clamped.items()
        }
        normalized_total = sum(normalized.values())
        return {factor: round(value / normalized_total, 4) for factor, value in normalized.items()}

    def _load_state(self) -> LearningState:
        if not self.state_path.exists():
            return LearningState()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return LearningState()
        return LearningState(
            factor_weights=dict(payload.get("factor_weights", DEFAULT_FACTOR_WEIGHTS)),
            confidence_bias=float(payload.get("confidence_bias", 0.0)),
            confidence_sensitivity=float(payload.get("confidence_sensitivity", 1.0)),
            model_bias=dict(payload.get("model_bias", {})),
            last_updates=list(payload.get("last_updates", [])),
            updated_at=str(payload.get("updated_at", "")),
        )

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "factor_weights": self.state.factor_weights,
            "confidence_bias": self.state.confidence_bias,
            "confidence_sensitivity": self.state.confidence_sensitivity,
            "model_bias": self.state.model_bias,
            "last_updates": self.state.last_updates,
            "updated_at": self.state.updated_at,
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
