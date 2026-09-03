"""Hash-bind resolved Test Data, canonical RunResult and evidence/report projections."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .case_contracts import canonical_hash, validate_document
from .path_utils import io_path
from .strict_json import load_strict_json


class RunEvidenceLinkError(ValueError):
    """运行结果链接错误。"""


def _relative_contained(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise RunEvidenceLinkError("E_RUN_ARTIFACT_PATH_ESCAPE") from exc


def _verified_snapshot(snapshot_path: Path) -> dict[str, Any]:
    snapshot = load_strict_json(snapshot_path)
    if validate_document(snapshot, "resolved-test-data.schema.json"):
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_SCHEMA_INVALID")
    supplied = snapshot["snapshot_hash"]
    computed = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    if supplied != computed:
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_HASH_MISMATCH")
    return snapshot


def bind_run_result_v3(base_run_result: dict[str, Any], *, run_root: str | Path, snapshot_path: str | Path) -> dict[str, Any]:
    """Create a new v3 result; never mutate a historical RunResult object."""
    root = io_path(run_root)
    path = io_path(snapshot_path)
    snapshot = _verified_snapshot(path)
    if snapshot["run_id"] != base_run_result.get("run_id") or snapshot["case_id"] != base_run_result.get("case_id") or snapshot["branch_id"] != base_run_result.get("branch_id"):
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_IDENTITY_MISMATCH")
    result = copy.deepcopy(base_run_result)
    result["schema_version"] = "ui-test.run-result.v3"
    result["resolved_test_data_ref"] = _relative_contained(path, root)
    result["resolved_test_data_hash"] = snapshot["snapshot_hash"]
    result.pop("run_result_hash", None)
    result["run_result_hash"] = canonical_hash(result)
    if validate_document(result, "run-result-v3.schema.json"):
        raise RunEvidenceLinkError("E_RUN_RESULT_V3_SCHEMA_INVALID")
    return result


def build_evidence_index_v2(run_result: dict[str, Any], *, run_result_ref: str) -> dict[str, Any]:
    if validate_document(run_result, "run-result-v3.schema.json"):
        raise RunEvidenceLinkError("E_RUN_RESULT_V3_SCHEMA_INVALID")
    return {
        "schema_version": "ui-test.evidence-index.v2",
        "run_id": run_result["run_id"],
        "case_id": run_result["case_id"],
        "branch_id": run_result["branch_id"],
        "run_result_ref": run_result_ref,
        "run_result_hash": run_result["run_result_hash"],
        "resolved_test_data_ref": run_result["resolved_test_data_ref"],
        "resolved_test_data_hash": run_result["resolved_test_data_hash"],
        "evidence_refs": copy.deepcopy(run_result.get("evidence_refs", [])),
        "read_only_projection": True,
    }


def verify_run_evidence_links(run_result: dict[str, Any], evidence_index: dict[str, Any], *, run_root: str | Path) -> list[str]:
    issues: list[str] = []
    if validate_document(run_result, "run-result-v3.schema.json"):
        issues.append("E_RUN_RESULT_V3_SCHEMA_INVALID")
    expected_run_hash = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
    if run_result.get("run_result_hash") != expected_run_hash:
        issues.append("E_RUN_RESULT_HASH_MISMATCH")
    if validate_document(evidence_index, "evidence-index-v2.schema.json"):
        issues.append("E_EVIDENCE_INDEX_V2_SCHEMA_INVALID")
    for field in ("run_id", "case_id", "branch_id", "run_result_hash", "resolved_test_data_ref", "resolved_test_data_hash"):
        if evidence_index.get(field) != run_result.get(field):
            issues.append(f"E_RUN_EVIDENCE_LINK_MISMATCH:{field}")
    snapshot_path = io_path(run_root) / str(run_result.get("resolved_test_data_ref", ""))
    try:
        snapshot = _verified_snapshot(snapshot_path)
        if snapshot["snapshot_hash"] != run_result.get("resolved_test_data_hash"):
            issues.append("E_RUN_SNAPSHOT_LINK_HASH_MISMATCH")
    except (OSError, ValueError):
        issues.append("E_RUN_SNAPSHOT_UNREADABLE")
    return sorted(set(issues))
