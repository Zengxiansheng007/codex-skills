"""Synthetic YAML fixtures for RuntimeValueLoader tests."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from scripts.ui_test_core.jcs import sha256 as jcs_sha256  # Reuse the RFC 8785 wrapper for stable hashes.


ASSETS_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "assets" / "fixtures"  # Keep fixtures inside the candidate package.


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": "ui-test.runtime-value-index.v1",  # Pin the runtime-index contract version.
        "environment": "test",  # Synthetic environment only.
        "runtime_values": {
            "base_url": {"value": "https://synthetic-test.example.com", "source_type": "literal", "description": "Synthetic base URL"},
            "timeout_ms": {"value": 30000, "source_type": "literal", "description": "Synthetic timeout"},
        },
        "exploration_values": {
            "create_route": {"value": "/synthetic/create", "source_type": "literal", "status": "active", "run_id": "RUN-SYNTHETIC-001", "discovered_at": "2026-08-27T00:00:00Z", "scope": "synthetic/test", "evidence_ref": "evidence:synthetic-route", "description": "Synthetic route"}
        },
        "required_runtime_keys": ["base_url", "timeout_ms"],  # Require only synthetic non-sensitive values.
    }


def compute_manual_hash(document: dict[str, Any]) -> str:
    manual_partition = {
        "runtime_values": document.get("runtime_values", {}),  # Hash human-maintained runtime values.
        "required_runtime_keys": sorted(document.get("required_runtime_keys", [])),  # Normalize ordering.
    }
    return jcs_sha256(manual_partition)  # Return the stable manual partition digest.


def valid_document_with_hash() -> dict[str, Any]:
    document = _valid_document()  # Start from the valid synthetic baseline.
    document["manual_hash"] = compute_manual_hash(document)  # Bind the human partition to its expected hash.
    return document


def valid_fixture_path() -> Path:
    return ASSETS_FIXTURES_DIR / "runtime-value-index-valid.yaml"  # Use YAML to verify comments/parser behavior.


def load_valid_fixture() -> dict[str, Any]:
    import yaml  # type: ignore  # PyYAML is the project runtime dependency.
    return yaml.safe_load(valid_fixture_path().read_text(encoding="utf-8"))


def write_fixture(directory: Path, document: dict[str, Any], name: str = "runtime-value-index.yaml") -> Path:
    import yaml  # type: ignore  # Serialize synthetic fixtures as YAML.
    path = Path(directory) / name
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")  # Preserve a readable fixture.
    return path


def document_with_hash_drift() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a self-consistent document.
    document["runtime_values"]["timeout_ms"]["value"] = 60000  # Change a human value without changing its hash.
    return document


def document_missing_key() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["required_runtime_keys"].append("missing_value")  # Declare a key absent from runtime_values.
    document["manual_hash"] = compute_manual_hash(document)  # Keep the hash valid so the required-key gate is exercised.
    return document


def document_with_secret_in_runtime_values() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["runtime_values"]["leaked_token"] = {"value": "Bearer " + "x" * 30, "source_type": "literal", "description": "invalid synthetic leak"}  # Place a secret-like value in the wrong partition.
    document["manual_hash"] = compute_manual_hash(document)  # Keep the hash valid so sensitive scanning is exercised.
    return document


def document_with_unknown_version() -> dict[str, Any]:
    document = valid_document_with_hash()  # Start from a valid document.
    document["schema_version"] = "unknown.v2"  # Force the version gate.
    return document


def document_malformed_yaml() -> str:
    return "schema_version: ["  # Truncated YAML for parser failure coverage.


def document_env_ref_compatibility() -> dict[str, Any]:
    document = valid_document_with_hash()  # Legacy metadata is parsed separately from actual values.
    return copy.deepcopy(document)


def document_with_runtime_state_partition() -> dict[str, Any]:
    """A valid index that already carries a machine-maintained runtime_state partition."""
    document = valid_document_with_hash()  # Start from the self-consistent synthetic baseline.
    document["runtime_state"] = {
        "popup_announcement_version": {  # A sequence advanced once already (next hands out 2).
            "next_value": 2,
            "scope": "synthetic/test",
            "description": "Synthetic prior allocation",
            "allocations": [{"value": 1, "run_id": "RUN-PREVIOUS-001", "allocated_at": "2026-08-27T00:00:00Z", "evidence_ref": "evidence:synthetic-previous"}],  # Preserve complete append-only lineage.
        }
    }  # The runtime_state partition is mutable and excluded from the manual hash.
    return document


def document_with_malformed_runtime_state() -> dict[str, Any]:
    """A runtime_state entry with a non-positive next_value to exercise the validation gate."""
    document = valid_document_with_hash()  # Keep the manual partition valid for this gate.
    document["runtime_state"] = {
        "broken_sequence": {  # A non-positive counter must be rejected before any allocation.
            "next_value": 0,
            "scope": "synthetic/test",
            "description": "Broken synthetic sequence",
            "allocations": [],
        }
    }
    return document
