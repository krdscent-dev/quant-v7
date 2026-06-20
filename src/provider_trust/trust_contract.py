"""Provider trust contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderTrustScore:
    provider_name: str
    overall_score: float
    coverage_score: float
    consistency_score: float
    freshness_score: float
    stability_score: float
    anomaly_score: float
    warning_count: int
    last_updated: str

