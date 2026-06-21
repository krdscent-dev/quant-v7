from __future__ import annotations

from production.circuit_breaker import CircuitBreaker


def test_circuit_breaker_stops_under_extreme_conditions():
    breaker = CircuitBreaker()
    decision = breaker.decide(
        {"status": "UNSTABLE"},
        {"status": "HIGH_LATENCY", "synchronization_status": "DESYNCED"},
        {"state": "EXTREME", "stress_score": 0.88},
    )

    assert decision.final_allowed_action == "STOP"
    assert decision.override is True


def test_circuit_breaker_allows_when_stable():
    breaker = CircuitBreaker()
    decision = breaker.decide(
        {"status": "STABLE"},
        {"status": "LOW_LATENCY", "synchronization_status": "SYNCED"},
        {"state": "NORMAL", "stress_score": 0.11},
    )

    assert decision.final_allowed_action == "ALLOW"
    assert decision.override is False

