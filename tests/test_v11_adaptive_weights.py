"""Tests for V11.2 adaptive agent weights."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agents.adaptive_governor import AdaptiveGovernor
from agents.agent_performance_tracker import AgentPerformanceTracker
from agents.decision_arbitrator import DecisionArbitrator
from agents.weight_manager import AgentWeightManager, DEFAULT_AGENT_WEIGHTS
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
    path = Path.cwd() / "reports" / "cache" / f"v112_audit_{uuid4().hex}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_performance_tracker_summarizes_agent_accuracy() -> None:
    summary = AgentPerformanceTracker().summarize(
        [
            {"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.1},
            {"agent_name": "AlphaAgent", "outcome": "LOSS", "pnl_contribution": -0.02},
            {"agent_name": "RiskAgent", "outcome": "WIN", "pnl_contribution": 0.03},
        ]
    )

    assert summary["AlphaAgent"].accuracy == 0.5
    assert summary["RiskAgent"].accuracy == 1.0


def test_weight_manager_increases_accurate_agent_weight() -> None:
    summary = AgentPerformanceTracker().summarize(
        [{"agent_name": "AlphaAgent", "outcome": "WIN", "pnl_contribution": 0.1}]
    )

    weights = AgentWeightManager().update_weights(summary)

    assert weights["AlphaAgent"] > DEFAULT_AGENT_WEIGHTS["AlphaAgent"]


def test_adaptive_governor_bear_increases_risk_weight() -> None:
    adjusted = AdaptiveGovernor().adjust_for_regime(DEFAULT_AGENT_WEIGHTS, "BEAR")

    assert adjusted["RiskAgent"] > DEFAULT_AGENT_WEIGHTS["RiskAgent"]
    assert adjusted["AlphaAgent"] < DEFAULT_AGENT_WEIGHTS["AlphaAgent"]


def test_adaptive_governor_bull_increases_alpha_weight() -> None:
    adjusted = AdaptiveGovernor().adjust_for_regime(DEFAULT_AGENT_WEIGHTS, "BULL")

    assert adjusted["AlphaAgent"] > DEFAULT_AGENT_WEIGHTS["AlphaAgent"]


def test_arbitrator_uses_dynamic_weights() -> None:
    result = DecisionArbitrator().arbitrate(
        {
            "AlphaAgent": {"suggested_action": "ADD"},
            "RiskAgent": {"risk_action": "REDUCE", "risk_score": 0.2},
            "MacroAgent": {"macro_regime": "STRUCTURAL"},
            "SectorAgent": {"sector_strength": 0.9},
            "PortfolioAgent": {"final_action": "ADD"},
        },
        agent_weights={
            "RiskAgent": 0.60,
            "AlphaAgent": 0.15,
            "MacroAgent": 0.10,
            "SectorAgent": 0.10,
            "PortfolioAgent": 0.05,
        },
    )

    assert result["agent_weights"]["RiskAgent"] == 0.60
    assert result["final_decision"] in {"HOLD", "REDUCE"}


def test_orchestrator_outputs_v112_fields() -> None:
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
            "causal_chain": ["AI Computing", "Order Confirmation", "Revenue Conversion"],
        },
        DummyRegime("BEAR"),
    )

    assert "current_agent_weights" in result
    assert "regime_adjusted_weights" in result
    assert "final_weighted_decision" in result
    assert "agent_performance_summary" in result
