"""Latency consistency checks for V12.9."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class LatencyReport:
    """Latency and synchronization status."""

    status: str
    synchronization_status: str
    latest_market_age_minutes: float
    decision_lag_minutes: float
    execution_lag_minutes: float
    warnings: list[str]


class LatencyController:
    """Ensure the latest market data is synchronized."""

    def assess(
        self,
        market_timestamp: str | datetime,
        decision_timestamp: str | datetime,
        execution_timestamp: str | datetime,
    ) -> LatencyReport:
        market_dt = self._as_datetime(market_timestamp)
        decision_dt = self._as_datetime(decision_timestamp)
        execution_dt = self._as_datetime(execution_timestamp)

        decision_lag = abs((decision_dt - market_dt).total_seconds()) / 60.0
        execution_lag = abs((execution_dt - decision_dt).total_seconds()) / 60.0
        latest_age = max(decision_lag, execution_lag)
        sync_delta = abs((execution_dt - market_dt).total_seconds()) / 60.0

        if sync_delta <= 1.0:
            status = "LOW_LATENCY"
            sync_status = "SYNCED"
        elif sync_delta <= 5.0:
            status = "MEDIUM_LATENCY"
            sync_status = "NEAR_SYNC"
        else:
            status = "HIGH_LATENCY"
            sync_status = "DESYNCED"

        warnings: list[str] = []
        if sync_delta > 5.0:
            warnings.append("market_data_desynchronized")
        if decision_lag > 5.0:
            warnings.append("decision_lag_high")
        if execution_lag > 5.0:
            warnings.append("execution_lag_high")

        return LatencyReport(
            status=status,
            synchronization_status=sync_status,
            latest_market_age_minutes=round(latest_age, 2),
            decision_lag_minutes=round(decision_lag, 2),
            execution_lag_minutes=round(execution_lag, 2),
            warnings=warnings,
        )

    @staticmethod
    def _as_datetime(value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

