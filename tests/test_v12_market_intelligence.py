"""Tests for V12 market intelligence OS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.v10_audit_engine import V10AuditEngine
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import V11AgentOrchestrator
from market.capital_flow_engine import CapitalFlowEngine
from market.cycle_engine import CycleEngine
from market.market_structure_engine import MarketStructureEngine
from market.narrative_engine import NarrativeEngine


@dataclass(frozen=True)
class DummyResult:
    code: str
    name: str
    theme: str
    strategic_score: float


@dataclass(frozen=True)
class DummyRegime:
    regime: str
    trend: float = 0.7
    volatility: float = 0.3
    confidence: float = 0.8


def _audit_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v12_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_market_structure_engine_classifies_bull_bear_range() -> None:
    engine = MarketStructureEngine()

    assert engine.classify({"trend": 0.8, "volatility": 0.2}).regime == "BULL"
    assert engine.classify({"trend": 0.1, "volatility": 0.2}).regime == "BEAR"
    assert engine.classify({"trend": 0.45, "volatility": 0.4}).regime == "RANGE"


def test_capital_flow_engine_ranks_sector_rotation() -> None:
    flows = CapitalFlowEngine().rank_flows({"AI Computing": 0.9, "Advanced Materials": 0.4})

    assert flows[0].sector == "AI Computing"
    assert flows[0].direction == "INFLOW"
    assert flows[1].direction == "OUTFLOW"


def test_narrative_engine_extracts_dominant_narrative() -> None:
    flows = CapitalFlowEngine().rank_flows({"AI Computing": 0.9, "Advanced Materials": 0.7})

    narrative = NarrativeEngine().extract(flows)

    assert "AI" in narrative.dominant_narrative
    assert narrative.supporting_themes[0] == "AI Computing"


def test_cycle_engine_maps_market_structure_to_risk_appetite() -> None:
    structure = MarketStructureEngine().classify({"trend": 0.1, "volatility": 0.8})

    cycle = CycleEngine().detect(structure)

    assert cycle.risk_appetite == "FALLING"


def test_v11_orchestrator_preserves_v12_market_intelligence() -> None:
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
            "narrative_consistency": "HIGH",
            "macro_cycle": "EXPANSION",
            "liquidity_cycle": "EASING_OR_SUPPORTIVE",
            "risk_appetite": "RISING",
        },
        DummyRegime("BULL"),
    )

    assert result["market_intelligence"]["dominant_narrative"].startswith("AI capital")
    assert result["market_intelligence"]["risk_appetite"] == "RISING"
