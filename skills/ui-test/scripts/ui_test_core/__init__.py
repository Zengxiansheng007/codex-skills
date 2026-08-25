"""Deterministic UI-Test contract helpers."""

from .packet_validator import validate_packet
from .case_contracts import canonical_bytes, canonical_hash, lower_to_case_ir, validate_source_case, validate_semantics
from .registry_validator import (
    validate_contract_registry,
    validate_registry_and_baseline,
    validate_source_baseline,
)

__all__ = [
    "validate_packet",
    "validate_contract_registry",
    "validate_source_baseline",
    "validate_registry_and_baseline",
    "canonical_bytes",
    "canonical_hash",
    "lower_to_case_ir",
    "validate_source_case",
    "validate_semantics",
    "AggregateError",
    "render_product_aggregate",
]

from .product_aggregate import AggregateError, render_product_aggregate
