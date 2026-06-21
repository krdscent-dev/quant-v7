"""Safely apply approved repair patches in memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AppliedPatch:
    """A reversible in-memory patch."""

    patch_id: str
    target: str
    before: Any
    after: Any
    reversible: bool = True


class PatchExecutor:
    """Apply approved patches to an overlay state only."""

    def apply(
        self,
        patches: list[Mapping[str, Any]],
        state: Mapping[str, Any],
    ) -> tuple[dict[str, Any], list[AppliedPatch]]:
        overlay = dict(state)
        applied: list[AppliedPatch] = []
        for patch in patches:
            patch_id = str(patch.get("patch_id", ""))
            target = str(patch.get("target", ""))
            before = overlay.get(target)
            after = patch.get("proposed_value", patch.get("value", before))
            overlay[target] = after
            applied.append(
                AppliedPatch(
                    patch_id=patch_id,
                    target=target,
                    before=before,
                    after=after,
                )
            )
        return overlay, applied

    def rollback(
        self,
        applied_patches: list[AppliedPatch],
        state: Mapping[str, Any],
    ) -> dict[str, Any]:
        overlay = dict(state)
        for patch in reversed(applied_patches):
            overlay[patch.target] = patch.before
        return overlay

