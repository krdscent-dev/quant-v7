"""Smoke test for the integrated research pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.research_engine import run_research_pipeline


def main() -> None:
    company_code = "000001.SZ"
    result = run_research_pipeline(company_code)

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / "research_decision_sample.md"

    lines = [
        "# Research Decision Sample",
        "",
        f"- Company Code: {result['company_code']}",
        f"- Strategic Score: {result['strategic_score']:.2f}",
        f"- Catalyst Strength: {result['catalyst_strength']:.2f}",
        f"- Order Confirmation Level: {result['order_confirmation_level']:.2f}",
        f"- Research Conclusion: {result['research_conclusion']}",
        f"- Risk Summary: {result['risk_summary']}",
        "",
        "## Theme Exposure",
        f"{result['theme_exposure']}",
        "",
        "## Factor Scores",
        f"{result['factor_scores']}",
        "",
        "## Factor Input Summary",
        f"{result['factor_input_summary']}",
    ]
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"company_code={result['company_code']}")
    print(f"has_research_decision={all(key in result for key in ['theme_exposure', 'catalyst_strength', 'order_confirmation_level', 'strategic_score', 'research_conclusion', 'risk_summary'])}")
    print(f"report_written={output_path.as_posix()}")


if __name__ == "__main__":
    main()
