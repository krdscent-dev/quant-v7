"""V10.4 cognitive graph for causal reasoning.

The graph is intentionally lightweight: it models research causality as
directed relations and exposes chain inference plus bottleneck detection.
It does not replace scoring, alpha, or sector logic.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CausalInference:
    """Decision-ready causal context for one trigger."""

    trigger: str
    causal_chain: list[str]
    bottleneck_node: str
    chain_strength: str


class V10CognitiveGraph:
    """Directed causal graph used by V10.4 decision context."""

    BOTTLENECK_KEYWORDS = (
        "Supply Validation",
        "Order Confirmation",
        "Capacity Bottleneck",
        "Customer Validation",
        "Revenue Conversion",
    )

    def __init__(self) -> None:
        self._relations: dict[str, list[str]] = {}
        self._load_default_relations()

    def add_relation(self, cause: str, effect: str) -> None:
        """Add a directed cause -> effect relation."""

        cause_key = str(cause)
        effect_key = str(effect)
        self._relations.setdefault(cause_key, [])
        if effect_key not in self._relations[cause_key]:
            self._relations[cause_key].append(effect_key)

    def infer_chain(self, trigger: str) -> list[str]:
        """Infer the strongest available causal chain from a trigger."""

        trigger_key = str(trigger)
        if trigger_key not in self._relations:
            return []

        best_chain: list[str] = []
        queue: deque[list[str]] = deque([[trigger_key]])
        while queue:
            chain = queue.popleft()
            if len(chain) > len(best_chain):
                best_chain = chain
            for effect in self._relations.get(chain[-1], []):
                if effect not in chain:
                    queue.append([*chain, effect])
        return best_chain

    def bottleneck_detect(self, chain: Iterable[str]) -> str:
        """Return the first bottleneck node in a causal chain."""

        for node in chain:
            if any(keyword in node for keyword in self.BOTTLENECK_KEYWORDS):
                return str(node)
        return "NONE"

    def infer_for_context(self, sector: str, theme: str = "") -> CausalInference:
        """Build decision-ready causal inference from sector/theme context."""

        trigger = self._trigger_from_context(sector=sector, theme=theme)
        chain = self.infer_chain(trigger)
        bottleneck = self.bottleneck_detect(chain)
        if len(chain) >= 5:
            strength = "STRONG"
        elif len(chain) >= 3:
            strength = "PARTIAL"
        else:
            strength = "NONE"
        return CausalInference(
            trigger=trigger,
            causal_chain=chain,
            bottleneck_node=bottleneck,
            chain_strength=strength,
        )

    def _trigger_from_context(self, sector: str, theme: str = "") -> str:
        sector_key = str(sector)
        theme_key = str(theme)
        if sector_key in self._relations:
            return sector_key
        if theme_key in self._relations:
            return theme_key
        if "AI" in sector_key:
            return "AI Computing"
        if "Ascend" in sector_key or "Huawei" in sector_key:
            return "Huawei Ascend Ecosystem"
        if "Domestic" in sector_key:
            return "Domestic Substitution"
        if "Packaging" in sector_key:
            return "Advanced Packaging"
        if "Material" in sector_key:
            return "Advanced Materials"
        return sector_key or theme_key or "UNKNOWN"

    def _load_default_relations(self) -> None:
        defaults = {
            "AI Computing": [
                "AI CapEx Expansion",
            ],
            "AI CapEx Expansion": [
                "AI Server Demand",
                "Supply Validation",
            ],
            "AI Server Demand": [
                "Optical Module Demand",
                "Liquid Cooling Demand",
                "PCB Demand",
            ],
            "Supply Validation": [
                "Order Confirmation",
            ],
            "Order Confirmation": [
                "Revenue Conversion",
            ],
            "Huawei Ascend Ecosystem": [
                "Ascend Cluster Deployment",
            ],
            "Ascend Cluster Deployment": [
                "Supernode Architecture Validation",
                "Customer Validation",
            ],
            "Supernode Architecture Validation": [
                "Domestic Compute Substitution",
            ],
            "Customer Validation": [
                "Order Confirmation",
            ],
            "Domestic Substitution": [
                "Localization Policy Support",
            ],
            "Localization Policy Support": [
                "Customer Validation",
                "Domestic Supply Chain Replacement",
            ],
            "Domestic Supply Chain Replacement": [
                "Order Confirmation",
            ],
            "Advanced Packaging": [
                "Chiplet Demand",
            ],
            "Chiplet Demand": [
                "Packaging Capacity Bottleneck",
                "High-end Substrate Demand",
            ],
            "Packaging Capacity Bottleneck": [
                "Order Confirmation",
            ],
            "Advanced Materials": [
                "Thermal Density Upgrade",
            ],
            "Thermal Density Upgrade": [
                "Glass Substrate Validation",
                "Diamond Thermal Material Validation",
            ],
            "Glass Substrate Validation": [
                "Customer Validation",
            ],
            "Diamond Thermal Material Validation": [
                "Customer Validation",
            ],
        }
        for cause, effects in defaults.items():
            for effect in effects:
                self.add_relation(cause, effect)
