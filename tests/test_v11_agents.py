"""Tests for V11 multi-agent investment system."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.v10_audit_engine import V10AuditEngine
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import AlphaAgent, RiskAgent, V11AgentOrchestrator


@dataclass(frozen=True)
class DummyResult:
    code: str
    name: str
    theme: str
    strategic_score: float


@dataclass(frozen=True)
class DummyRegime:
    regime: str = "BEAR"
    trend: float = 0.2
    volatility: float = 0.4
    confidence: float = 0.8


def _audit_path() -> Path:
    path = Path.cwd() / "reports" / "cache" / f"v11_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_alpha_agent_suggests_but_does_not_finalize() -> None:
    output = AlphaAgent().evaluate(
        {
            "symbol": "000977.SZ",
            "action": "SMALL_ADD",
            "sector_strength": 0.9,
            "confidence": 0.5,
            "causal_chain": ["A", "B", "C", "D"],
        }
    )

    assert output.agent_name == "AlphaAgent"
    assert "alpha_score" in output.payload
    assert "final_action" not in output.payload


def test_risk_agent_can_reduce_but_not_generate_trade() -> None:
    output = RiskAgent().evaluate(
        {
            "symbol": "000977.SZ",
            "risk_score": 0.8,
            "portfolio_exposure": 0.2,
        }
    )

    assert output.payload["risk_action"] == "REDUCE"
    assert "suggested_action" not in output.payload


def test_v11_orchestrator_returns_consensus_decision_with_audit_trail() -> None:
    sector_engine = V10SectorEngine.from_results(
        [DummyResult("000977.SZ", "浪潮信息", "AI算力", 80.0)]
    )
    orchestrator = V11AgentOrchestrator(sector_engine, V10AuditEngine(_audit_path()))

    result = orchestrator.run(
        {
            "symbol": "000977.SZ",
            "action": "SMALL_ADD",
            "confidence": 0.6,
            "risk_score": 0.2,
            "portfolio_exposure": 0.1,
            "causal_chain": ["AI Computing", "AI CapEx Expansion", "Order Confirmation", "Revenue Conversion"],
            "bottleneck_node": "Order Confirmation",
        },
        DummyRegime(),
    )

    assert result["symbol"] == "000977.SZ"
    assert "alpha_score" in result
    assert "risk_score" in result
    assert result["macro_regime"] == "BEAR"
    assert result["sector_context"]["sector"] == "AI Computing"
    assert "final_allocation" in result
    assert result["audit_trail"]["event_type"] == "V11_AGENT_DECISION"


def test_arbitrator_prevents_single_agent_override() -> None:
    sector_engine = V10SectorEngine.from_results(
        [DummyResult("000977.SZ", "浪潮信息", "AI算力", 80.0)]
    )
    orchestrator = V11AgentOrchestrator(sector_engine, V10AuditEngine(_audit_path()))

    result = orchestrator.run(
        {
            "symbol": "000977.SZ",
            "action": "ADD",
            "confidence": 0.9,
            "risk_score": 0.9,
            "portfolio_exposure": 0.5,
            "causal_chain": ["A", "B", "C", "D", "E"],
        },
        DummyRegime(regime="STRUCTURAL"),
    )

    assert result["conflict_detected"] is True
    assert result["final_action"] in {"HOLD", "REDUCE"}
    assert result["final_action"] != "ADD"
    assert result["final_allocation"] == 0.0
