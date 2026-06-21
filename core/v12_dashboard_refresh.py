"""Manual refresh mode for the V12 dashboard.

The dashboard is intentionally non-autonomous: it only updates when the
caller explicitly requests a refresh. A cached snapshot is kept on disk so the
last valid state can be returned if refresh generation fails.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.v12_dashboard_adapter import adapt_v12_dashboard
from core.v12_pipeline_lock import PIPELINE_LOCK_STATUS, pipeline_lock_error_state, validate_adapter_payload
from core.v12_report_normalizer import normalize_v12_report
from core.v12_research_evaluation_engine import run_v12_research_evaluation
from ui.v12_ui_layer import build_v12_ui


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compare_snapshots(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> dict[str, Any]:
    if not previous:
        return {
            "available": False,
            "delta": {},
            "summary": "No previous snapshot available.",
        }
    sections = ("market_state", "capital_state", "performance", "decision")
    delta: dict[str, Any] = {}
    for section in sections:
        prev_section = previous.get(section, {})
        curr_section = current.get(section, {})
        if not isinstance(prev_section, Mapping) or not isinstance(curr_section, Mapping):
            continue
        section_delta: dict[str, float] = {}
        for key in set(prev_section) & set(curr_section):
            prev_value = _safe_float(prev_section.get(key, 0.0), 0.0)
            curr_value = _safe_float(curr_section.get(key, 0.0), 0.0)
            section_delta[str(key)] = round(curr_value - prev_value, 4)
        delta[section] = section_delta
    return {
        "available": True,
        "delta": delta,
        "summary": "Snapshot comparison available.",
    }


@dataclass
class V12DashboardRefreshManager:
    """Generate dashboard snapshots only on manual request."""

    storage_dir: Path | str = Path("reports") / "v12_dashboard"

    def __post_init__(self) -> None:
        self.storage_dir = Path(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.storage_dir / "last_snapshot.json"

    def _load_last_snapshot(self) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        self.cache_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_snapshot(self, symbols: Sequence[str] | None = None) -> dict[str, Any]:
        raw_report = run_v12_research_evaluation(symbols=symbols)
        normalized = normalize_v12_report(raw_report)
        adapter_output = adapt_v12_dashboard(normalized)
        if not validate_adapter_payload(adapter_output):
            return pipeline_lock_error_state()
        ui_layout = build_v12_ui(adapter_output)
        return {
            "timestamp": _now_iso(),
            "refresh_mode": "MANUAL_ONLY",
            "status": "OK",
            "market_state": normalized["market_state"],
            "capital_state": normalized["capital_state"],
            "performance": normalized["performance"],
            "decision": normalized["decision"],
            "reasoning": normalized["explanation"],
            "system_health": normalized["system_health"],
            "dashboard_adapter": adapter_output,
            "ui_layout": ui_layout,
            "warnings": [],
            "source": "report_adapter_ui",
        }

    def refresh_analysis(self, symbols: Sequence[str] | None = None) -> dict[str, Any]:
        """Run the full V12 pipeline only when called explicitly."""

        previous = self._load_last_snapshot()
        try:
            snapshot = self._build_snapshot(symbols=symbols)
            if snapshot.get("status") == PIPELINE_LOCK_STATUS:
                snapshot["last_valid_snapshot"] = previous or {}
                snapshot["previous_snapshot_available"] = bool(previous)
                snapshot["refresh_mode"] = "MANUAL_ONLY"
                return snapshot
            snapshot["comparison"] = _compare_snapshots(previous, snapshot)
            snapshot["last_refresh_time"] = snapshot["timestamp"]
            snapshot["refresh_button"] = "REFRESH ANALYSIS"
            snapshot["previous_snapshot_available"] = bool(previous)
            self._save_snapshot(snapshot)
            return snapshot
        except Exception as exc:
            if previous:
                stale = dict(previous)
                stale["timestamp"] = _now_iso()
                stale["status"] = "STALE DATA"
                stale["warnings"] = list(stale.get("warnings", [])) + ["STALE DATA"]
                stale["refresh_mode"] = "MANUAL_ONLY"
                stale["refresh_button"] = "REFRESH ANALYSIS"
                stale["comparison"] = _compare_snapshots(previous, stale)
                stale["last_refresh_time"] = previous.get("last_refresh_time", previous.get("timestamp", stale["timestamp"]))
                stale["refresh_error"] = str(exc)
                stale["previous_snapshot_available"] = True
                return stale
            neutral = self._neutral_snapshot(error_message=str(exc))
            self._save_snapshot(neutral)
            return neutral

    def _neutral_snapshot(self, error_message: str | None = None) -> dict[str, Any]:
        normalized = normalize_v12_report({})
        adapter_output = adapt_v12_dashboard(normalized)
        timestamp = _now_iso()
        snapshot = {
            "timestamp": timestamp,
            "last_refresh_time": timestamp,
            "refresh_mode": "MANUAL_ONLY",
            "refresh_button": "REFRESH ANALYSIS",
            "status": "STALE DATA",
            "market_state": normalized["market_state"],
            "capital_state": normalized["capital_state"],
            "performance": normalized["performance"],
            "decision": normalized["decision"],
            "reasoning": normalized["explanation"],
            "system_health": normalized["system_health"],
            "dashboard_adapter": adapter_output,
            "ui_layout": build_v12_ui(adapter_output),
            "warnings": ["STALE DATA"],
            "refresh_error": error_message or "No cached snapshot available.",
            "previous_snapshot_available": False,
            "comparison": {
                "available": False,
                "delta": {},
                "summary": "No previous snapshot available.",
            },
            "source": "report_adapter_ui",
        }
        return snapshot


def refresh_dashboard(symbols: Sequence[str] | None = None) -> dict[str, Any]:
    """Manual trigger entrypoint for the V12 dashboard."""

    return V12DashboardRefreshManager().refresh_analysis(symbols=symbols)


def load_last_dashboard_snapshot() -> dict[str, Any] | None:
    """Load the last cached dashboard snapshot without refreshing."""

    manager = V12DashboardRefreshManager()
    return manager._load_last_snapshot()
