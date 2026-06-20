"""Test financial cross validation across AkShare and Tushare."""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data_mapping import DataMappingLayer
from core.financial_cross_validator import FinancialCrossValidator
from data_sources.akshare_provider import AkShareDataProvider
from data_sources.tushare_provider import TushareDataProvider


def main() -> None:
    codes = ["000977.SZ", "688041.SH", "002371.SZ"]
    akshare_provider = AkShareDataProvider()
    tushare_provider = TushareDataProvider()
    validator = FinancialCrossValidator()
    mapping = DataMappingLayer()

    print(f"akshare_available={akshare_provider.akshare_available}")
    print(f"tushare_available={tushare_provider.tushare_available}")

    for code in codes:
        akshare_summary = dict(akshare_provider.get_financial_summary(code))
        tushare_summary = dict(tushare_provider.get_financial_summary(code))
        cross_validation_result = validator.compare_financial_summary(akshare_summary, tushare_summary)
        factor_input = mapping.build_factor_input(code)

        print(f"\n=== {code} ===")
        print("AkShare 财务摘要:")
        print(pformat(akshare_summary, width=120))
        print("Tushare 财务摘要:")
        print(pformat(tushare_summary, width=120))
        print("Cross Validation Result:")
        print(pformat(cross_validation_result, width=120))
        print("Factor Input Financial Summary:")
        print(pformat(factor_input.get("financial_summary"), width=120))


if __name__ == "__main__":
    main()
