"""Provider governance and routing layer.

This module selects the appropriate data provider based on
`config/provider_priority.yaml`.
It does not compute factors, scores, or reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("PyYAML is required to use provider routing") from exc

from data_sources.akshare_provider import AkShareDataProvider
from data_sources.mock_provider import MockDataProvider
from data_sources.tushare_provider import TushareDataProvider
from data_sources.base import DataProvider


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    priority: int
    enabled: bool


class ProviderRouterError(RuntimeError):
    pass


class ProviderRouter:
    """Select a provider based on governance rules."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path(__file__).resolve().parents[1] / "config" / "provider_priority.yaml"
        self._config = self._load_config(self.config_path)
        self._providers = self._build_provider_map()

    def _load_config(self, path: Path) -> Mapping[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            raise ProviderRouterError("provider_priority.yaml must contain a mapping")
        return payload

    def _build_provider_map(self) -> dict[str, DataProvider]:
        return {
            "tushare": TushareDataProvider(),
            "akshare": AkShareDataProvider(),
            "mock": MockDataProvider(),
        }

    def _provider_settings(self) -> list[ProviderConfig]:
        providers = self._config.get("providers", {})
        settings: list[ProviderConfig] = []
        for name, config in providers.items():
            settings.append(
                ProviderConfig(
                    name=name,
                    priority=int(config.get("priority", 999)),
                    enabled=bool(config.get("enabled", False)),
                )
            )
        return sorted(settings, key=lambda item: item.priority)

    def get_provider(self, preferred_provider: str | None = None) -> DataProvider:
        """Return the best available provider.

        Routing order:
        1. Explicit preferred provider from field mapping
        2. Enabled providers sorted by configured priority
        3. Mock fallback
        """

        if preferred_provider:
            provider = self._providers.get(preferred_provider)
            provider_config = self._config.get("providers", {}).get(preferred_provider, {})
            if provider is not None and bool(provider_config.get("enabled", False)):
                return provider

        for setting in self._provider_settings():
            if not setting.enabled:
                continue
            provider = self._providers.get(setting.name)
            if provider is not None:
                return provider

        return self._providers["mock"]

    def get_provider_for_field(self, field_name: str) -> DataProvider:
        field_mapping = self._config.get("field_mapping", {})
        field_config = field_mapping.get(field_name, {})
        preferred_provider = field_config.get("preferred_provider")
        return self.get_provider(preferred_provider=preferred_provider)

    def get_conflict_strategy(self) -> str:
        conflict = self._config.get("conflict_resolution", {})
        return str(conflict.get("strategy", "priority_based"))

    def describe_routing(self) -> dict[str, Any]:
        """Return a lightweight routing snapshot for diagnostics."""

        return {
            "config_path": str(self.config_path),
            "strategy": self.get_conflict_strategy(),
            "providers": [
                {
                    "name": item.name,
                    "priority": item.priority,
                    "enabled": item.enabled,
                }
                for item in self._provider_settings()
            ],
        }

