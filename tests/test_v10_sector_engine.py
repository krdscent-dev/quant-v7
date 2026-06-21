"""Tests for the V10.3 sector intelligence layer."""

from __future__ import annotations

from dataclasses import dataclass

from core.v10_sector_engine import V10SectorEngine


@dataclass(frozen=True)
class DummyResult:
    code: str
    name: str
    theme: str
    strategic_score: float


def test_sector_engine_classifies_symbols_and_detects_leader() -> None:
    results = [
        DummyResult("000001.SZ", "A", "AI算力", 80.0),
        DummyResult("000002.SZ", "B", "AI算力", 65.0),
        DummyResult("000003.SZ", "C", "先进封装", 40.0),
    ]

    engine = V10SectorEngine.from_results(results)

    assert engine.classify("000001.SZ") == "AI Computing"
    assert engine.detect_leader(results[:2]) == "000001.SZ"
    assert engine.sector_strength("AI Computing") > 0.75


def test_sector_context_marks_only_top_symbol_as_leader() -> None:
    results = [
        DummyResult("000001.SZ", "A", "AI算力", 80.0),
        DummyResult("000002.SZ", "B", "AI算力", 65.0),
    ]

    context = V10SectorEngine.from_results(results).build_sector_context()

    assert context["000001.SZ"]["sector_leader_flag"] is True
    assert context["000001.SZ"]["sector_rank"] == 1
    assert context["000002.SZ"]["sector_leader_flag"] is False
    assert context["000002.SZ"]["sector_rank"] == 2


def test_rotation_signal_distinguishes_leader_concentration() -> None:
    engine = V10SectorEngine()

    signals = engine.rotation_signal({"AI Computing": 0.90, "Advanced Packaging": 0.55})

    assert signals["AI Computing"] == "LEADER_CONCENTRATION"
    assert signals["Advanced Packaging"] == "ROTATION_CANDIDATE"
