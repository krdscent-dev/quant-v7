from __future__ import annotations

from diagnosis.v12_7_health_monitor import HealthMonitor


def test_health_monitor_detects_critical_state():
    monitor = HealthMonitor()
    result = monitor.assess(
        {"total_return": -0.12, "max_drawdown": 0.18, "win_rate": 0.32},
        [{"pnl": -0.02}, {"pnl": 0.01}],
        {"agent_accuracy": 0.42, "risk_events": 4, "volatility": 0.18},
    )

    assert result.status == "CRITICAL"
    assert result.severity == "HIGH"
    assert "max_drawdown_above_10pct" in result.warnings
    assert result.risk_level == "HIGH"


def test_health_monitor_detects_warning_state():
    monitor = HealthMonitor()
    result = monitor.assess(
        {"total_return": 0.03, "max_drawdown": 0.06, "win_rate": 0.62},
        [{"pnl": 0.02}, {"pnl": -0.01}],
        {"agent_accuracy": 0.61, "risk_events": 0, "volatility": 0.03},
    )

    assert result.status in {"HEALTHY", "WARNING"}
    assert result.score > 0.0

