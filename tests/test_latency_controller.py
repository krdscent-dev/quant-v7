from __future__ import annotations

from production.latency_controller import LatencyController


def test_latency_controller_syncs_close_timestamps():
    controller = LatencyController()
    report = controller.assess(
        "2026-06-25T16:00:00",
        "2026-06-25T16:00:30",
        "2026-06-25T16:01:00",
    )

    assert report.status == "LOW_LATENCY"
    assert report.synchronization_status == "SYNCED"
    assert report.latest_market_age_minutes >= 0.0


def test_latency_controller_detects_desync():
    controller = LatencyController()
    report = controller.assess(
        "2026-06-25T16:00:00",
        "2026-06-25T16:10:00",
        "2026-06-25T16:25:00",
    )

    assert report.status == "HIGH_LATENCY"
    assert report.synchronization_status == "DESYNCED"
    assert report.warnings

