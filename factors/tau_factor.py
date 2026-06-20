"""τ因子研究模块。

用于定义与 τ 因子相关的计算接口、数据结构和后续扩展点。
当前只提供函数骨架，便于后续接入真实行情与基本面数据。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class TauFactorResult:
    """τ因子计算结果。"""

    ticker: str
    score: float
    details: Mapping[str, float]


def calculate_tau_factor(
    market_data: Mapping[str, Any],
    fundamentals: Mapping[str, Any] | None = None,
) -> TauFactorResult:
    """计算单只股票的 τ 因子。"""

    ticker = str(market_data.get("ticker", "UNKNOWN"))
    _ = fundamentals
    return TauFactorResult(ticker=ticker, score=0.0, details={})
