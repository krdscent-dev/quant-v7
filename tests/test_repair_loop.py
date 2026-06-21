from __future__ import annotations

from tempfile import TemporaryDirectory
import os
from types import SimpleNamespace

from backtest.v12_6_backtest_engine import V126BacktestEngine
from diagnosis.bias_detector import BiasFinding
from diagnosis.repair_engine import RepairEngine
from diagnosis.v12_7_health_monitor import HealthAssessment
from repair_loop.repair_orchestrator import RepairOrchestrator
from repair_loop.human_approval_gate import HumanApprovalGate
from logs.trade_logger import TradeLogger


def _sample_state():
    return {
        "market_state": {"regime": "TRANSITION", "structure": SimpleNamespace(structure_strength=0.6)},
        "capital_state": {"capital_bias": "BALANCED", "allocation_ceiling": 0.1, "risk_score": 0.2},
        "learning_context": {"confidence_bias": 0.02, "confidence_sensitivity": 1.0},
        "agent_weights": {"RiskAgent": 0.41, "AlphaAgent": 0.22},
        "decisions": [],
        "v11_decisions": [
            {
                "symbol": "000977.SZ",
                "final_weighted_decision": "SMALL_ADD",
                "alpha_score": 1.0,
                "risk_score": 0.2,
                "sector_context": {"sector": "AI Computing", "sector_strength": 0.95},
                "market_intelligence": {"capital_flow_score": 0.9},
            }
        ],
    }


def test_repair_loop_waits_for_approval():
    previous = os.environ.pop("V12_8_REPAIR_APPROVAL", None)
    try:
        with TemporaryDirectory() as temp_dir:
            state = _sample_state()
            engine = V126BacktestEngine(trade_logger=TradeLogger(f"{temp_dir}/trade_log.jsonl"))
            pre_backtest = engine.simulate(
                market_state=state["market_state"],
                capital_state=state["capital_state"],
                decisions=state["decisions"],
                v11_decisions=state["v11_decisions"],
                periods=2,
            )
            suggestions = RepairEngine().propose(
                HealthAssessment(
                    status="WARNING",
                    severity="MEDIUM",
                    drawdown_risk="MANAGEABLE",
                    accuracy_risk="MANAGEABLE",
                    risk_level="LOW",
                    score=0.7,
                    warnings=[],
                ),
                [BiasFinding("risk_overweight", "MEDIUM", "risk heavy", {"risk_weight": 0.41})],
                {"total_return": pre_backtest.total_return},
            )
            report = RepairOrchestrator(backtest_engine=engine).run(
                health=HealthAssessment(
                    status="WARNING",
                    severity="MEDIUM",
                    drawdown_risk="MANAGEABLE",
                    accuracy_risk="MANAGEABLE",
                    risk_level="LOW",
                    score=0.7,
                    warnings=[],
                ),
                biases=[BiasFinding("risk_overweight", "MEDIUM", "risk heavy", {"risk_weight": 0.41})],
                suggestions=suggestions,
                current_state=state,
                pre_fix_backtest=pre_backtest,
            )

            assert report.approval.status == "PENDING"
            assert report.post_fix_backtest is None
            assert report.comparison["status"] == "PENDING_APPROVAL"
    finally:
        if previous is not None:
            os.environ["V12_8_REPAIR_APPROVAL"] = previous


def test_repair_loop_applies_when_approved():
    previous = os.environ.get("V12_8_REPAIR_APPROVAL")
    os.environ["V12_8_REPAIR_APPROVAL"] = "APPROVE"
    try:
        with TemporaryDirectory() as temp_dir:
            state = _sample_state()
            engine = V126BacktestEngine(trade_logger=TradeLogger(f"{temp_dir}/trade_log.jsonl"))
            pre_backtest = engine.simulate(
                market_state=state["market_state"],
                capital_state=state["capital_state"],
                decisions=state["decisions"],
                v11_decisions=state["v11_decisions"],
                periods=2,
            )
            suggestions = RepairEngine().propose(
                HealthAssessment(
                    status="CRITICAL",
                    severity="HIGH",
                    drawdown_risk="ELEVATED",
                    accuracy_risk="ELEVATED",
                    risk_level="HIGH",
                    score=0.3,
                    warnings=["max_drawdown_above_10pct"],
                ),
                [
                    BiasFinding("risk_overweight", "HIGH", "risk heavy", {"risk_weight": 0.45}),
                    BiasFinding("confidence_calibration_bias", "MEDIUM", "confidence drift", {"confidence_bias": "underconfidence_bias_detected"}),
                ],
                {"total_return": pre_backtest.total_return},
            )
            report = RepairOrchestrator(backtest_engine=engine).run(
                health=HealthAssessment(
                    status="CRITICAL",
                    severity="HIGH",
                    drawdown_risk="ELEVATED",
                    accuracy_risk="ELEVATED",
                    risk_level="HIGH",
                    score=0.3,
                    warnings=["max_drawdown_above_10pct"],
                ),
                biases=[
                    BiasFinding("risk_overweight", "HIGH", "risk heavy", {"risk_weight": 0.45}),
                    BiasFinding("confidence_calibration_bias", "MEDIUM", "confidence drift", {"confidence_bias": "underconfidence_bias_detected"}),
                ],
                suggestions=suggestions,
                current_state=state,
                pre_fix_backtest=pre_backtest,
            )

            assert report.approval.status == "APPROVED"
            assert report.post_fix_backtest is not None
            assert report.applied_patches
            assert report.comparison["status"] == "REPAIRED"
    finally:
        if previous is None:
            os.environ.pop("V12_8_REPAIR_APPROVAL", None)
        else:
            os.environ["V12_8_REPAIR_APPROVAL"] = previous
