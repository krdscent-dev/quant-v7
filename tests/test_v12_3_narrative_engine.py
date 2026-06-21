"""Tests for V12.3 narrative intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.v10_audit_engine import V10AuditEngine
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import V11AgentOrchestrator
from market.v12_1_structure_engine import analyze_market_structure
from market.v12_2_capital_flow_engine import V122CapitalFlowEngine
from market.v12_3_narrative_engine import V123NarrativeEngine


@dataclass(frozen=True)
class DummyResult:
    code: str
    name: str
    theme: str
    strategic_score: float


@dataclass(frozen=True)
class DummyRegime:
    regime: str
    trend: float = 0.5
    volatility: float = 0.3
    confidence: float = 0.8


def _audit_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v123_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _strong_flow():
    return V122CapitalFlowEngine().analyze_sector_flows(
        sector_trading_volume={
            "AI Computing": 100.0,
            "Advanced Packaging": 90.0,
            "Huawei Ascend Ecosystem": 80.0,
        },
        capital_inflow={
            "AI Computing": 90.0,
            "Advanced Packaging": 80.0,
            "Huawei Ascend Ecosystem": 70.0,
        },
        capital_outflow={
            "AI Computing": 10.0,
            "Advanced Packaging": 10.0,
            "Huawei Ascend Ecosystem": 10.0,
        },
        leader_stock_volume={
            "AI Computing": 70.0,
            "Advanced Packaging": 60.0,
            "Huawei Ascend Ecosystem": 50.0,
        },
    )


def test_v123_extracts_active_narratives_with_flow_support() -> None:
    structure = analyze_market_structure(0.55, 0.4, 0.45)

    analysis = V123NarrativeEngine().extract_market_theme(
        sector_data={
            "AI Computing": 0.95,
            "Advanced Packaging": 0.90,
            "Huawei Ascend Ecosystem": 0.88,
        },
        capital_flow_data=_strong_flow(),
        market_structure=structure,
    )

    assert analysis.active_narratives
    assert analysis.dominant_narrative == "AI capital expenditure and compute infrastructure"
    assert analysis.narrative_strength >= 0.55


def test_v123_filters_weak_narratives_without_flow_support() -> None:
    structure = analyze_market_structure(0.5, 0.4, 0.4)
    flow = V122CapitalFlowEngine().analyze_sector_flows(
        sector_trading_volume={"AI Computing": 100.0},
        capital_inflow={"AI Computing": 1.0},
        capital_outflow={"AI Computing": 99.0},
        leader_stock_volume={"AI Computing": 1.0},
    )

    analysis = V123NarrativeEngine().extract_market_theme(
        sector_data={"AI Computing": 0.2},
        capital_flow_data=flow,
        market_structure=structure,
    )

    assert analysis.active_narratives == []
    assert analysis.dominant_narrative == "No confirmed narrative"


def test_v123_detects_narrative_phase() -> None:
    engine = V123NarrativeEngine()

    assert engine.detect_narrative_phase(0.9, "STRONG", "BULL") == "PEAK"
    assert engine.detect_narrative_phase(0.9, "STRONG", "TRANSITION") == "EXPANSION"
    assert engine.detect_narrative_phase(0.6, "MEDIUM", "RANGE") == "EMERGING"


def test_v123_agent_output_preserves_narrative_fields() -> None:
    sector_engine = V10SectorEngine.from_results(
        [DummyResult("000977.SZ", "sample", "AI Computing", 80.0)]
    )
    orchestrator = V11AgentOrchestrator(sector_engine, V10AuditEngine(_audit_path()))

    result = orchestrator.run(
        {
            "symbol": "000977.SZ",
            "action": "HOLD",
            "confidence": 0.8,
            "risk_score": 0.2,
            "portfolio_exposure": 0.1,
            "dominant_narrative": "AI capital expenditure and compute infrastructure",
            "active_narratives": ["AI capital expenditure and compute infrastructure"],
            "narrative_strength": 0.88,
            "narrative_phase": "EXPANSION",
        },
        DummyRegime("RANGE"),
    )

    assert result["market_intelligence"]["narrative_strength"] == 0.88
    assert result["market_intelligence"]["narrative_phase"] == "EXPANSION"
    assert result["market_intelligence"]["active_narratives"]
