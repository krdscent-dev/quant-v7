"""Smoke test for the AkShare real data integration phase 1."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_sources.akshare_provider import AkShareDataProvider


def _print_payload(title: str, payload: Any) -> None:
    print(title)
    print(payload)
    print("---")


def main() -> None:
    provider = AkShareDataProvider()
    print(f"akshare_available={provider.akshare_available}")

    for code in ["000977.SZ", "688041.SH", "002371.SZ"]:
        basic = provider.get_company_basic_info(code)
        financial = provider.get_financial_summary(code)
        _print_payload(f"company_basic_info[{code}]", basic)
        _print_payload(f"financial_summary[{code}]", financial)


if __name__ == "__main__":
    main()
