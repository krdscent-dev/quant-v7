"""Tests for V12.4 cycle intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass

from core.decision_engine import DecisionEngine
from core.v11_agents import MacroAgent, PortfolioAgent, RiskAgent, SectorAgent
from market.v12_4_cycle_engine import V124CycleEngine


@dataclass(frozen=True)
class DummyRegime:
    regime: str
    trend: float = 0.5
    volatility: float = 0.3
    confidence: float = 0.8


def test_v124_detects_liquidity_cycle() -> None:
    engine = V124CycleEngine()

    assert engine.detect_liquidity_cycle(0.75).cycle == "EXPANSION"
    assert engine.detect_liquidity_cycle(0.30).cycle == "CONTRACTION"


def test_v124_detects_sentiment_cycle() -> None:
    engine = V124CycleEngine()

    assert engine.detect_sentiment_cycle(80.0).cycle == "PANIC"
    assert engine.detect_sentiment_cycle(20.0).cycle == "GREED"
    assert engine.detect_sentiment_cycle(50.0).cycle == "NEUTRAL"


def test_v124_detects_industry_cycle() -> None:
    engine = V124CycleEngine()

    assert engine.detect_industry_cycle(0.80, 0.30).cycle == "EARLY_GROWTH"
    assert engine.detect_industry_cycle(0.72, 0.60).cycle == "EXPANSION"
    assert engine.detect_industry_cycle(0.52, 0.75).cycle == "MATURITY"
    assert engine.detect_industry_cycle(0.25, 0.55).cycle == "DECLINE"


def test_v124_build_cycle_state_combines_signals() -> None:
    state = V124CycleEngine().build_cycle_state(
        {"liquidity_score": 0.82},
        {"fear_index": 18.0},
        {"industry_growth": 0.78, "valuation_score": 0.30},
    )

    assert state.combined_cycle_state == "RISK_ON"
    assert state.risk_appetite == "RISING"
    assert state.aggressiveness > 1.0


def test_v124_same_signal_differs_by_cycle_for_decision_engine() -> None:
    engine = DecisionEngine()
    bullish = engine.decide(
        symbol="000977.SZ",
        score=72.0,
        regime=DummyRegime("RANGE"),
        confidence=0.75,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.60,
            "sector_leader_flag": False,
            "combined_cycle_state": "RISK_ON",
            "risk_appetite": "RISING",
            "liquidity_cycle": "EXPANSION",
            "sentiment_cycle": "GREED",
            "industry_cycle": "EXPANSION",
        },
    )
    defensive = engine.decide(
        symbol="000977.SZ",
        score=72.0,
        regime=DummyRegime("RANGE"),
        confidence=0.75,
        context={
            "sector": "AI Computing",
            "sector_strength": 0.60,
            "sector_leader_flag": False,
            "combined_cycle_state": "STRESS",
            "risk_appetite": "FALLING",
            "liquidity_cycle": "CONTRACTION",
            "sentiment_cycle": "PANIC",
            "industry_cycle": "DECLINE",
        },
    )

    assert bullish["action"] != defensive["action"]
    assert bullish["action"] in {"HOLD", "SMALL_ADD", "ADD"}
    assert defensive["action"] in {"OBSERVE", "HOLD", "SMALL_ADD"}


def test_v124_portfolio_agent_uses_cycle_aggressiveness() -> None:
    macro = MacroAgent().evaluate(DummyRegime("RANGE"))
    sector = SectorAgent.__new__(SectorAgent)
    sector.payload = {  # type: ignore[attr-defined]
        "sector": "AI Computing",
        "sector_strength": 0.92,
        "sector_leader_flag": True,
        "sector_rank": 1,
        "rotation_signal": "LEADER_CONCENTRATION",
    }
    alpha = type("Alpha", (), {"payload": {"alpha_score": 0.82}})()
    risk = RiskAgent().evaluate(
        {
            "symbol": "000977.SZ",
            "risk_score": 0.15,
            "portfolio_exposure": 0.1,
        }
    )
    base_decision = {
        "symbol": "000977.SZ",
        "action": "HOLD",
    }
    portfolio_agent = PortfolioAgent()

    bullish = portfolio_agent.evaluate(
        base_decision,
        macro,
        sector,  # type: ignore[arg-type]
        alpha,  # type: ignore[arg-type]
        risk,
        cycle={
            "risk_appetite": "RISING",
            "combined_cycle_state": "RISK_ON",
            "aggressiveness": 1.15,
            "liquidity_cycle": "EXPANSION",
            "sentiment_cycle": "GREED",
            "industry_cycle": "EXPANSION",
        },
    )
    defensive = portfolio_agent.evaluate(
        base_decision,
        macro,
        sector,  # type: ignore[arg-type]
        alpha,  # type: ignore[arg-type]
        risk,
        cycle={
            "risk_appetite": "FALLING",
            "combined_cycle_state": "STRESS",
            "aggressiveness": 0.65,
            "liquidity_cycle": "CONTRACTION",
            "sentiment_cycle": "PANIC",
            "industry_cycle": "DECLINE",
        },
    )

    assert bullish.payload["final_action"] != defensive.payload["final_action"]
    assert bullish.payload["final_allocation"] >= defensive.payload["final_allocation"]
