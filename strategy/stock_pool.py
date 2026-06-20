"""股票池构建模块。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


@dataclass
class StockPoolConfig:
    """股票池构建参数。"""

    min_market_cap: float | None = None
    allow_st: bool = False
    excluded_industries: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class SampleStockRecord:
    """样例标的记录。"""

    code: str
    name: str
    theme: str
    tau_score: float
    ai_compute_score: float
    ascend_supernode_score: float
    domestic_substitution_score: float
    advanced_material_score: float
    packaging_score: float


def build_stock_pool(
    universe: Iterable[str],
    config: StockPoolConfig | None = None,
) -> list[str]:
    """根据基础规则构建研究股票池。"""

    _ = config
    return [ticker for ticker in universe if ticker]


def load_sample_stock_pool(csv_path: str | Path) -> list[SampleStockRecord]:
    """读取样例 A 股标的池。"""

    path = Path(csv_path)
    records: list[SampleStockRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            records.append(
                SampleStockRecord(
                    code=str(row["code"]),
                    name=str(row["name"]),
                    theme=str(row["theme"]),
                    tau_score=float(row["tau_score"]),
                    ai_compute_score=float(row["ai_compute_score"]),
                    ascend_supernode_score=float(row["ascend_supernode_score"]),
                    domestic_substitution_score=float(row["domestic_substitution_score"]),
                    advanced_material_score=float(row["advanced_material_score"]),
                    packaging_score=float(row["packaging_score"]),
                )
            )
    return records
