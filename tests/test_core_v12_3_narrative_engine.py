from __future__ import annotations

from core.v12_3_narrative_engine import NarrativeEngine, extract_market_theme


def test_core_narrative_engine_detects_ai_and_packaging_themes() -> None:
    result = extract_market_theme(
        {
            "sectors": ["AI Computing", "Advanced Packaging", "Materials"],
            "flow_strength": 0.78,
            "sector_flows": {
                "AI Computing": 0.82,
                "Advanced Packaging": 0.76,
                "Materials": 0.40,
            },
            "news_keywords": ["AI capex", "chiplet cycle"],
        }
    )

    assert "AI EXPANSION" in result["active_narratives"]
    assert "CHIPLET CYCLE" in result["active_narratives"]
    assert result["narrative_strength"] > 0.5
    assert result["narrative_phase"] in {"EXPANSION", "PEAK", "DECLINE"}
    assert "AI Computing" in result["supporting_sectors"]


def test_core_narrative_engine_falls_back_without_data() -> None:
    result = NarrativeEngine().extract_market_theme({})

    assert result == {
        "active_narratives": [],
        "narrative_strength": 0.5,
        "narrative_phase": "UNKNOWN",
        "supporting_sectors": [],
        "sector_narrative_mapping": {},
    }


def test_core_narrative_phase_thresholds() -> None:
    engine = NarrativeEngine()
    assert engine.detect_narrative_phase(0.1) == "EMERGING"
    assert engine.detect_narrative_phase(0.45) == "EXPANSION"
    assert engine.detect_narrative_phase(0.7) == "PEAK"
    assert engine.detect_narrative_phase(0.95) == "DECLINE"

