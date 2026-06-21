from __future__ import annotations

from production.stability_monitor import StabilityMonitor


def test_stability_monitor_reports_stable_state():
    monitor = StabilityMonitor()
    report = monitor.assess(
        [{"symbol": "000977.SZ", "action": "SMALL_ADD", "confidence": 0.9}],
        [{"final_weighted_decision": "SMALL_ADD", "market_intelligence": {"capital_flow_score": 0.9}}],
        {"approval_status": "PENDING"},
    )

    assert report.status in {"STABLE", "WARNING"}
    assert 0.0 <= report.drift_score <= 1.0
    assert 0.0 <= report.sync_score <= 1.0


def test_stability_monitor_detects_inconsistency():
    monitor = StabilityMonitor()
    report = monitor.assess(
        [
            {"symbol": "000977.SZ", "action": "BUY", "confidence": 0.9},
            {"symbol": "000977.SZ", "action": "SELL", "confidence": 0.2},
        ],
        [
            {"final_weighted_decision": "BUY", "market_intelligence": {"capital_flow_score": 0.7}},
            {"final_weighted_decision": "SELL", "market_intelligence": {"capital_flow_score": 0.3}},
        ],
        {"approval_status": "APPROVED"},
    )

    assert report.inconsistency_score >= 0.0
    assert report.warnings

