"""国产替代主题因子模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class DomesticSubstitutionResult:
    """国产替代因子结果。"""

    ticker: str
    score: float
    components: Mapping[str, float]


def calculate_domestic_substitution_factor(
    supply_chain_data: Mapping[str, Any],
    policy_signals: Mapping[str, Any] | None = None,
) -> DomesticSubstitutionResult:
    """计算国产替代主题评分。"""

    ticker = str(supply_chain_data.get("ticker", "UNKNOWN"))
    _ = policy_signals
    return DomesticSubstitutionResult(ticker=ticker, score=0.0, components={})
