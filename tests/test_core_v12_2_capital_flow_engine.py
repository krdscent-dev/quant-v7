from __future__ import annotations

from core.v12_2_capital_flow_engine import CapitalFlowEngine, analyze_capital_flow


def test_core_capital_flow_ranks_inflow_sectors() -> None:
    result = analyze_capital_flow(
        {
            "sector_data": {
                "AI": 120.0,
                "Semiconductor": 90.0,
                "Materials": 30.0,
            },
            "stock_data": {
                "AAA": {"volume": 80.0, "price_change": 0.06, "is_leader": True},
                "BBB": {"volume": 20.0, "price_change": 0.02, "is_leader": False},
            },
        }
    )

    assert result["top_inflow_sectors"][0] == "AI"
    assert result["flow_strength"] > 0.0
    assert 0.0 <= result["leader_concentration"] <= 1.0
    assert result["rotation_signal"] in {
        "AI_LEAD_ROTATION",
        "CHIP_CYCLE_EXPANSION",
        "MID_LATE_CYCLE_ROTATION",
        "NO_CLEAR_ROTATION",
    }


def test_core_capital_flow_defaults_when_sector_data_missing() -> None:
    result = CapitalFlowEngine().analyze_capital_flow({})

    assert result == {
        "top_inflow_sectors": [],
        "top_outflow_sectors": [],
        "flow_strength": 0.5,
        "leader_concentration": 0.0,
        "rotation_signal": "UNKNOWN",
    }


def test_core_capital_flow_detects_leader_concentration() -> None:
    result = analyze_capital_flow(
        {
            "sector_data": {"AI": 100.0},
            "stock_data": {
                "AAA": {"volume": 70.0, "price_change": 0.05, "is_leader": True},
                "BBB": {"volume": 30.0, "price_change": -0.01, "is_leader": False},
            },
        }
    )

    assert result["leader_concentration"] == 0.7

