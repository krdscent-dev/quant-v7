"""V10 version control for model state snapshots and rollback."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json
import shutil


class V10VersionControl:
    """Create state snapshots and support rollback."""

    def __init__(self, state_path: Path, snapshot_dir: Path | None = None) -> None:
        self.state_path = state_path
        self.snapshot_dir = snapshot_dir or Path("reports/versions")

    def snapshot(self, label: str = "manual") -> dict[str, Any]:
        """Create a version snapshot of the current learning state."""

        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        version_id = f"v10_{timestamp}_{label}"
        snapshot_path = self.snapshot_dir / f"{version_id}.json"
        if self.state_path.exists():
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        else:
            payload = {}
        snapshot = {
            "version_id": version_id,
            "created_at": datetime.now().isoformat(),
            "label": label,
            "state_path": str(self.state_path),
            "state": payload,
        }
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "version_id": version_id,
            "snapshot_path": str(snapshot_path),
            "label": label,
            "state_present": bool(payload),
        }

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List available snapshots."""

        if not self.snapshot_dir.exists():
            return []
        snapshots = []
        for path in sorted(self.snapshot_dir.glob("v10_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                payload = {"version_id": path.stem}
            snapshots.append(
                {
                    "version_id": payload.get("version_id", path.stem),
                    "snapshot_path": str(path),
                    "created_at": payload.get("created_at", ""),
                    "label": payload.get("label", ""),
                }
            )
        return snapshots

    def rollback(self, version_id: str) -> dict[str, Any]:
        """Rollback the state file to a previous snapshot."""

        candidates = list(self.snapshot_dir.glob(f"{version_id}.json"))
        if not candidates:
            return {"rolled_back": False, "reason": "snapshot_not_found", "version_id": version_id}
        payload = json.loads(candidates[0].read_text(encoding="utf-8"))
        state = payload.get("state", {})
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"rolled_back": True, "version_id": version_id, "state_path": str(self.state_path)}

    def rollback_latest(self) -> dict[str, Any]:
        """Rollback to latest available snapshot."""

        snapshots = self.list_snapshots()
        if not snapshots:
            return {"rolled_back": False, "reason": "no_snapshots"}
        return self.rollback(str(snapshots[-1]["version_id"]))
