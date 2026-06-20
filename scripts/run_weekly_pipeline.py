"""Unified entry point for the weekly research pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.weekly_pipeline import generate_weekly_report


def main() -> None:
    output_path = generate_weekly_report()
    print(f"weekly_report_written={output_path.as_posix()}")


if __name__ == "__main__":
    main()

