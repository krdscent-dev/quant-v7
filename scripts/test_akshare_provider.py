"""Smoke tests for the AkShare adapter layer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_sources.akshare_provider import AkShareDataProvider, ak


def _is_mapping_like(value: Any) -> bool:
    return isinstance(value, dict)


def main() -> None:
    provider = AkShareDataProvider()

    print(f"akshare_installed={ak is not None}")
    print(f"provider_initialized={provider.akshare_available}")

    methods = [
        ("get_company_basic_info", provider.get_company_basic_info("000001.SZ")),
        ("get_financial_summary", provider.get_financial_summary("000001.SZ")),
        ("get_order_signals", provider.get_order_signals("000001.SZ")),
        ("get_news_signals", provider.get_news_signals("000001.SZ")),
        ("get_theme_signals", provider.get_theme_signals("000001.SZ")),
    ]

    for method_name, payload in methods:
        if not _is_mapping_like(payload):
            raise TypeError(f"{method_name} should return dict-like data, got {type(payload)!r}")
        print(f"{method_name}=ok status={payload.get('status', 'unknown')}")

    if ak is None:
        print("akshare_missing_graceful_degradation=ok")
    else:
        print("akshare_present_adapter_payloads=ok")


if __name__ == "__main__":
    main()
