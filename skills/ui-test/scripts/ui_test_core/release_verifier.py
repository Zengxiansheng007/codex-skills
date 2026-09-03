"""Manifest-driven v2 release integrity and current-input synchronization evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .path_utils import io_path
from .strict_json import load_strict_json


IDENTITY_FIELDS = (
    "case_id",
    "branch_id",
    "source_hash",
    "test_data_hash",
    "parameter_manifest_hash",
    "runtime_material_digest",
    "dependency_digest",
    "page_module_registry_digest",
    "module_coverage_digest",
    "config_fingerprint",
    "build_fingerprint",
)


def _issue(code: str, path: str, detail: str | None = None) -> dict[str, str]:
    item = {"code": code, "path": path}
    if detail:
        item["detail"] = detail
    return item


def _is_contained(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _load_artifact(path: Path) -> Any:
    if path.suffix in {".md", ".py"}:
        return path.read_text(encoding="utf-8")
    return load_strict_json(path)


def verify_release(
    release_dir: str | Path,
    *,
    active_pointer: Mapping[str, Any] | None = None,
    current_identity: Mapping[str, Any] | None = None,
    migration_eligible: bool = True,
    environment_ready: bool = True,
    authorization_ready: bool = True,
    guard_ready: bool = True,
) -> dict[str, Any]:
    """Evaluate independent release-integrity, input-sync and execution-gate axes."""
    release = io_path(release_dir)
    manifest_path = release / "manifest.json"
    issues: list[dict[str, str]] = []
    if not manifest_path.is_file():
        return {
            "schema_version": "ui-test.sync-state.v2",
            "case_id": None,
            "branch_id": None,
            "build_fingerprint": None,
            "release_integrity": "missing",
            "input_sync": "unverifiable",
            "execution_gate": "blocked",
            "issues": [_issue("E_RELEASE_MANIFEST_MISSING", "manifest.json")],
        }
    try:
        manifest = load_strict_json(manifest_path)
    except ValueError:
        manifest = {}
        issues.append(_issue("E_RELEASE_MANIFEST_INVALID_JSON", "manifest.json"))
    schema_issues = validate_document(manifest, "case-manifest-v2.schema.json")
    if schema_issues:
        issues.append(_issue("E_RELEASE_MANIFEST_SCHEMA", "manifest.json"))
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest, dict) else {}
    expected_names = set(artifacts) | {"manifest.json"}
    actual_names = {path.relative_to(release).as_posix() for path in release.rglob("*") if path.is_file()}
    for name in sorted(expected_names - actual_names):
        issues.append(_issue("E_RELEASE_ARTIFACT_MISSING", name))
    for name in sorted(actual_names - expected_names):
        issues.append(_issue("E_RELEASE_ARTIFACT_UNDECLARED", name))
    for name, expected_hash in sorted(artifacts.items()):
        path = release / Path(name)
        if not _is_contained(path, release):
            issues.append(_issue("E_RELEASE_ARTIFACT_PATH_ESCAPE", name))
            continue
        if not path.is_file():
            continue
        try:
            if canonical_hash(_load_artifact(path)) != expected_hash:
                issues.append(_issue("E_RELEASE_ARTIFACT_HASH_MISMATCH", name))
        except (OSError, UnicodeError, ValueError):
            issues.append(_issue("E_RELEASE_ARTIFACT_UNREADABLE", name))
    receipt_path = release / "compile-receipt.json"
    if receipt_path.is_file():
        try:
            receipt = load_strict_json(receipt_path)
            if validate_document(receipt, "compile-receipt-v2.schema.json"):
                issues.append(_issue("E_RELEASE_RECEIPT_SCHEMA", "compile-receipt.json"))
            elif any(receipt.get(field) != manifest.get(field) for field in IDENTITY_FIELDS):
                issues.append(_issue("E_RELEASE_RECEIPT_IDENTITY_MISMATCH", "compile-receipt.json"))
        except ValueError:
            issues.append(_issue("E_RELEASE_RECEIPT_INVALID_JSON", "compile-receipt.json"))
    else:
        issues.append(_issue("E_RELEASE_RECEIPT_MISSING", "compile-receipt.json"))
    if active_pointer is not None:
        if validate_document(dict(active_pointer), "active-pointer-v2.schema.json"):
            issues.append(_issue("E_ACTIVE_POINTER_SCHEMA", "active.json"))
        elif any(active_pointer.get(field) != manifest.get(field) for field in ("case_id", "branch_id", "build_fingerprint")):
            issues.append(_issue("E_ACTIVE_POINTER_IDENTITY_MISMATCH", "active.json"))
    integrity_codes = {item["code"] for item in issues}
    release_integrity = "valid"
    if integrity_codes:
        release_integrity = "manual_drift" if integrity_codes <= {
            "E_RELEASE_ARTIFACT_MISSING", "E_RELEASE_ARTIFACT_UNDECLARED", "E_RELEASE_ARTIFACT_HASH_MISMATCH"
        } else "invalid"
    if current_identity is None or release_integrity != "valid":
        input_sync = "unverifiable"
    else:
        drifted = [field for field in IDENTITY_FIELDS if field != "build_fingerprint" and current_identity.get(field) != manifest.get(field)]
        input_sync = "out_of_sync" if drifted else "in_sync"
        issues.extend(_issue("E_CURRENT_INPUT_DRIFT", field) for field in drifted)
    gates = {
        "migration": migration_eligible,
        "environment": environment_ready,
        "authorization": authorization_ready,
        "guard": guard_ready,
    }
    for name, ready in gates.items():
        if not ready:
            issues.append(_issue(f"E_EXECUTION_{name.upper()}_BLOCKED", name))
    execution_gate = "ready" if release_integrity == "valid" and input_sync == "in_sync" and all(gates.values()) else "blocked"
    return {
        "schema_version": "ui-test.sync-state.v2",
        "case_id": manifest.get("case_id"),
        "branch_id": manifest.get("branch_id"),
        "build_fingerprint": manifest.get("build_fingerprint"),
        "release_integrity": release_integrity,
        "input_sync": input_sync,
        "execution_gate": execution_gate,
        "issues": sorted(issues, key=lambda item: (item["code"], item["path"])),
    }
