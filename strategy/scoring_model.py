"""综合评分模型模块。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass
class ScoringWeights:
    """综合评分权重。"""

    tau: float = 0.33
    ascend_supernode: float = 0.33
    domestic_substitution: float = 0.34


@dataclass
class StockScore:
    """单股综合评分结果。"""

    ticker: str
    total_score: float
    components: Mapping[str, float] = field(default_factory=dict)


def score_stock(
    ticker: str,
    tau_score: float,
    ascend_supernode_score: float,
    domestic_substitution_score: float,
    weights: ScoringWeights | None = None,
) -> StockScore:
    """计算股票综合评分。"""

    w = weights or ScoringWeights()
    total_score = (
        tau_score * w.tau
        + ascend_supernode_score * w.ascend_supernode
        + domestic_substitution_score * w.domestic_substitution
    )
    return StockScore(
        ticker=ticker,
        total_score=total_score,
        components={
            "tau": tau_score,
            "ascend_supernode": ascend_supernode_score,
            "domestic_substitution": domestic_substitution_score,
        },
    )
