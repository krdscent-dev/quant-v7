"""股票池构建模块。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass
class StockPoolConfig:
    """股票池构建参数。"""

    min_market_cap: float | None = None
    allow_st: bool = False
    excluded_industries: Sequence[str] = field(default_factory=tuple)


def build_stock_pool(
    universe: Iterable[str],
    config: StockPoolConfig | None = None,
) -> list[str]:
    """根据基础规则构建研究股票池。"""

    _ = config
    return [ticker for ticker in universe if ticker]
