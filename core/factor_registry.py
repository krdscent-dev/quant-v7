"""Factor registry.

The registry is the canonical lookup table for research factors.
It prevents duplicated factor definitions from drifting across modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.factor_contract import FactorContract, build_contracts


@dataclass(frozen=True)
class RegisteredFactor:
    contract: FactorContract


class FactorRegistry:
    """Registry for all strategic research factors."""

    def __init__(self) -> None:
        self._contracts = build_contracts()

    def get(self, factor_name: str) -> FactorContract:
        if factor_name not in self._contracts:
            raise KeyError(f"Unknown factor: {factor_name}")
        return self._contracts[factor_name]

    def list_factor_names(self) -> list[str]:
        return list(self._contracts.keys())

    def list_contracts(self) -> list[FactorContract]:
        return list(self._contracts.values())

    def register(self, contract: FactorContract) -> None:
        self._contracts[contract.factor_name] = contract


DEFAULT_FACTOR_REGISTRY = FactorRegistry()
