"""Deterministic UI-Test contract helpers."""

from .packet_validator import validate_packet
from .case_contracts import canonical_bytes, canonical_hash, lower_to_case_ir, validate_source_case, validate_semantics
from .registry_validator import (
    validate_contract_registry,
    validate_registry_and_baseline,
    validate_source_baseline,
)
from .runtime_value_loader import (
    RuntimeValueError,
    get_credential_value,
    get_exploration_value,
    get_runtime_value,
    load_runtime_value_index,
    parse_env_ref,
    resolve_value_ref,
)
from .credential_index_loader import CredentialIndexError, load_credential_index
from .project_config import credential_index_path, load_project_runtime_values, runtime_index_path
from .runtime_value_writer import RuntimeValueWriteError, append_exploration_value, promote_exploration_value
from .runtime_state_allocator import RuntimeStateError, allocate_runtime_sequence, initialize_runtime_sequence

# pytest_runtime_plugin 不在此导入；由根 conftest 通过 pytest_plugins 显式加载。

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
    "render_product_aggregate_v2",
    "RuntimeValueError",
    "CredentialIndexError",
    "load_runtime_value_index",
    "load_credential_index",
    "get_runtime_value",
    "get_credential_value",
    "get_exploration_value",
    "parse_env_ref",
    "resolve_value_ref",
    "load_project_runtime_values",
    "runtime_index_path",
    "credential_index_path",
    "RuntimeValueWriteError",
    "append_exploration_value",
    "promote_exploration_value",
    "RuntimeStateError",
    "allocate_runtime_sequence",
    "initialize_runtime_sequence",
]

from .product_aggregate import AggregateError, render_product_aggregate, render_product_aggregate_v2
