from __future__ import annotations

from diagnosis.bias_detector import BiasDetector


def test_bias_detector_finds_risk_overweight_and_defensive_bias():
    detector = BiasDetector()
    findings = detector.detect(
        [{"action": "OBSERVE"}, {"action": "HOLD"}, {"action": "OBSERVE"}],
        agent_weights={"RiskAgent": 0.41, "AlphaAgent": 0.22},
        performance_metrics={"confidence_bias": "underconfidence_bias_detected"},
    )

    names = {item.bias_name for item in findings}
    assert "risk_overweight" in names
    assert "alpha_underperformance" in names
    assert "defensive_action_bias" in names
    assert "confidence_calibration_bias" in names

