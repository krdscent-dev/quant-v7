"""Normalization helpers for the unified V12 report schema."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.v12_report_schema import V12ReportSchema


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return default


def _sigmoidish(value: float) -> float:
    """Map a possibly negative return-like value to 0..1 deterministically."""

    return _clamp(0.5 + 0.5 * math.tanh(value))


def _cycle_to_score(cycle_state: Any) -> float:
    if not isinstance(cycle_state, str):
        return 0.5
    normalized = cycle_state.strip().upper()
    if normalized == "RISK_ON":
        return 0.9
    if normalized == "TRANSITION":
        return 0.55
    if normalized == "RISK_OFF":
        return 0.2
    return 0.5


def _risk_level_from_score(score: float) -> str:
    if score <= 0.33:
        return "LOW"
    if score <= 0.66:
        return "MEDIUM"
    return "HIGH"


def _decision_from_score(score: float, confidence: float) -> str:
    if confidence < 0.35:
        return "HOLD"
    if score >= 0.66:
        return "BUY"
    if score >= 0.45:
        return "HOLD"
    return "REDUCE"


def calculate_decision_score(market_state: Mapping[str, float]) -> float:
    """Calculate the normalized decision score required by the schema."""

    return _clamp(
        0.35 * _clamp(_safe_float(market_state.get("structure", 0.5), 0.5))
        + 0.30 * _clamp(_safe_float(market_state.get("flow", 0.5), 0.5))
        + 0.20 * _clamp(_safe_float(market_state.get("cycle", 0.5), 0.5))
        + 0.15 * _clamp(_safe_float(market_state.get("narrative", 0.5), 0.5))
    )


@dataclass(frozen=True)
class V12ReportNormalizer:
    """Convert raw V12 research outputs into the unified schema."""

    missing_value: float = 0.5
    missing_confidence: float = 0.3

    def _normalize_section_score(self, value: Any) -> float:
        return _clamp(_safe_float(value, self.missing_value))

    def _normalize_market_state(self, report: Mapping[str, Any]) -> dict[str, float]:
        market_regime = report.get("market_regime", {})
        if not isinstance(market_regime, Mapping):
            market_regime = {}
        structure = market_regime.get("structure", {})
        capital_flow = market_regime.get("capital_flow", {})
        narrative = market_regime.get("narrative", {})
        cycle_state = market_regime.get("cycle_state", {})
        return {
            "structure": self._normalize_section_score(
                structure.get("trend_score", report.get("stability_score", self.missing_value))
                if isinstance(structure, Mapping)
                else report.get("stability_score", self.missing_value)
            ),
            "flow": self._normalize_section_score(
                capital_flow.get("flow_strength", report.get("risk_score", self.missing_value))
                if isinstance(capital_flow, Mapping)
                else report.get("risk_score", self.missing_value)
            ),
            "narrative": self._normalize_section_score(
                narrative.get("narrative_strength", self.missing_value)
                if isinstance(narrative, Mapping)
                else self.missing_value
            ),
            "cycle": self._normalize_section_score(_cycle_to_score(cycle_state.get("unified_cycle_state")) if isinstance(cycle_state, Mapping) else self.missing_value),
        }

    def _normalize_capital_state(self, report: Mapping[str, Any]) -> dict[str, float]:
        market_regime = report.get("market_regime", {})
        capital_simulation = market_regime.get("capital_simulation", {}) if isinstance(market_regime, Mapping) else {}
        if not isinstance(capital_simulation, Mapping):
            capital_simulation = {}
        risk_budget = _safe_float(capital_simulation.get("risk_budget", 0.5), 0.5)
        exposure_limit = _safe_float(capital_simulation.get("exposure_limit", 0.5), 0.5)
        risk_level = _clamp(1.0 - _clamp(risk_budget))
        exposure = _clamp(exposure_limit)
        return {"risk_level": risk_level, "exposure": exposure}

    def _normalize_performance(self, report: Mapping[str, Any]) -> dict[str, float]:
        backtest = report.get("backtest_result", {})
        if not isinstance(backtest, Mapping):
            backtest = {}
        if not backtest:
            return {
                "return": self.missing_value,
                "drawdown": self.missing_value,
                "win_rate": self.missing_value,
            }
        raw_return = _safe_float(backtest.get("return", self.missing_value), self.missing_value)
        drawdown = _safe_float(backtest.get("drawdown", self.missing_value), self.missing_value)
        win_rate = _safe_float(backtest.get("win_rate", self.missing_value), self.missing_value)
        return {
            "return": _sigmoidish(raw_return),
            "drawdown": _clamp(abs(drawdown)),
            "win_rate": _clamp(win_rate),
        }

    def _normalize_system_health(self, report: Mapping[str, Any]) -> dict[str, float]:
        validation = report.get("validation", {})
        diagnosis = report.get("diagnosis", {})
        market_regime = report.get("market_regime", {})
        if not isinstance(validation, Mapping):
            validation = {}
        if not isinstance(diagnosis, Mapping):
            diagnosis = {}
        if not isinstance(market_regime, Mapping):
            market_regime = {}
        health = diagnosis.get("health", {})
        stability = diagnosis.get("stability", {})
        if not isinstance(health, Mapping):
            health = {}
        if not isinstance(stability, Mapping):
            stability = {}
        stability_score = _safe_float(
            report.get("stability_score", validation.get("stability_score", self.missing_value)),
            self.missing_value,
        )
        overfit = _safe_float(validation.get("overfit_risk", report.get("risk_score", self.missing_value)), self.missing_value)
        confidence = _safe_float(report.get("confidence", market_regime.get("confidence", self.missing_value)), self.missing_value)
        data_quality = _safe_float(
            health.get("score", confidence if confidence is not None else self.missing_value),
            self.missing_value,
        )
        if "status" in stability and str(stability.get("status", "")).upper() == "CRITICAL":
            stability_score = min(stability_score, 0.25)
        return {
            "stability": _clamp(stability_score),
            "overfitting_risk": _clamp(overfit),
            "data_quality": _clamp(data_quality),
        }

    def _decision_score(self, market_state: Mapping[str, float]) -> float:
        return _clamp(
            0.35 * _clamp(market_state.get("structure", self.missing_value))
            + 0.30 * _clamp(market_state.get("flow", self.missing_value))
            + 0.20 * _clamp(market_state.get("cycle", self.missing_value))
            + 0.15 * _clamp(market_state.get("narrative", self.missing_value))
        )

    def _normalize_decision(self, report: Mapping[str, Any], market_state: Mapping[str, float]) -> dict[str, Any]:
        market_regime = report.get("market_regime", {})
        if not isinstance(market_regime, Mapping):
            market_regime = {}
        raw_confidence = report.get("confidence", market_regime.get("confidence", self.missing_confidence))
        confidence = _clamp(_safe_float(raw_confidence, self.missing_confidence))
        if not report:
            return {
                "action": "HOLD",
                "confidence": self.missing_confidence,
                "risk_level": "MEDIUM",
            }
        decision_score = calculate_decision_score(market_state)
        action = _decision_from_score(decision_score, confidence)
        risk_score = _clamp(
            (1.0 - market_state.get("structure", self.missing_value)) * 0.35
            + (1.0 - market_state.get("flow", self.missing_value)) * 0.25
            + (1.0 - market_state.get("cycle", self.missing_value)) * 0.20
            + (1.0 - market_state.get("narrative", self.missing_value)) * 0.20
        )
        risk_level = _risk_level_from_score(risk_score)
        if confidence < 0.35:
            action = "HOLD"
            confidence = self.missing_confidence
        return {"action": action, "confidence": confidence, "risk_level": risk_level}

    def _normalize_explanation(self, report: Mapping[str, Any], market_state: Mapping[str, float]) -> dict[str, Any]:
        factors: list[tuple[str, float]] = [
            ("structure", market_state.get("structure", self.missing_value)),
            ("flow", market_state.get("flow", self.missing_value)),
            ("cycle", market_state.get("cycle", self.missing_value)),
            ("narrative", market_state.get("narrative", self.missing_value)),
        ]
        factors.sort(key=lambda item: item[1], reverse=True)
        key_factors = [name for name, value in factors if value >= 0.55]
        if not key_factors:
            key_factors = [name for name, _ in factors[:2]]
        if not report or all(abs(value - self.missing_value) < 1e-9 for _, value in factors):
            dominant_driver = "neutral fallback"
        else:
            dominant_driver = key_factors[0] if key_factors else "neutral fallback"
        return {
            "key_factors": key_factors,
            "dominant_driver": dominant_driver,
        }

    def normalize(self, report: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize any raw V12 research output into the canonical schema."""

        if not isinstance(report, Mapping):
            report = {}
        market_state = self._normalize_market_state(report)
        schema = V12ReportSchema.from_mapping(
            {
                "market_state": market_state,
                "capital_state": self._normalize_capital_state(report),
                "performance": self._normalize_performance(report),
                "system_health": self._normalize_system_health(report),
                "decision": self._normalize_decision(report, market_state),
                "explanation": self._normalize_explanation(report, market_state),
            }
        )
        normalized = schema.to_dict()
        return normalized


def normalize_v12_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for callers that only need the normalized mapping."""

    return V12ReportNormalizer().normalize(report)
