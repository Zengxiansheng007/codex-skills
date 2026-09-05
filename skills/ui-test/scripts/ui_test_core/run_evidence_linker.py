"""Hash-bind resolved Test Data, canonical RunResult and evidence/report projections。

ST-008：新增RunResultV4 builder/verifier，保持V3函数和历史Schema不变。
ST-013：新增RunResultV5 builder/verifier；V5不再自证PyCharm或人工验收状态。
V4包含resolved snapshot ref/hash、ExecutionContext/Attempt/Approval ref/hash、
write_state、观测submit_count、六层状态和自身hash。
evidence-index-v2可向后兼容V4但必须验证V4链接。
禁止把v3结果升级改写。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .path_utils import io_path
from .strict_json import load_strict_json


class RunEvidenceLinkError(ValueError):
    """运行结果链接错误。"""


def _validate_relative_ref(value: str, *, field: str) -> None:
    """拒绝绝对路径、反斜杠和父目录逃逸。"""
    if not isinstance(value, str):
        raise RunEvidenceLinkError(f"E_RUN_RESULT_REF_ESCAPE:{field}")
    path = Path(value)
    if not value or path.is_absolute() or "\\" in value or ".." in path.parts or (len(value) > 1 and value[1] == ":"):
        raise RunEvidenceLinkError(f"E_RUN_RESULT_REF_ESCAPE:{field}")


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


def relative_contained(path: Path, root: Path) -> str:
    """项目adapter可复用的公开相对引用校验。"""
    return _relative_contained(path, root)


def verified_snapshot(snapshot_path: Path) -> dict[str, Any]:
    """项目adapter可复用的公开resolved snapshot校验。"""
    return _verified_snapshot(snapshot_path)


def bind_run_result_v3(
    base_run_result: dict[str, Any],
    *,
    run_root: str | Path,
    snapshot_path: str | Path,
    legacy_fixture: bool = False,
) -> dict[str, Any]:
    """仅为历史reader测试构造V3 fixture；正式调用默认拒绝。"""
    if legacy_fixture is not True:
        raise RunEvidenceLinkError("E_RUN_RESULT_V3_HISTORICAL_READ_ONLY")
    root = io_path(run_root)
    path = io_path(snapshot_path)
    snapshot_ref = _relative_contained(path, root)  # 包含性校验必须先于任何文件读取。
    snapshot = _verified_snapshot(path)
    if snapshot["run_id"] != base_run_result.get("run_id") or snapshot["case_id"] != base_run_result.get("case_id") or snapshot["branch_id"] != base_run_result.get("branch_id"):
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_IDENTITY_MISMATCH")
    result = copy.deepcopy(base_run_result)
    result["schema_version"] = "ui-test.run-result.v3"
    result["resolved_test_data_ref"] = snapshot_ref
    result["resolved_test_data_hash"] = snapshot["snapshot_hash"]
    result.pop("run_result_hash", None)
    result["run_result_hash"] = canonical_hash(result)
    if validate_document(result, "run-result-v3.schema.json"):
        raise RunEvidenceLinkError("E_RUN_RESULT_V3_SCHEMA_INVALID")
    return result


def build_evidence_index_v2(run_result: dict[str, Any], *, run_result_ref: str) -> dict[str, Any]:
    """evidence-index-v2兼容V3/V4/V5，并按各自Schema验证。"""
    # 按版本验证结果，不把旧结果隐式升级为新版本。
    schema_version = run_result.get("schema_version", "")
    if schema_version == "ui-test.run-result.v5":
        if validate_document(run_result, "run-result-v5.schema.json"):
            raise RunEvidenceLinkError("E_RUN_RESULT_V5_SCHEMA_INVALID")
    elif schema_version == "ui-test.run-result.v4":
        # V4结果：验证V4链接后构建evidence index。
        if validate_document(run_result, "run-result-v4.schema.json"):
            raise RunEvidenceLinkError("E_RUN_RESULT_V4_SCHEMA_INVALID")
    elif schema_version == "ui-test.run-result.v3":
        # V3结果：保持原有验证逻辑。
        if validate_document(run_result, "run-result-v3.schema.json"):
            raise RunEvidenceLinkError("E_RUN_RESULT_V3_SCHEMA_INVALID")
    else:
        raise RunEvidenceLinkError("E_RUN_RESULT_VERSION_UNSUPPORTED")
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
    schema_version = run_result.get("schema_version", "")
    if schema_version == "ui-test.run-result.v5":
        if validate_document(run_result, "run-result-v5.schema.json"):
            issues.append("E_RUN_RESULT_V5_SCHEMA_INVALID")
    elif schema_version == "ui-test.run-result.v4":
        # ST-008：V4结果使用V4 Schema验证。
        if validate_document(run_result, "run-result-v4.schema.json"):
            issues.append("E_RUN_RESULT_V4_SCHEMA_INVALID")
    elif schema_version == "ui-test.run-result.v3":
        if validate_document(run_result, "run-result-v3.schema.json"):
            issues.append("E_RUN_RESULT_V3_SCHEMA_INVALID")
    else:
        issues.append("E_RUN_RESULT_VERSION_UNSUPPORTED")
    expected_run_hash = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
    if run_result.get("run_result_hash") != expected_run_hash:
        issues.append("E_RUN_RESULT_HASH_MISMATCH")
    if validate_document(evidence_index, "evidence-index-v2.schema.json"):
        issues.append("E_EVIDENCE_INDEX_V2_SCHEMA_INVALID")
    for field in ("run_id", "case_id", "branch_id", "run_result_hash", "resolved_test_data_ref", "resolved_test_data_hash"):
        if evidence_index.get(field) != run_result.get(field):
            issues.append(f"E_RUN_EVIDENCE_LINK_MISMATCH:{field}")
    resolved_ref = str(run_result.get("resolved_test_data_ref", ""))
    try:
        _validate_relative_ref(resolved_ref, field="resolved_test_data_ref")
    except RunEvidenceLinkError:
        return sorted(set(issues))  # 非法ref不得继续触发越界只读。
    snapshot_path = io_path(run_root) / resolved_ref
    try:
        snapshot = _verified_snapshot(snapshot_path)
        if snapshot["snapshot_hash"] != run_result.get("resolved_test_data_hash"):
            issues.append("E_RUN_SNAPSHOT_LINK_HASH_MISMATCH")
    except (OSError, ValueError):
        issues.append("E_RUN_SNAPSHOT_UNREADABLE")
    return sorted(set(issues))


# ---------------------------------------------------------------------------
# ST-008：RunResultV4 builder/verifier
# ---------------------------------------------------------------------------


def build_run_result_v4(
    *,
    run_root: str | Path,
    snapshot_path: str | Path,
    execution_context_ref: str,
    execution_context_hash: str,
    attempt_ref: str,
    attempt_hash: str,
    approval_ref: str,
    approval_hash: str,
    run_id: str,
    node_id: str,
    case_id: str,
    branch_id: str,
    overall_status: str,
    write_state: str,
    submit_count: int,
    layered_status: dict[str, str],
    step_results: list[dict[str, Any]] | None = None,
    evidence_refs: list[str] | None = None,
    retained_test_data: list[dict[str, Any]] | None = None,
    cleanup_status: str = "not_applicable",
    legacy_fixture: bool = False,
) -> dict[str, Any]:
    """ST-008：构建RunResultV4，保持V3函数和历史Schema不变。

    V4必须包含resolved snapshot ref/hash、ExecutionContext/Attempt/Approval ref/hash、
    write_state、观测submit_count、六层状态和自身hash。
    相对引用必须受包含性校验。
    """
    if legacy_fixture is not True:
        raise RunEvidenceLinkError("E_RUN_RESULT_V4_HISTORICAL_READ_ONLY")
    root = io_path(run_root)
    path = io_path(snapshot_path)
    snapshot_ref = _relative_contained(path, root)  # 先验证路径边界，再读取snapshot。
    for field, value in {
        "execution_context_ref": execution_context_ref,
        "attempt_ref": attempt_ref,
        "approval_ref": approval_ref,
    }.items():
        _validate_relative_ref(value, field=field)
    all_layers_passed = all(value == "passed" for value in layered_status.values()) and len(layered_status) == 6
    if overall_status == "passed" and not (
        all_layers_passed and write_state == "write_succeeded_verified" and submit_count == 1
    ):
        raise RunEvidenceLinkError("E_RUN_RESULT_V4_PASSED_WITHOUT_COMPLETE_EVIDENCE")
    snapshot = _verified_snapshot(path)
    if snapshot["run_id"] != run_id or snapshot["case_id"] != case_id or snapshot["branch_id"] != branch_id:
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_IDENTITY_MISMATCH")
    result: dict[str, Any] = {
        "schema_version": "ui-test.run-result.v4",
        "run_id": run_id,
        "node_id": node_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "resolved_test_data_ref": snapshot_ref,
        "resolved_test_data_hash": snapshot["snapshot_hash"],
        "execution_context_ref": execution_context_ref,
        "execution_context_hash": execution_context_hash,
        "attempt_ref": attempt_ref,
        "attempt_hash": attempt_hash,
        "approval_ref": approval_ref,
        "approval_hash": approval_hash,
        "overall_status": overall_status,
        "write_state": write_state,
        "submit_count": submit_count,
        "layered_status": copy.deepcopy(layered_status),
        "step_results": copy.deepcopy(step_results) if step_results else [],
        "evidence_refs": copy.deepcopy(evidence_refs) if evidence_refs else [],
        "conflicts": [],
        "findings": [],
        "retained_test_data": copy.deepcopy(retained_test_data) if retained_test_data else [],
        "cleanup_status": cleanup_status,
        "business_cleanup_attempted": False,
    }
    result["run_result_hash"] = canonical_hash(result)
    if validate_document(result, "run-result-v4.schema.json"):
        raise RunEvidenceLinkError("E_RUN_RESULT_V4_SCHEMA_INVALID")
    return result


def verify_run_result_v4_links(
    run_result: dict[str, Any],
    *,
    run_root: str | Path,
    expected_execution_context_ref: str | None = None,
    expected_execution_context_hash: str | None = None,
    expected_attempt_ref: str | None = None,
    expected_attempt_hash: str | None = None,
    expected_approval_ref: str | None = None,
    expected_approval_hash: str | None = None,
) -> list[str]:
    """ST-008：验证V4结果链接一致性，返回错误码列表。

    验证context/attempt/approval ref/hash一致、resolved snapshot hash一致、
    自身run_result_hash一致。禁止篡改。
    """
    issues: list[str] = []
    if validate_document(run_result, "run-result-v4.schema.json"):
        issues.append("E_RUN_RESULT_V4_SCHEMA_INVALID")
    expected_run_hash = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
    if run_result.get("run_result_hash") != expected_run_hash:
        issues.append("E_RUN_RESULT_HASH_MISMATCH")
    # 验证相对引用受包含性校验。
    for ref_field in ("resolved_test_data_ref", "execution_context_ref", "attempt_ref", "approval_ref"):
        ref = run_result.get(ref_field, "")
        try:
            _validate_relative_ref(ref, field=ref_field)
        except (RunEvidenceLinkError, TypeError):
            issues.append(f"E_RUN_RESULT_REF_ESCAPE:{ref_field}")
    # 验证已知期望值（如果提供）。
    if expected_execution_context_ref is not None and run_result.get("execution_context_ref") != expected_execution_context_ref:
        issues.append("E_EXECUTION_CONTEXT_REF_MISMATCH")
    if expected_execution_context_hash is not None and run_result.get("execution_context_hash") != expected_execution_context_hash:
        issues.append("E_EXECUTION_CONTEXT_HASH_MISMATCH")
    if expected_attempt_ref is not None and run_result.get("attempt_ref") != expected_attempt_ref:
        issues.append("E_ATTEMPT_REF_MISMATCH")
    if expected_attempt_hash is not None and run_result.get("attempt_hash") != expected_attempt_hash:
        issues.append("E_ATTEMPT_HASH_MISMATCH")
    if expected_approval_ref is not None and run_result.get("approval_ref") != expected_approval_ref:
        issues.append("E_APPROVAL_REF_MISMATCH")
    if expected_approval_hash is not None and run_result.get("approval_hash") != expected_approval_hash:
        issues.append("E_APPROVAL_HASH_MISMATCH")
    # 验证snapshot hash一致。
    resolved_ref = str(run_result.get("resolved_test_data_ref", ""))
    try:
        _validate_relative_ref(resolved_ref, field="resolved_test_data_ref")
    except RunEvidenceLinkError:
        return sorted(set(issues))
    snapshot_path = io_path(run_root) / resolved_ref
    try:
        snapshot = _verified_snapshot(snapshot_path)
        if snapshot["snapshot_hash"] != run_result.get("resolved_test_data_hash"):
            issues.append("E_RUN_SNAPSHOT_LINK_HASH_MISMATCH")
    except (OSError, ValueError):
        issues.append("E_RUN_SNAPSHOT_UNREADABLE")
    return sorted(set(issues))


# ---------------------------------------------------------------------------
# ST-013：RunResultV5 builder/verifier
# ---------------------------------------------------------------------------


def build_run_result_v5(
    *,
    run_root: str | Path,
    snapshot_path: str | Path,
    transaction_id: str,
    session_id: str,
    execution_context_ref: str,
    execution_context_hash: str,
    attempt_ref: str,
    pre_terminal_events_hash: str,
    approval_ref: str,
    approval_hash: str,
    run_id: str,
    node_id: str,
    case_id: str,
    branch_id: str,
    pytest_phase_status: dict[str, str],
    overall_status: str,
    write_state: str,
    submit_count: int,
    step_results: list[dict[str, Any]] | None = None,
    evidence_refs: list[str] | None = None,
    retained_test_data: list[dict[str, Any]] | None = None,
    cleanup_status: str = "not_applicable",
) -> dict[str, Any]:
    """构建不含PyCharm/人工自证字段的RunResultV5。"""
    root = io_path(run_root)
    path = io_path(snapshot_path)
    snapshot_ref = _relative_contained(path, root)  # fail closed before opening caller-supplied path。
    for field, value in {
        "execution_context_ref": execution_context_ref,
        "attempt_ref": attempt_ref,
        "approval_ref": approval_ref,
    }.items():
        _validate_relative_ref(value, field=field)
    all_phases_passed = (
        set(pytest_phase_status) == {"setup", "call", "teardown"}
        and all(pytest_phase_status.get(name) == "passed" for name in ("setup", "call", "teardown"))
    )
    if overall_status == "passed" and not (
        all_phases_passed and write_state == "write_succeeded_verified" and submit_count == 1
    ):
        raise RunEvidenceLinkError("E_RUN_RESULT_V5_PASSED_WITHOUT_COMPLETE_EVIDENCE")
    snapshot = _verified_snapshot(path)
    if snapshot["run_id"] != run_id or snapshot["case_id"] != case_id or snapshot["branch_id"] != branch_id:
        raise RunEvidenceLinkError("E_RUN_SNAPSHOT_IDENTITY_MISMATCH")
    result: dict[str, Any] = {
        "schema_version": "ui-test.run-result.v5",
        "transaction_id": transaction_id,
        "session_id": session_id,
        "run_id": run_id,
        "node_id": node_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "resolved_test_data_ref": snapshot_ref,
        "resolved_test_data_hash": snapshot["snapshot_hash"],
        "execution_context_ref": execution_context_ref,
        "execution_context_hash": execution_context_hash,
        "attempt_ref": attempt_ref,
        "pre_terminal_events_hash": pre_terminal_events_hash,
        "approval_ref": approval_ref,
        "approval_hash": approval_hash,
        "pytest_phase_status": copy.deepcopy(pytest_phase_status),
        "overall_status": overall_status,
        "write_state": write_state,
        "submit_count": submit_count,
        "step_results": copy.deepcopy(step_results) if step_results else [],
        "evidence_refs": copy.deepcopy(evidence_refs) if evidence_refs else [],
        "conflicts": [],
        "findings": [],
        "retained_test_data": copy.deepcopy(retained_test_data) if retained_test_data else [],
        "cleanup_status": cleanup_status,
        "business_cleanup_attempted": False,
    }
    result["run_result_hash"] = canonical_hash(result)
    if validate_document(result, "run-result-v5.schema.json"):
        raise RunEvidenceLinkError("E_RUN_RESULT_V5_SCHEMA_INVALID")
    return result


def verify_run_result_v5_links(
    run_result: dict[str, Any],
    *,
    run_root: str | Path,
    expected_transaction_id: str | None = None,
    expected_session_id: str | None = None,
    expected_run_id: str | None = None,
    expected_node_id: str | None = None,
    expected_execution_context_ref: str | None = None,
    expected_execution_context_hash: str | None = None,
    expected_attempt_ref: str | None = None,
    expected_pre_terminal_events_hash: str | None = None,
    expected_approval_ref: str | None = None,
    expected_approval_hash: str | None = None,
    expected_pytest_phase_status: dict[str, str] | None = None,
) -> list[str]:
    """验证V5身份、阶段、引用、快照和自身hash，拒绝自证字段。"""
    issues: list[str] = []
    if validate_document(run_result, "run-result-v5.schema.json"):
        issues.append("E_RUN_RESULT_V5_SCHEMA_INVALID")
    for field in ("pycharm_integration", "human_r2", "layered_status"):
        if field in run_result:
            issues.append(f"E_RUN_RESULT_V5_SELF_ATTESTATION_FORBIDDEN:{field}")
    expected_run_hash = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
    if run_result.get("run_result_hash") != expected_run_hash:
        issues.append("E_RUN_RESULT_HASH_MISMATCH")
    for ref_field in ("resolved_test_data_ref", "execution_context_ref", "attempt_ref", "approval_ref"):
        try:
            _validate_relative_ref(run_result.get(ref_field, ""), field=ref_field)
        except (RunEvidenceLinkError, TypeError):
            issues.append(f"E_RUN_RESULT_REF_ESCAPE:{ref_field}")

    expected_values = {
        "transaction_id": (expected_transaction_id, "E_TRANSACTION_ID_MISMATCH"),
        "session_id": (expected_session_id, "E_SESSION_ID_MISMATCH"),
        "run_id": (expected_run_id, "E_RUN_ID_MISMATCH"),
        "node_id": (expected_node_id, "E_NODE_ID_MISMATCH"),
        "execution_context_ref": (expected_execution_context_ref, "E_EXECUTION_CONTEXT_REF_MISMATCH"),
        "execution_context_hash": (expected_execution_context_hash, "E_EXECUTION_CONTEXT_HASH_MISMATCH"),
        "attempt_ref": (expected_attempt_ref, "E_ATTEMPT_REF_MISMATCH"),
        "pre_terminal_events_hash": (expected_pre_terminal_events_hash, "E_PRE_TERMINAL_EVENTS_HASH_MISMATCH"),
        "approval_ref": (expected_approval_ref, "E_APPROVAL_REF_MISMATCH"),
        "approval_hash": (expected_approval_hash, "E_APPROVAL_HASH_MISMATCH"),
        "pytest_phase_status": (expected_pytest_phase_status, "E_PYTEST_PHASE_STATUS_MISMATCH"),
    }
    for field, (expected, error_code) in expected_values.items():
        if expected is not None and run_result.get(field) != expected:
            issues.append(error_code)

    resolved_ref = str(run_result.get("resolved_test_data_ref", ""))
    try:
        _validate_relative_ref(resolved_ref, field="resolved_test_data_ref")
    except RunEvidenceLinkError:
        return sorted(set(issues))
    snapshot_path = io_path(run_root) / resolved_ref
    try:
        snapshot = _verified_snapshot(snapshot_path)
        if snapshot["snapshot_hash"] != run_result.get("resolved_test_data_hash"):
            issues.append("E_RUN_SNAPSHOT_LINK_HASH_MISMATCH")
        for field in ("run_id", "case_id", "branch_id"):
            if snapshot.get(field) != run_result.get(field):
                issues.append(f"E_RUN_SNAPSHOT_LINK_IDENTITY_MISMATCH:{field}")
    except (OSError, ValueError):
        issues.append("E_RUN_SNAPSHOT_UNREADABLE")
    return sorted(set(issues))
