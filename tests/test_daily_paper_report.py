from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from reporting.daily_paper_report import DailyPaperReport


def test_daily_paper_report_writes_markdown():
    with TemporaryDirectory() as temp_dir:
        report = DailyPaperReport(Path(temp_dir))
        payload = {
            "timestamp": "2026-06-21T15:00:00+08:00",
            "source_status": "LIVE",
            "portfolio_snapshot": {
                "portfolio_value": 1_012_345.67,
                "daily_pnl": 12_345.67,
                "drawdown": 0.0123,
                "cash": 900_000.0,
                "positions": [
                    {
                        "symbol": "000001",
                        "quantity": 100.0,
                        "average_cost": 10.0,
                        "last_price": 11.0,
                        "market_value": 1_100.0,
                        "unrealized_pnl": 100.0,
                    }
                ],
            },
            "decisions": [
                {
                    "symbol": "000001",
                    "sector": "AI Computing",
                    "action": "BUY",
                    "confidence": 0.82,
                    "alpha_score": 78.5,
                    "reason": "strong theme",
                    "data_status": "LIVE",
                }
            ],
            "trade_records": [],
            "market_state": {
                "structure": {"regime": "BULL", "trend_score": 0.75, "volatility_state": "LOW", "structure_strength": 0.68},
                "capital_flow": {"flow_strength": 0.8},
                "narrative": {"narrative_phase": "EXPANSION"},
                "cycle": {"unified_cycle_state": "RISK_ON"},
            },
            "capital_state": {
                "risk_mode": "AGGRESSIVE",
                "position_multiplier": 1.2,
                "risk_budget": 0.8,
                "exposure_limit": 1.0,
                "leverage_adjustment": 1.1,
            },
            "warnings": [],
        }
        path = report.write(payload)
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "# Daily Paper Trading Report" in text
        assert "Current portfolio value" in text
        assert "000001" in text
