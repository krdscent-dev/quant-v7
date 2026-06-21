from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from core.v12_research_evaluation_engine import V12ResearchEvaluationEngine
from core.v12_research_report import V12ResearchReport
from portfolio.multi_symbol_data_engine import SymbolSnapshot


@dataclass
class MockSymbolEngine:
    snapshots: list[SymbolSnapshot]

    def fetch_symbols(self, symbols):
        return list(self.snapshots)


@dataclass
class MockBacktestEngine:
    total_return: float = 0.12
    max_drawdown: float = 0.05
    win_rate: float = 0.67

    def simulate(self, historical_market_data):
        return SimpleNamespace(
            total_return=self.total_return,
            max_drawdown=self.max_drawdown,
            win_rate=self.win_rate,
            trade_log=[
                {"symbol": "000001", "action": "HOLD", "pnl": 0.01},
                {"symbol": "300750", "action": "ADD", "pnl": 0.02},
            ],
            warnings=[],
            volatility=0.18,
        )


@dataclass
class MockValidationEngine:
    backtest_engine: MockBacktestEngine

    def validate(self, historical_market_data):
        return {
            "stability_score": 0.82,
            "profit_score": 0.71,
            "overfit_risk": 0.18,
            "overall_score": 0.77,
            "failure_points": [],
            "recommendation": "System is robust enough for controlled production use.",
        }


def _snapshot(symbol: str, sector: str, close: float, trend: float, volatility: float, momentum: float) -> SymbolSnapshot:
    return SymbolSnapshot(
        symbol=symbol,
        trend=trend,
        volatility=volatility,
        momentum=momentum,
        breadth=0.61,
        liquidity=0.58,
        volume_pressure=0.63,
        close=close,
        data_source="LIVE",
        data_status="LIVE",
        timestamp="2026-06-21T15:00:00+08:00",
    )


def test_v12_research_evaluation_outputs_structured_report():
    snapshots = [
        _snapshot("000001", "AI Computing", 10.5, 0.74, 0.18, 0.62),
        _snapshot("300750", "Domestic Substitution", 120.0, 0.82, 0.12, 0.70),
    ]
    engine = V12ResearchEvaluationEngine(
        symbol_engine=MockSymbolEngine(snapshots),
        backtest_engine=MockBacktestEngine(),
        validation_engine=MockValidationEngine(MockBacktestEngine()),
        output_dir=Path("reports") / "research_test",
    )

    with patch(
        "core.v12_research_evaluation_engine.run_research_pipeline",
        side_effect=lambda symbol: {
            "strategic_score": 78.0 if symbol == "300750" else 66.0,
            "catalyst_strength": 61.0,
            "order_confirmation_level": 72.0,
            "research_conclusion": "theme remains valid",
            "factor_input_summary": {"provider_summary": {"financial_summary": {"confidence_score": 0.88}}},
        },
    ):
        result = engine.evaluate(symbols=("000001", "300750"))

    assert result["market_regime"]["structure"]["regime"] in {"BULL", "BEAR", "RANGE", "TRANSITION"}
    assert result["capital_flow"]["flow_strength"] >= 0.0
    assert result["narrative"]["narrative_strength"] >= 0.0
    assert result["cycle_state"]["unified_cycle_state"] in {"RISK_ON", "RISK_OFF", "TRANSITION"}
    assert result["strategy_score"] == 72.0
    assert result["stability_score"] == 0.82
    assert result["risk_score"] >= 0.0
    assert result["backtest_result"] == {"return": 0.12, "drawdown": 0.05, "win_rate": 0.67}
    assert result["recommendation"] in {"GO", "NO_GO", "NEED_OPTIMIZATION"}
    assert "health" in result["diagnosis"]


def test_v12_research_report_writes_markdown_and_json():
    snapshots = [
        _snapshot("000001", "AI Computing", 10.5, 0.74, 0.18, 0.62),
    ]
    engine = V12ResearchEvaluationEngine(
        symbol_engine=MockSymbolEngine(snapshots),
        backtest_engine=MockBacktestEngine(),
        validation_engine=MockValidationEngine(MockBacktestEngine()),
        output_dir=Path("reports") / "research_test",
    )
    with patch(
        "core.v12_research_evaluation_engine.run_research_pipeline",
        return_value={
            "strategic_score": 75.0,
            "catalyst_strength": 60.0,
            "order_confirmation_level": 70.0,
            "research_conclusion": "theme remains valid",
            "factor_input_summary": {"provider_summary": {"financial_summary": {"confidence_score": 0.90}}},
        },
    ):
        result = engine.evaluate(symbols=("000001",))

    with TemporaryDirectory() as temp_dir:
        report = V12ResearchReport(Path(temp_dir))
        paths = report.write(result)
        assert Path(paths["markdown"]).exists()
        assert Path(paths["json"]).exists()
        markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
        assert "NO LIVE TRADING" not in markdown
        assert "V12 Research & Evaluation Report" in markdown
