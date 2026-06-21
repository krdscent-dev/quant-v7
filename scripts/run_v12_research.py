"""Run the pure V12 research and evaluation engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.v12_research_evaluation_engine import run_v12_research_evaluation
from core.v12_research_report import V12ResearchReport


def main() -> int:
    result = run_v12_research_evaluation()
    report_paths = V12ResearchReport().write(result)
    print(report_paths["markdown"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
