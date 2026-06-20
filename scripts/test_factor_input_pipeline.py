"""Smoke test for the factor input pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data_mapping import DataMappingLayer


def _is_mapping_like(value: Any) -> bool:
    return isinstance(value, dict)


def main() -> None:
    mapping = DataMappingLayer()
    payload = mapping.build_factor_input("000001.SZ")

    if not _is_mapping_like(payload):
        raise TypeError(f"build_factor_input should return dict-like data, got {type(payload)!r}")

    required_fields = [
        "company_basic_info",
        "financial_summary",
        "order_signals",
        "news_signals",
        "theme_signals",
    ]

    for field_name in required_fields:
        field_payload = payload.get(field_name)
        if not isinstance(field_payload, dict):
            raise TypeError(f"{field_name} should be a dict, got {type(field_payload)!r}")
        for key in ["data", "provider_used", "fallback_used", "timestamp"]:
            if key not in field_payload:
                raise KeyError(f"{field_name} missing required key: {key}")

    print(f"build_factor_input_ok=True")
    print(f"provider_used_present={all('provider_used' in payload[f] for f in required_fields)}")
    print(f"fallback_used_present={all('fallback_used' in payload[f] for f in required_fields)}")
    print(f"output_is_dict={isinstance(payload, dict)}")


if __name__ == "__main__":
    main()
