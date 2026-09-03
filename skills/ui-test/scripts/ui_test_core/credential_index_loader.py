"""Governed YAML loader for UI-Test credential values."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .jcs import sha256 as jcs_sha256  # Stable RFC 8785 hash for the manual partition.


SKILL_ROOT = Path(__file__).resolve().parents[2]  # Resolve schemas relative to this Skill package.
SCHEMA_NAME = "credential-index.schema.json"  # Keep one versioned credential-index contract.
SCHEMA_VERSION = "ui-test.credential-index.v1"  # Reject unknown index versions fail-closed.
PRIVATE_RUNTIME_ROOT = Path(r"D:\UI-Test\_private\runtime-values")  # Credentials are private local values.


class CredentialIndexError(ValueError):
    """Machine-readable fail-closed error without sensitive value echoing."""


def _load_schema() -> dict[str, Any]:
    return json.loads((SKILL_ROOT / "schemas" / SCHEMA_NAME).read_text(encoding="utf-8"))  # Load the local contract.


def _validate_structure(document: Any) -> list[dict[str, str]]:
    validator = Draft202012Validator(_load_schema())  # Use the project-standard JSON Schema validator.
    return [
        {"code": "E_CRI_SCHEMA_INVALID", "path": "/" + "/".join(str(part) for part in error.absolute_path), "message": error.message}
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))  # Keep diagnostics deterministic.
    ]


def compute_manual_hash(document: dict[str, Any]) -> str:
    """Hash only human-maintained credential values and required keys."""
    manual_partition = {
        "credentials": document.get("credentials", {}),  # Human-maintained credential values are included in the hash.
        "required_credential_keys": sorted(document.get("required_credential_keys", [])),  # Normalize list ordering.
    }
    return jcs_sha256(manual_partition)  # Return the stable RFC 8785 digest.


def _is_private_runtime_path(source: Path) -> bool:
    try:
        source.relative_to(PRIVATE_RUNTIME_ROOT)  # Credentials are allowed only below the private D-drive root.
        return True
    except ValueError:
        return False


def _parse_yaml(source: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise CredentialIndexError("E_CRI_PARSER_MISSING: PyYAML is required for credential-index.yaml") from exc
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))  # YAML comments remain non-semantic.
    except (OSError, yaml.YAMLError) as exc:
        raise CredentialIndexError(f"E_CRI_FILE_UNREADABLE: {exc.__class__.__name__}") from exc
    if not isinstance(document, dict):
        raise CredentialIndexError("E_CRI_ROOT_INVALID: root must be an object")  # Reject scalar and list documents.
    return document


def load_credential_index(path: str | Path) -> dict[str, Any]:
    """Load a YAML credential index and return a validated in-memory view."""
    source = Path(path).resolve()  # Resolve paths before applying the private-boundary check.
    if not source.is_file():
        raise CredentialIndexError("E_CRI_FILE_MISSING: credential index does not exist")
    if not _is_private_runtime_path(source):
        raise CredentialIndexError("E_CRI_PATH_FORBIDDEN: credential values require a private runtime index path")
    document = _parse_yaml(source)  # Parse YAML so comments and human annotations are supported.
    if document.get("schema_version") != SCHEMA_VERSION:
        raise CredentialIndexError(f"E_CRI_VERSION_UNKNOWN: expected {SCHEMA_VERSION}")
    schema_errors = _validate_structure(document)  # Apply the machine-readable structural contract.
    if schema_errors:
        first = schema_errors[0]
        raise CredentialIndexError(f"E_CRI_SCHEMA_INVALID: {first['path']} {first['message']}")
    if document.get("manual_hash") != compute_manual_hash(document):
        raise CredentialIndexError("E_CRI_MANUAL_HASH_DRIFT: human-maintained partition hash mismatch")
    required_keys = sorted(document.get("required_credential_keys", []))  # Normalize required-key ordering.
    missing = [key for key in required_keys if key not in document.get("credentials", {})]
    if missing:
        raise CredentialIndexError(f"E_CRI_REQUIRED_KEY_MISSING: {','.join(missing)}")
    return {
        "schema_version": SCHEMA_VERSION,  # Expose only validated fields.
        "environment": document.get("environment", "test"),  # Preserve the declared execution environment.
        "credentials": dict(document.get("credentials", {})),  # Credential values remain in process memory only.
        "required_credential_keys": required_keys,  # Preserve the normalized required-key list.
        "manual_hash": compute_manual_hash(document),  # Return only the verified digest.
        "source_path": str(source),  # Record location without recording values.
    }


def get_credential_value(loaded: dict[str, Any], key: str) -> str:
    credentials = loaded.get("credentials", {})  # Select the private credential partition.
    if key not in credentials:
        raise CredentialIndexError(f"E_CRI_KEY_NOT_FOUND: {key}")
    entry = credentials[key]
    if not isinstance(entry, dict) or not isinstance(entry.get("value"), str):
        raise CredentialIndexError(f"E_CRI_ENTRY_INVALID: {key}")
    return entry["value"]  # Return plaintext only inside the caller's process memory.
