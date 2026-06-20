"""综合评分模型模块。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass
class ScoringWeights:
    """综合评分权重。"""

    tau: float = 0.25
    ai_compute: float = 0.20
    ascend_supernode: float = 0.20
    domestic_substitution: float = 0.15
    advanced_material: float = 0.10
    packaging: float = 0.10


@dataclass
class StockScore:
    """单股综合评分结果。"""

    ticker: str
    total_score: float
    components: Mapping[str, float] = field(default_factory=dict)


def score_stock(
    ticker: str,
    tau_score: float,
    ai_compute_score: float,
    ascend_supernode_score: float,
    domestic_substitution_score: float,
    advanced_material_score: float,
    packaging_score: float,
    weights: ScoringWeights | None = None,
) -> StockScore:
    """计算股票综合评分。

    总评分公式:
        total_score = 0.25 * tau_score
                    + 0.20 * ai_compute_score
                    + 0.20 * ascend_supernode_score
                    + 0.15 * domestic_substitution_score
                    + 0.10 * advanced_material_score
                    + 0.10 * packaging_score
    """

    w = weights or ScoringWeights()
    total_score = (
        tau_score * w.tau
        + ai_compute_score * w.ai_compute
        + ascend_supernode_score * w.ascend_supernode
        + domestic_substitution_score * w.domestic_substitution
        + advanced_material_score * w.advanced_material
        + packaging_score * w.packaging
    )
    return StockScore(
        ticker=ticker,
        total_score=total_score,
        components={
            "tau": tau_score,
            "ai_compute": ai_compute_score,
            "ascend_supernode": ascend_supernode_score,
            "domestic_substitution": domestic_substitution_score,
            "advanced_material": advanced_material_score,
            "packaging": packaging_score,
        },
    )
