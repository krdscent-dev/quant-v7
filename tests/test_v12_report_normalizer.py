from __future__ import annotations

from core.v12_report_normalizer import (
    V12ReportNormalizer,
    calculate_decision_score,
    normalize_v12_report,
)
from core.v12_report_schema import V12ReportSchema


def test_v12_report_normalizer_produces_unified_schema():
    raw_report = {
        "market_regime": {
            "structure": {"trend_score": 0.90},
            "capital_flow": {"flow_strength": 0.80},
            "narrative": {"narrative_strength": 0.60},
            "cycle_state": {"unified_cycle_state": "RISK_ON"},
            "capital_simulation": {"risk_budget": 0.78, "exposure_limit": 0.42},
            "confidence": 0.88,
        },
        "backtest_result": {"return": 0.12, "drawdown": 0.05, "win_rate": 0.67},
        "stability_score": 0.81,
        "validation": {"stability_score": 0.81, "overfit_risk": 0.18},
        "diagnosis": {"health": {"score": 0.77}, "stability": {"status": "OK"}},
        "confidence": 0.88,
    }

    normalized = V12ReportNormalizer().normalize(raw_report)

    assert set(normalized) == {
        "market_state",
        "capital_state",
        "performance",
        "system_health",
        "decision",
        "explanation",
    }
    assert normalized["market_state"]["structure"] == 0.90
    assert normalized["market_state"]["flow"] == 0.80
    assert normalized["market_state"]["narrative"] == 0.60
    assert normalized["market_state"]["cycle"] == 0.90
    assert abs(normalized["capital_state"]["risk_level"] - 0.22) < 1e-9
    assert normalized["capital_state"]["exposure"] == 0.42
    assert 0.0 <= normalized["performance"]["return"] <= 1.0
    assert normalized["performance"]["drawdown"] == 0.05
    assert normalized["performance"]["win_rate"] == 0.67
    assert normalized["system_health"]["stability"] == 0.81
    assert normalized["system_health"]["overfitting_risk"] == 0.18
    assert normalized["system_health"]["data_quality"] == 0.77
    assert normalized["decision"]["action"] == "BUY"
    assert normalized["decision"]["confidence"] == 0.88
    assert normalized["decision"]["risk_level"] == "LOW"
    assert normalized["explanation"]["dominant_driver"] == "structure"
    assert normalized["explanation"]["key_factors"][0] == "structure"
    assert abs(calculate_decision_score(normalized["market_state"]) - 0.825) < 1e-9


def test_v12_report_normalizer_falls_back_to_neutral_defaults():
    normalized = normalize_v12_report({})

    assert normalized["market_state"] == {
        "structure": 0.5,
        "flow": 0.5,
        "narrative": 0.5,
        "cycle": 0.5,
    }
    assert normalized["capital_state"] == {"risk_level": 0.5, "exposure": 0.5}
    assert normalized["performance"] == {"return": 0.5, "drawdown": 0.5, "win_rate": 0.5}
    assert normalized["system_health"] == {
        "stability": 0.5,
        "overfitting_risk": 0.5,
        "data_quality": 0.5,
    }
    assert normalized["decision"] == {
        "action": "HOLD",
        "confidence": 0.3,
        "risk_level": "MEDIUM",
    }
    assert normalized["explanation"]["dominant_driver"] == "neutral fallback"
    assert normalized["explanation"]["key_factors"] == ["structure", "flow"]


def test_v12_report_schema_round_trip():
    schema = V12ReportSchema.from_mapping(
        {
            "market_state": {"structure": 0.7, "flow": 0.6, "narrative": 0.55, "cycle": 0.8},
            "capital_state": {"risk_level": 0.2, "exposure": 0.4},
            "performance": {"return": 0.58, "drawdown": 0.12, "win_rate": 0.66},
            "system_health": {"stability": 0.78, "overfitting_risk": 0.2, "data_quality": 0.9},
            "decision": {"action": "HOLD", "confidence": 0.52, "risk_level": "MEDIUM"},
            "explanation": {"key_factors": ["structure", "cycle"], "dominant_driver": "structure"},
        }
    )

    payload = schema.to_dict()

    assert payload["market_state"]["structure"] == 0.7
    assert payload["capital_state"]["risk_level"] == 0.2
    assert payload["performance"]["return"] == 0.58
    assert payload["system_health"]["data_quality"] == 0.9
    assert payload["decision"]["action"] == "HOLD"
    assert payload["explanation"]["dominant_driver"] == "structure"
