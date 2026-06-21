from __future__ import annotations

from diagnosis.bias_detector import BiasFinding
from diagnosis.repair_engine import RepairEngine
from diagnosis.v12_7_health_monitor import HealthAssessment


def test_repair_engine_ranks_high_severity_first():
    engine = RepairEngine()
    health = HealthAssessment(
        status="CRITICAL",
        severity="HIGH",
        drawdown_risk="ELEVATED",
        accuracy_risk="ELEVATED",
        risk_level="HIGH",
        score=0.31,
        warnings=["max_drawdown_above_10pct"],
    )
    suggestions = engine.propose(
        health,
        [
            BiasFinding("risk_overweight", "HIGH", "risk heavy", {"risk_weight": 0.45}),
            BiasFinding("defensive_action_bias", "MEDIUM", "too defensive", {"observe_ratio": 0.5}),
        ],
        {"total_return": -0.1},
    )

    assert suggestions[0].priority == 1
    assert suggestions[0].severity == "HIGH"
    assert any(item.title == "Reduce exposure and pause new expansion" for item in suggestions)

