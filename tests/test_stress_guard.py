from __future__ import annotations

from production.stress_guard import StressGuard


def test_stress_guard_detects_extreme_state():
    guard = StressGuard()
    report = guard.assess(
        {"total_return": -0.18, "max_drawdown": 0.22, "win_rate": 0.28},
        {"status": "CRITICAL", "score": 0.31},
        {"status": "UNSTABLE", "drift_score": 0.42},
        {"regime": "BEAR", "latency_status": "HIGH_LATENCY"},
    )

    assert report.state == "EXTREME"
    assert report.severity == "HIGH"
    assert "drawdown_stress" in report.warnings


def test_stress_guard_keeps_normal_state_when_stable():
    guard = StressGuard()
    report = guard.assess(
        {"total_return": 0.02, "max_drawdown": 0.02, "win_rate": 0.72},
        {"status": "HEALTHY", "score": 0.86},
        {"status": "STABLE", "drift_score": 0.05},
        {"regime": "RANGE", "latency_status": "LOW_LATENCY"},
    )

    assert report.state == "NORMAL"
    assert report.severity == "LOW"

