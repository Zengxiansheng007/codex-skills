"""Synthetic YAML fixtures for CredentialIndexLoader tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.ui_test_core.jcs import sha256 as jcs_sha256  # Reuse the RFC 8785 wrapper for stable hashes.


ASSETS_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "assets" / "fixtures"  # Keep fixtures inside the candidate package.


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": "ui-test.credential-index.v1",  # Pin the credential-index contract version.
        "environment": "test",  # Synthetic environment only.
        "credentials": {
            "BOPS_ACCOUNT_USER": {"value": "synthetic-user", "description": "Synthetic account user", "sensitive": True},
            "BOPS_ACCOUNT_PASSWORD": {"value": "synthetic-password", "description": "Synthetic account password", "sensitive": True},
        },
        "required_credential_keys": ["BOPS_ACCOUNT_USER", "BOPS_ACCOUNT_PASSWORD"],  # Require the full account pair.
    }


def compute_manual_hash(document: dict[str, Any]) -> str:
    manual_partition = {
        "credentials": document.get("credentials", {}),  # Hash human-maintained credential values.
        "required_credential_keys": sorted(document.get("required_credential_keys", [])),  # Normalize ordering.
    }
    return jcs_sha256(manual_partition)  # Return the stable manual partition digest.


def valid_document_with_hash() -> dict[str, Any]:
    document = _valid_document()  # Start from the valid synthetic baseline.
    document["manual_hash"] = compute_manual_hash(document)  # Bind the human partition to its expected hash.
    return document


def valid_fixture_path() -> Path:
    return ASSETS_FIXTURES_DIR / "credential-index-valid.yaml"  # Use YAML to verify comments/parser behavior.


def load_valid_fixture() -> dict[str, Any]:
    import yaml  # type: ignore  # PyYAML is the project runtime dependency.
    return yaml.safe_load(valid_fixture_path().read_text(encoding="utf-8"))


def write_fixture(directory: Path, document: dict[str, Any], name: str = "credential-index.yaml") -> Path:
    import yaml  # type: ignore  # Serialize synthetic fixtures as YAML.
    path = Path(directory) / name
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")  # Preserve a readable fixture.
    return path


def document_with_hash_drift() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a self-consistent document.
    document["credentials"]["BOPS_ACCOUNT_PASSWORD"]["value"] = "synthetic-password-drift"  # Change a human value without changing its hash.
    return document


def document_missing_key() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["required_credential_keys"].append("BOPS_EXTRA_KEY")  # Declare a key absent from credentials.
    document["manual_hash"] = compute_manual_hash(document)  # Keep the hash valid so the required-key gate is exercised.
    return document


def document_with_unknown_version() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["schema_version"] = "unknown.v2"  # Force the version gate.
    return document


def document_malformed_yaml() -> str:
    return "schema_version: ["  # Truncated YAML for parser failure coverage.


def document_with_secret_in_runtime_values() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["credentials"]["BOPS_ACCOUNT_USER"]["value"] = "Bearer " + "x" * 20  # Use a synthetic secret-shaped credential value.
    document["manual_hash"] = compute_manual_hash(document)  # Keep the hash valid for structural fixture use.
    return document
