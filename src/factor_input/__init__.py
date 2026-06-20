"""Factor input compatibility package.

This package provides a stable contract for turning validated data into
factor-ready inputs. The existing research stack may continue to use
`core.data_mapping`, while newer code can depend on these contract
objects and builders directly.
"""

from .factor_confidence import ValidationStatus, confidence_from_validation_status
from .factor_input_builder import FactorInputBuilder
from .factor_input_contract import FactorInput, FactorInputContract

__all__ = [
    "FactorInput",
    "FactorInputBuilder",
    "FactorInputContract",
    "ValidationStatus",
    "confidence_from_validation_status",
]


