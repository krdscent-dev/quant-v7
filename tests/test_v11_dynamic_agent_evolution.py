"""Tests for V11.3 dynamic agent evolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agents.agent_factory import AgentFactory
from agents.agent_lifecycle_manager import AgentLifecycleManager
from agents.agent_performance_tracker import AgentPerformanceTracker
from agents.agent_registry import AgentRegistry
from core.v10_audit_engine import V10AuditEngine
from core.v10_sector_engine import V10SectorEngine
from core.v11_agents import V11AgentOrchestrator


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
    path = Path.cwd() / "reports" / "cache" / f"v113_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_agent_factory_creates_promotion_variant() -> None:
    variant = AgentFactory().create_variant_for("AlphaAgent")

    assert variant is not None
    assert variant.agent_name == "MomentumAgent"
    assert variant.parent_agent == "AlphaAgent"


def test_agent_registry_tracks_active_agents() -> None:
    registry = AgentRegistry()

    assert "AlphaAgent" in registry.active_agent_names()
    registry.remove("AlphaAgent")
    assert "AlphaAgent" not in registry.active_agent_names()


def test_lifecycle_removes_weak_agent() -> None:
    summary = AgentPerformanceTracker().summarize(
        [{"agent_name": "AlphaAgent", "outcome": "LOSS", "pnl_contribution": -0.3}]
    )

    result = AgentLifecycleManager().evaluate(summary, {"AlphaAgent": 0.2})

    assert "AlphaAgent" in result.removed_agents
    assert result.performance_scores["AlphaAgent"] < 0.4


def test_lifecycle_promotes_strong_agent() -> None:
    summary = AgentPerformanceTracker().summarize(
        [
            {"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.2},
            {"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.1},
        ]
    )

    result = AgentLifecycleManager().evaluate(summary, {"AlphaAgent": 0.4})

    assert "AlphaAgent" in result.promoted_agents
    assert "MomentumAgent" in result.newly_created_agents
    assert "MomentumAgent" in result.active_agents


def test_orchestrator_outputs_v113_lifecycle_fields() -> None:
    sector_engine = V10SectorEngine.from_results(
        [DummyResult("000977.SZ", "sample", "AI Computing", 80.0)]
    )
    orchestrator = V11AgentOrchestrator(sector_engine, V10AuditEngine(_audit_path()))

    result = orchestrator.run(
        {
            "symbol": "000977.SZ",
            "action": "SMALL_ADD",
            "confidence": 0.8,
            "risk_score": 0.2,
            "portfolio_exposure": 0.1,
            "causal_chain": ["AI Computing", "Order Confirmation", "Revenue Conversion"],
        },
        DummyRegime("STRUCTURAL"),
        agent_performance_log=[
            {"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.2},
            {"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.1},
        ],
    )

    assert "active_agents" in result
    assert "removed_agents" in result
    assert "newly_created_agents" in result
    assert "agent_performance_scores" in result
    assert "MomentumAgent" in result["active_agents"]
