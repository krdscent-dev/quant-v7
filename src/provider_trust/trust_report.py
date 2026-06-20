"""Provider trust reporting helpers."""

from __future__ import annotations

from typing import Iterable

from .trust_contract import ProviderTrustScore


def format_trust_ranking(scores: Iterable[ProviderTrustScore]) -> str:
    lines = ["# Provider Trust Ranking", ""]
    for rank, score in enumerate(sorted(scores, key=lambda item: item.overall_score, reverse=True), start=1):
        lines.append(f"{rank}. {score.provider_name} {score.overall_score:.2f}")
    return "\n".join(lines).rstrip() + "\n"
