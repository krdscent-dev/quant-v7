"""简单回测模块。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import sys

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from strategy.stock_pool import SampleStockRecord, load_sample_stock_pool


@dataclass
class BacktestResult:
    """简单回测结果。"""

    total_return: float
    benchmark_return: float | None
    max_drawdown: float | None
    trades: int


@dataclass(frozen=True)
class RankedStock:
    """排序后的标的记录。"""

    code: str
    name: str
    theme: str
    total_score: float
    tau_score: float
    ai_compute_score: float
    ascend_supernode_score: float
    domestic_substitution_score: float
    advanced_material_score: float
    packaging_score: float


def compute_total_score(record: SampleStockRecord) -> float:
    """按 V7 公式计算总分。"""

    return (
        0.25 * record.tau_score
        + 0.20 * record.ai_compute_score
        + 0.20 * record.ascend_supernode_score
        + 0.15 * record.domestic_substitution_score
        + 0.10 * record.advanced_material_score
        + 0.10 * record.packaging_score
    )


def run_simple_backtest(
    signals: Sequence[float],
    prices: Sequence[float],
    benchmark_prices: Sequence[float] | None = None,
) -> BacktestResult:
    """运行一个最小化的回测流程。"""

    _ = signals
    _ = prices
    _ = benchmark_prices
    return BacktestResult(
        total_return=0.0,
        benchmark_return=None,
        max_drawdown=None,
        trades=0,
    )


def rank_sample_pool(
    sample_pool_path: str | Path,
    output_path: str | Path,
) -> list[RankedStock]:
    """读取样例池，计算总分并输出排序结果。"""

    records = load_sample_stock_pool(sample_pool_path)
    ranked = sorted(
        (
            RankedStock(
                code=record.code,
                name=record.name,
                theme=record.theme,
                total_score=compute_total_score(record),
                tau_score=record.tau_score,
                ai_compute_score=record.ai_compute_score,
                ascend_supernode_score=record.ascend_supernode_score,
                domestic_substitution_score=record.domestic_substitution_score,
                advanced_material_score=record.advanced_material_score,
                packaging_score=record.packaging_score,
            )
            for record in records
        ),
        key=lambda item: item.total_score,
        reverse=True,
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "code",
                "name",
                "theme",
                "total_score",
                "tau_score",
                "ai_compute_score",
                "ascend_supernode_score",
                "domestic_substitution_score",
                "advanced_material_score",
                "packaging_score",
            ]
        )
        for index, item in enumerate(ranked, start=1):
            writer.writerow(
                [
                    index,
                    item.code,
                    item.name,
                    item.theme,
                    f"{item.total_score:.4f}",
                    f"{item.tau_score:.4f}",
                    f"{item.ai_compute_score:.4f}",
                    f"{item.ascend_supernode_score:.4f}",
                    f"{item.domestic_substitution_score:.4f}",
                    f"{item.advanced_material_score:.4f}",
                    f"{item.packaging_score:.4f}",
                ]
            )
    return ranked


def main() -> None:
    """脚本入口。"""

    base_dir = Path(__file__).resolve().parents[1]
    sample_pool_path = base_dir / "data" / "processed" / "sample_stock_pool.csv"
    output_path = base_dir / "reports" / "sample_ranking.csv"
    ranked = rank_sample_pool(sample_pool_path, output_path)
    print(f"Ranked {len(ranked)} sample stocks -> {output_path}")


if __name__ == "__main__":
    main()
