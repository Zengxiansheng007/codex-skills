"""Governed YAML loader for UI-Test runtime values."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .jcs import sha256 as jcs_sha256  # Stable RFC 8785 hash for the manual partition.
from .secret_governance import scan_value  # Reuse the existing sensitive-value detector.


SKILL_ROOT = Path(__file__).resolve().parents[2]  # Resolve schemas relative to this Skill package.
SCHEMA_NAME = "runtime-value-index.schema.json"  # Keep one versioned runtime-index contract.
SCHEMA_VERSION = "ui-test.runtime-value-index.v1"  # Reject unknown index versions fail-closed.
class RuntimeValueError(ValueError):
    """Machine-readable fail-closed error without sensitive value echoing."""


def _load_schema() -> dict[str, Any]:
    return json.loads((SKILL_ROOT / "schemas" / SCHEMA_NAME).read_text(encoding="utf-8"))  # Load the local contract.


def _validate_structure(document: Any) -> list[dict[str, str]]:
    validator = Draft202012Validator(_load_schema())  # Use the project-standard JSON Schema validator.
    return [
        {"code": "E_RVI_SCHEMA_INVALID", "path": "/" + "/".join(str(part) for part in error.absolute_path), "message": error.message}
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))  # Keep diagnostics deterministic.
    ]


def compute_manual_hash(document: dict[str, Any]) -> str:
    """Hash only human-maintained runtime values and required keys."""
    manual_partition = {
        "runtime_values": document.get("runtime_values", {}),  # Human-maintained non-credential values.
        "required_runtime_keys": sorted(document.get("required_runtime_keys", [])),  # Normalize list ordering.
    }
    return jcs_sha256(manual_partition)  # Return the stable RFC 8785 digest.


def _parse_yaml(source: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeValueError("E_RVI_PARSER_MISSING: PyYAML is required for runtime-value-index.yaml") from exc
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))  # YAML comments remain non-semantic.
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeValueError(f"E_RVI_FILE_UNREADABLE: {exc.__class__.__name__}") from exc
    if not isinstance(document, dict):
        raise RuntimeValueError("E_RVI_ROOT_INVALID: root must be an object")  # Reject scalar and list documents.
    return document


def _scan_non_credential_values(document: dict[str, Any]) -> None:
    for section in ("runtime_values", "exploration_values", "runtime_state"):  # Credentials are permitted only in the private partition; runtime_state is mutable but non-credential.
        for key, entry in document.get(section, {}).items():
            if isinstance(entry, dict) and "value" in entry:
                findings = scan_value(entry["value"], f"$.{section}.{key}.value")  # Scan values without printing them.
                if findings:
                    raise RuntimeValueError("E_RVI_SECRET_DETECTED: secret-like value in non-credential partition")


def validate_runtime_state(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate machine-maintained runtime_state entries without touching the manual hash."""
    state = document.get("runtime_state", {})  # Default to empty when the partition is absent.
    if not isinstance(state, dict):
        raise RuntimeValueError("E_RVI_RUNTIME_STATE_INVALID: runtime_state must be an object")  # Reject scalar/list partitions.
    validated: dict[str, dict[str, Any]] = {}
    for key, entry in state.items():
        if not isinstance(key, str) or not key:
            raise RuntimeValueError("E_RVI_RUNTIME_STATE_KEY_INVALID")  # Reject empty/non-string sequence keys.
        if not isinstance(entry, dict):
            raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_ENTRY_INVALID: {key}")  # Reject scalar/list entries.
        next_value = entry.get("next_value")
        if not isinstance(next_value, int) or isinstance(next_value, bool) or next_value < 1:
            raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_NEXT_VALUE_INVALID: {key}")  # Reject non-positive or non-integer next values.
        for required_field in ("scope", "description"):
            if not isinstance(entry.get(required_field), str) or not entry[required_field].strip():
                raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_FIELD_INVALID: {key}.{required_field}")  # Reject missing or empty sequence metadata.
        allocations = entry.get("allocations")  # Read the append-only allocation ledger.
        if not isinstance(allocations, list):
            raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_ALLOCATIONS_INVALID: {key}")  # A mutable sequence always owns a list ledger.
        expected_values = list(range(1, len(allocations) + 1))  # Sequence values must remain contiguous from the governed first value.
        actual_values: list[int] = []  # Collect values only after every ledger row passes type checks.
        run_ids: list[str] = []  # Preserve run identities for duplicate detection.
        for index, allocation in enumerate(allocations):
            if not isinstance(allocation, dict):
                raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_ALLOCATION_INVALID: {key}.{index}")  # Reject scalar ledger rows.
            value = allocation.get("value")  # Resolve the allocated business version.
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_ALLOCATION_VALUE_INVALID: {key}.{index}")  # Reject invalid allocated values.
            for required_field in ("run_id", "allocated_at", "evidence_ref"):
                if not isinstance(allocation.get(required_field), str) or not allocation[required_field].strip():
                    raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_ALLOCATION_FIELD_INVALID: {key}.{index}.{required_field}")  # Require complete lineage.
            if scan_value(allocation["evidence_ref"], f"$.runtime_state.{key}.allocations.{index}.evidence_ref"):
                raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_SECRET_DETECTED: {key}")  # Keep ledger references free of credential material.
            actual_values.append(value)  # Record the validated sequence value.
            run_ids.append(allocation["run_id"])  # Record the validated run identity.
        if actual_values != expected_values or next_value != len(allocations) + 1:
            raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_SEQUENCE_DRIFT: {key}")  # Reject gaps, reordering or a counter/ledger mismatch.
        if len(run_ids) != len(set(run_ids)):
            raise RuntimeValueError(f"E_RVI_RUNTIME_STATE_RUN_DUPLICATE: {key}")  # One run may never own two sequence values.
        validated[key] = {
            "next_value": next_value,
            "scope": entry["scope"],
            "description": entry["description"],
            "allocations": [dict(allocation) for allocation in allocations],  # Return defensive copies of ledger rows.
        }  # Expose only the validated mutable fields.
    return validated  # Return a defensive shallow copy of the mutable state.


def load_runtime_value_index(path: str | Path) -> dict[str, Any]:
    """Load a YAML index and return a validated in-memory view."""
    source = Path(path).resolve()  # Resolve paths before applying the private-boundary check.
    if not source.is_file():
        raise RuntimeValueError("E_RVI_FILE_MISSING: runtime value index does not exist")
    document = _parse_yaml(source)  # Parse YAML so comments and human annotations are supported.
    if document.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeValueError(f"E_RVI_VERSION_UNKNOWN: expected {SCHEMA_VERSION}")
    schema_errors = _validate_structure(document)  # Apply the machine-readable structural contract.
    if schema_errors:
        first = schema_errors[0]
        raise RuntimeValueError(f"E_RVI_SCHEMA_INVALID: {first['path']} {first['message']}")
    if document.get("manual_hash") != compute_manual_hash(document):
        raise RuntimeValueError("E_RVI_MANUAL_HASH_DRIFT: human-maintained partition hash mismatch")
    runtime_state = validate_runtime_state(document)  # Validate mutable machine state without affecting the manual hash.
    _scan_non_credential_values(document)  # Prevent secrets from leaking into non-credential partitions.
    required_keys = sorted(document.get("required_runtime_keys", []))  # Normalize required-key ordering.
    missing = [key for key in required_keys if key not in document.get("runtime_values", {})]
    if missing:
        raise RuntimeValueError(f"E_RVI_REQUIRED_KEY_MISSING: {','.join(missing)}")
    return {
        "schema_version": SCHEMA_VERSION,  # Expose only validated fields.
        "environment": document.get("environment", "test"),  # Preserve the declared execution environment.
        "runtime_values": dict(document.get("runtime_values", {})),  # Return a defensive shallow copy.
        "exploration_values": dict(document.get("exploration_values", {})),  # Exploration values are separate.
        "runtime_state": runtime_state,  # Expose validated mutable sequence state; never part of the manual hash.
        "required_runtime_keys": required_keys,  # Preserve the normalized required-key list.
        "manual_hash": compute_manual_hash(document),  # Return only the verified digest.
        "source_path": str(source),  # Record location without recording values.
        "raw_values_in_errors": False,  # Promise that errors never contain raw values.
    }


def get_runtime_value(loaded: dict[str, Any], key: str) -> Any:
    values = loaded.get("runtime_values", {})  # Select the non-credential partition.
    if key not in values:
        raise RuntimeValueError(f"E_RVI_KEY_NOT_FOUND: {key}")
    entry = values[key]
    if not isinstance(entry, dict) or "value" not in entry:
        raise RuntimeValueError(f"E_RVI_ENTRY_INVALID: {key}")
    return entry["value"]  # Return the requested value only to the in-memory caller.


def get_credential_value(loaded: dict[str, Any], key: str) -> str:
    credentials = loaded.get("credentials", {})  # Select the private credential partition when the caller merges indices.
    if key not in credentials:
        raise RuntimeValueError(f"E_RVI_CREDENTIAL_KEY_NOT_FOUND: {key}")
    entry = credentials[key]
    if not isinstance(entry, dict) or not isinstance(entry.get("value"), str):
        raise RuntimeValueError(f"E_RVI_CREDENTIAL_ENTRY_INVALID: {key}")
    return entry["value"]  # Return plaintext only inside the caller's process memory.


def get_exploration_value(loaded: dict[str, Any], key: str) -> Any:
    values = loaded.get("exploration_values", {})  # Exploration values never contribute to manual_hash.
    if key not in values:
        raise RuntimeValueError(f"E_RVI_EXPLORATION_KEY_NOT_FOUND: {key}")
    entry = values[key]
    if not isinstance(entry, dict) or "value" not in entry:
        raise RuntimeValueError(f"E_RVI_EXPLORATION_ENTRY_INVALID: {key}")
    return entry["value"]  # Return the validated exploration value.


def parse_env_ref(env_ref_value: Any) -> dict[str, Any]:
    """Parse deprecated metadata without reading the process environment."""
    if not isinstance(env_ref_value, dict) or not isinstance(env_ref_value.get("env_ref"), str):
        return {"ok": False, "code": "E_ENV_REF_INVALID", "env_ref": None}  # Reject malformed legacy metadata.
    return {"ok": True, "code": "OK", "env_ref": env_ref_value["env_ref"]}  # Return the name, never an OS value.


def resolve_value_ref(loaded: dict[str, Any], reference: str) -> Any:
    """Resolve new value/credential/exploration references and deprecated env metadata."""
    if not isinstance(reference, str) or ":" not in reference:
        raise RuntimeValueError("E_RVI_REFERENCE_INVALID: reference must include a supported prefix")
    prefix, key = reference.split(":", 1)  # Split only the governed prefix from the stable key.
    if prefix == "value":
        return get_runtime_value(loaded, key)  # Resolve non-sensitive runtime values.
    if prefix == "credential":
        return get_credential_value(loaded, key)  # Resolve credentials only from an explicitly merged private index.
    if prefix == "exploration":
        entry = loaded.get("exploration_values", {}).get(key)
        if not isinstance(entry, dict) or entry.get("status") != "active":
            raise RuntimeValueError(f"E_RVI_EXPLORATION_NOT_ACTIVE: {key}")
        return get_exploration_value(loaded, key)  # Consume only active exploration values.
    if prefix == "env":
        if key in loaded.get("runtime_values", {}):
            return get_runtime_value(loaded, key)  # Legacy env metadata resolves through the file, not os.environ.
        if key in loaded.get("credentials", {}):
            return get_credential_value(loaded, key)  # Legacy credential names resolve through the private file.
        raise RuntimeValueError(f"E_ENV_REF_UNRESOLVED: {key}")
    raise RuntimeValueError(f"E_RVI_REFERENCE_PREFIX_UNKNOWN: {prefix}")


def external_env_conflict(loaded: dict[str, Any], environ: dict[str, str] | None = None) -> list[str]:
    """Report conflicts without using external values as a source of truth."""
    current_env = os.environ if environ is None else environ  # Read only for conflict detection when explicitly requested.
    conflicts: list[str] = []
    for key, entry in loaded.get("runtime_values", {}).items():
        if isinstance(entry, dict) and key in current_env and current_env[key] != str(entry.get("value")):
            conflicts.append(key)  # Report variable names only, never conflicting values.
    return sorted(conflicts)  # Stable issue ordering for machine-readable callers.
