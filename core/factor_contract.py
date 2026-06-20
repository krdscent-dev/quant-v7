"""Factor contract definitions.

Every factor in V8 must declare a contract so inputs, outputs, and
anti-double-counting notes stay explicit across the research stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FactorContract:
    factor_name: str
    factor_version: str
    input_fields: Sequence[str]
    output_fields: Sequence[str]
    score_range: tuple[float, float]
    description: str
    anti_double_counting_notes: str


DEFAULT_SCORE_RANGE: tuple[float, float] = (0.0, 100.0)


def build_contracts() -> dict[str, FactorContract]:
    """Return the canonical V8 factor contracts."""

    return {
        "tau_factor_score": FactorContract(
            factor_name="tau_factor_score",
            factor_version="v1",
            input_fields=(
                "tau_cycle_signal",
                "mate90_signal",
                "ascend_cluster_signal",
                "supernode_signal",
                "domestic_substitution_signal",
                "strategic_score",
            ),
            output_fields=("tau_factor_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Medium-term structural factor for industrial trend strength.",
            anti_double_counting_notes="Do not re-add order verification or theme exposure if they are already used in downstream factors.",
        ),
        "supernode_score": FactorContract(
            factor_name="supernode_score",
            factor_version="v1",
            input_fields=("ascend_exposure", "supernode_deployment", "eco_partners", "compatibility_progress"),
            output_fields=("supernode_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Huawei Ascend supernode ecosystem exposure.",
            anti_double_counting_notes="Avoid double counting with ascend_cluster signals and other Huawei ecosystem exposures.",
        ),
        "domestic_substitution_score": FactorContract(
            factor_name="domestic_substitution_score",
            factor_version="v1",
            input_fields=("localization_penetration", "import_substitution_progress", "customer_validation"),
            output_fields=("domestic_substitution_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Localization and supply-chain substitution strength.",
            anti_double_counting_notes="Do not duplicate scores already captured by order confirmation or advanced materials if they are the primary evidence source.",
        ),
        "advanced_packaging_score": FactorContract(
            factor_name="advanced_packaging_score",
            factor_version="v1",
            input_fields=("packaging_capacity_utilization", "chiplet_adoption_progress", "process_maturity"),
            output_fields=("advanced_packaging_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Advanced packaging and integration process readiness.",
            anti_double_counting_notes="Keep packaging and materials separated; packaging should not absorb raw material validation signals.",
        ),
        "advanced_material_score": FactorContract(
            factor_name="advanced_material_score",
            factor_version="v1",
            input_fields=("material_validation_stage", "customer_adoption_count", "production_line_investment"),
            output_fields=("advanced_material_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Advanced materials and industrial material validation.",
            anti_double_counting_notes="Avoid double counting with packaging or generic capex if the same evidence is used elsewhere.",
        ),
        "order_confirmation_score": FactorContract(
            factor_name="order_confirmation_score",
            factor_version="v1",
            input_fields=(
                "new_orders",
                "capacity_expansion",
                "management_guidance",
                "customer_verification",
                "revenue_acceleration",
            ),
            output_fields=("order_confirmation_score",),
            score_range=DEFAULT_SCORE_RANGE,
            description="Whether the story has moved into order and earnings validation.",
            anti_double_counting_notes="Order confirmation should be a separate validation layer and must not be repackaged as theme exposure.",
        ),
    }


def get_contract(name: str) -> FactorContract:
    contracts = build_contracts()
    if name not in contracts:
        raise KeyError(f"Unknown factor contract: {name}")
    return contracts[name]
