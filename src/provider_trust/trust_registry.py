"""Provider trust registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .trust_calculator import TrustCalculator
from .trust_contract import ProviderTrustScore


@dataclass(frozen=True)
class TrustProfile:
    provider_name: str
    total_fields: int
    missing_fields: int
    agreement_ratio: float
    days_since_update: int
    success_count: int
    total_count: int
    anomaly_count: int
    warning_count: int = 0
    last_updated: str | None = None


class TrustRegistry:
    """Maintain provider trust scores and snapshots."""

    def __init__(self) -> None:
        self.calculator = TrustCalculator()
        self._scores: dict[str, ProviderTrustScore] = {}
        self._profiles: dict[str, TrustProfile] = {}

    def register_profile(self, profile: TrustProfile) -> ProviderTrustScore:
        score = self.calculator.calculate_provider_trust(
            profile.provider_name,
            total_fields=profile.total_fields,
            missing_fields=profile.missing_fields,
            agreement_ratio=profile.agreement_ratio,
            days_since_update=profile.days_since_update,
            success_count=profile.success_count,
            total_count=profile.total_count,
            anomaly_count=profile.anomaly_count,
            warning_count=profile.warning_count,
            last_updated=profile.last_updated,
        )
        self._profiles[profile.provider_name] = profile
        self._scores[profile.provider_name] = score
        return score

    def set_score(self, score: ProviderTrustScore) -> None:
        self._scores[score.provider_name] = score

    def get_score(self, provider_name: str) -> ProviderTrustScore | None:
        return self._scores.get(provider_name)

    def list_scores(self) -> list[ProviderTrustScore]:
        return sorted(self._scores.values(), key=lambda item: item.overall_score, reverse=True)

    def load_default_profiles(self) -> None:
        for profile in (
            TrustProfile("tushare", 100, 5, 0.97, 1, 98, 100, 2),
            TrustProfile("akshare", 100, 8, 0.91, 2, 96, 100, 4),
            TrustProfile("mock", 20, 15, 0.50, 30, 60, 100, 10),
        ):
            self.register_profile(profile)

