"""Tests for V12.2 capital flow intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.v10_audit_engine import V10AuditEngine
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import V11AgentOrchestrator
from market.v12_2_capital_flow_engine import V122CapitalFlowEngine


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
    path = Path.cwd() / "reports" / "cache" / f"v122_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_v122_analyze_sector_flows_ranks_inflow_sectors() -> None:
    analysis = V122CapitalFlowEngine().analyze_sector_flows(
        sector_trading_volume={"AI Computing": 100.0, "Advanced Materials": 50.0},
        capital_inflow={"AI Computing": 90.0, "Advanced Materials": 10.0},
        capital_outflow={"AI Computing": 10.0, "Advanced Materials": 40.0},
        leader_stock_volume={"AI Computing": 70.0, "Advanced Materials": 5.0},
    )

    assert analysis.ranked_flows[0].sector == "AI Computing"
    assert analysis.top_inflow_sectors[0].sector == "AI Computing"
    assert analysis.ranked_flows[0].leader_concentration == 0.7


def test_v122_detects_leader_concentration() -> None:
    concentration = V122CapitalFlowEngine().detect_leader_flow(100.0, 65.0)

    assert concentration == 0.65


def test_v122_detects_rotation_path() -> None:
    analysis = V122CapitalFlowEngine().analyze_sector_flows(
        sector_trading_volume={"A": 100.0, "B": 80.0, "C": 50.0},
        capital_inflow={"A": 80.0, "B": 50.0, "C": 10.0},
        capital_outflow={"A": 10.0, "B": 20.0, "C": 40.0},
        leader_stock_volume={"A": 60.0, "B": 20.0, "C": 5.0},
    )

    assert analysis.rotation_path[0] == "A"
    assert "C" == analysis.rotation_path[-1]


def test_v122_agent_output_preserves_capital_flow_fields() -> None:
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
            "capital_flow_score": 0.88,
            "capital_flow_direction": "INFLOW",
            "leader_concentration": 0.65,
            "rotation_path": ["AI Computing", "Advanced Packaging"],
        },
        DummyRegime("RANGE"),
    )

    assert result["market_intelligence"]["capital_flow_score"] == 0.88
    assert result["market_intelligence"]["capital_flow_direction"] == "INFLOW"
    assert result["market_intelligence"]["leader_concentration"] == 0.65
