"""ST-013版本化契约、2.2配置门禁与历史字节兼容性测试。"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from scripts.ui_test_core.project_config import ProjectConfigError, load_project_config
from scripts.ui_test_core.strict_json import load_strict_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = SKILL_ROOT / "schemas"
FIXTURES = SKILL_ROOT / "assets" / "fixtures"
HASH = "sha256:" + "1" * 64
HASH_2 = "sha256:" + "2" * 64
OBJECT_REF = "objects/" + "1" * 64 + ".json"


def _schema(name: str) -> dict:
    # 所有Schema均从候选Skill根读取，测试不接受调用方覆盖路径。
    return load_strict_json(SCHEMAS / name)


def _validate(name: str, document: dict) -> None:
    Draft202012Validator(_schema(name), format_checker=Draft202012Validator.FORMAT_CHECKER).validate(document)


def _project_v22() -> dict:
    document = copy.deepcopy(load_strict_json(FIXTURES / "project-v2.1-valid.json"))
    document["schema_version"] = "2.2"
    document["pycharm_manual_execution"].update(
        {
            "contract_version": 3,
            "finalization_contract": "transaction-v1",
            "run_result_contract": "v5",
            "session_result_contract": "v1",
            "acceptance_contract": "external-exit-v1",
        }
    )
    return document


def _context_v3() -> dict:
    return {
        "schema_version": "ui-test.execution-context.v3",
        "session_id": "SESSION-001",
        "execution_origin": "pycharm",
        "origin_evidence": {
            "source_type": "jetbrains-runner-path",
            "evidence_digest": HASH,
            "runner_path_hash": HASH_2,
            "runner_content_hash": HASH,
            "invocation_marker": "_jb_pytest_runner.py",
        },
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "risk_level": "r2-ui-write-test",
        "environment": "test",
        "approved": True,
        "approval_source": "pycharm-project-policy",
        "stable_runner_digest": HASH,
        "active_build_fingerprint": HASH,
        "active_attachment_digest": HASH,
        "project_config_digest": HASH,
        "finalization_policy_digest": HASH,
        "attempt_ref": "attempts/attempt-001",
        "finalization_contract": "transaction-v1",
        "run_result_contract": "v5",
        "session_result_contract": "v1",
        "acceptance_contract": "external-exit-v1",
        "config_summary": {
            "schema_version": "2.2",
            "contract_version": 3,
            "origin_detection": "jetbrains-runner-path",
            "entry_scope": "stable-active-runners",
            "r2_authorization": "auto-test-only",
            "run_scope": "per-node",
            "r2_parallelism": "serial-project-environment",
            "finalization_contract": "transaction-v1",
            "run_result_contract": "v5",
            "session_result_contract": "v1",
            "acceptance_contract": "external-exit-v1",
        },
    }


def _attempt_v2() -> dict:
    events = [
        ("detected", None),
        ("executing", "setup"),
        ("executing", "call"),
        ("executing", "teardown"),
        ("finalization_started", "finalization"),
        ("finalization_committed", "finalization"),
    ]
    return {
        "schema_version": "ui-test.execution-attempt.v2",
        "attempt_id": "ATTEMPT-001",
        "session_id": "SESSION-001",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "finalization_mode": "transaction-v1",
        "diagnostics_admission": {"admitted": True, "admission_digest": HASH},
        "events": [
            {
                "event_type": event_type,
                "recorded_at": f"2026-09-04T10:00:0{index}Z",
                "event_digest": HASH,
                **({"phase": phase} if phase else {}),
                **({"transaction_id": "TX-001"} if event_type.startswith("finalization_") else {}),
            }
            for index, (event_type, phase) in enumerate(events)
        ],
        "pre_terminal_events_hash": HASH,
        "finalization_commit_ref": "finalization/finalization-commit.json",
        "finalization_commit_hash": HASH,
        "finalization_receipt_ref": "finalization/finalization-receipt.json",
        "finalization_receipt_hash": HASH,
        "terminal": {
            "status": "passed",
            "recorded_at": "2026-09-04T10:00:07Z",
            "terminal_digest": HASH,
            "is_unique_terminal": True,
        },
        "evidence_refs": ["reports/resolved-test-data.json"],
    }


def _run_result_v5() -> dict:
    return {
        "schema_version": "ui-test.run-result.v5",
        "transaction_id": "TX-001",
        "session_id": "SESSION-001",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "resolved_test_data_ref": "reports/resolved-test-data.json",
        "resolved_test_data_hash": HASH,
        "execution_context_ref": "attempts/attempt-001/execution-context.json",
        "execution_context_hash": HASH,
        "attempt_ref": "attempts/attempt-001",
        "pre_terminal_events_hash": HASH,
        "approval_ref": "approval-record.json",
        "approval_hash": HASH,
        "pytest_phase_status": {"setup": "passed", "call": "passed", "teardown": "passed"},
        "overall_status": "passed",
        "write_state": "write_succeeded_verified",
        "submit_count": 1,
        "step_results": [],
        "evidence_refs": ["reports/attachments/before-submit.png"],
        "conflicts": [],
        "findings": [],
        "retained_test_data": [],
        "cleanup_status": "not_planned_this_release",
        "business_cleanup_attempted": False,
        "run_result_hash": HASH,
    }


def _commit() -> dict:
    return {
        "schema_version": "ui-test.finalization-commit.v1",
        "transaction_id": "TX-001",
        "session_id": "SESSION-001",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "status": "committed",
        "candidate_hash": HASH,
        "pre_terminal_events_hash": HASH,
        "run_result_ref": OBJECT_REF,
        "run_result_hash": HASH,
        "evidence_index_ref": "objects/" + "2" * 64 + ".json",
        "evidence_index_hash": HASH_2,
        "atomic_publish": True,
        "committed_at": "2026-09-04T10:00:06Z",
        "commit_hash": HASH,
    }


def _receipt(*, failed: bool = False) -> dict:
    base = {
        "schema_version": "ui-test.run-finalization-receipt.v1",
        "transaction_id": "TX-001",
        "session_id": "SESSION-001",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "status": "failed" if failed else "committed",
        "recovery_mode": "none",
        "recorded_at": "2026-09-04T10:00:07Z",
        "receipt_hash": HASH,
    }
    if failed:
        base.update({"error_code": "E_FINALIZER_FAILED", "exception_class": "RuntimeError", "message_digest": HASH})
    else:
        base.update(
            {
                "commit_manifest_ref": "finalization/finalization-commit.json",
                "commit_manifest_hash": HASH,
                "run_result_ref": OBJECT_REF,
                "run_result_hash": HASH,
                "evidence_index_ref": "objects/" + "2" * 64 + ".json",
                "evidence_index_hash": HASH_2,
            }
        )
    return base


def _session_result() -> dict:
    return {
        "schema_version": "ui-test.pytest-session-result.v1",
        "session_id": "SESSION-001",
        "execution_origin": "pycharm",
        "origin_evidence_digest": HASH,
        "nodes": [
            {
                "run_id": "RUN-001",
                "node_id": "test_case.py::test_case",
                "terminal_ref": "attempts/attempt-001/terminal.json",
                "terminal_hash": HASH,
                "finalization_status": "committed",
                "receipt_ref": "finalization/finalization-receipt.json",
                "receipt_hash": HASH,
            }
        ],
        "pytest_exitstatus": 0,
        "all_required_nodes_committed": True,
        "session_status": "passed",
        "recorded_at": "2026-09-04T10:00:08Z",
        "session_result_hash": HASH,
    }


def _acceptance() -> dict:
    return {
        "schema_version": "ui-test.pycharm-acceptance-result.v1",
        "acceptance_id": "ACCEPT-001",
        "session_id": "SESSION-001",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "helper_identity_digest": HASH,
        "authorization_ref": "approvals/run-001.json",
        "authorization_hash": HASH,
        "approval_source": "pycharm-project-policy",
        "execution_context_ref": "attempts/attempt-001/execution-context.json",
        "execution_context_hash": HASH,
        "terminal_ref": "attempts/attempt-001/terminal.json",
        "terminal_hash": HASH,
        "run_result_ref": OBJECT_REF,
        "run_result_hash": HASH,
        "finalization_commit_ref": "finalization/finalization-commit.json",
        "finalization_commit_hash": HASH,
        "finalization_receipt_ref": "finalization/finalization-receipt.json",
        "finalization_receipt_hash": HASH,
        "pytest_session_result_ref": "sessions/session-001.json",
        "pytest_session_result_hash": HASH,
        "console_evidence_ref": "console/session-001-summary.json",
        "console_evidence_hash": HASH,
        "pytest_session_exitstatus": 0,
        "observed_process_exit_code": 0,
        "post_run_recovery": False,
        "pycharm_integration": "passed",
        "human_r2": "passed",
        "overall_status": "passed",
        "evaluation_authority": "independent-qa",
        "evaluated_at": "2026-09-04T10:00:09Z",
        "acceptance_hash": HASH,
    }


def _process_evidence() -> dict:
    return {
        "schema_version": "ui-test.pycharm-process-evidence.v1",
        "session_id": "SESSION-001",
        "helper_path_hash": HASH,
        "helper_content_hash": HASH_2,
        "observed_process_exit_code": 0,
        "pytest_exitstatus": 0,
        "stdout_hash": HASH,
        "stderr_hash": HASH_2,
        "recorded_at": "2026-09-04T10:00:08Z",
        "process_evidence_hash": HASH,
    }


def test_new_contract_family_has_valid_positive_documents() -> None:
    documents = {
        "ui-test-project-v2.2.schema.json": _project_v22(),
        "execution-context-v3.schema.json": _context_v3(),
        "execution-attempt-v2.schema.json": _attempt_v2(),
        "run-result-v5.schema.json": _run_result_v5(),
        "finalization-commit-v1.schema.json": _commit(),
        "run-finalization-receipt-v1.schema.json": _receipt(),
        "pytest-session-result-v1.schema.json": _session_result(),
        "pycharm-process-evidence-v1.schema.json": _process_evidence(),
        "pycharm-acceptance-result-v1.schema.json": _acceptance(),
    }
    for schema_name, document in documents.items():
        Draft202012Validator.check_schema(_schema(schema_name))
        _validate(schema_name, document)


def test_project_v22_requires_all_finalization_contract_fields() -> None:
    document = _project_v22()
    document["pycharm_manual_execution"].pop("finalization_contract")
    with pytest.raises(ValidationError):
        _validate("ui-test-project-v2.2.schema.json", document)


def test_attempt_v2_passed_requires_commit_and_receipt_closure() -> None:
    document = _attempt_v2()
    document.pop("finalization_receipt_hash")
    with pytest.raises(ValidationError):
        _validate("execution-attempt-v2.schema.json", document)


def test_attempt_v2_finalizer_error_requires_redacted_exception_fields() -> None:
    # finalizer治理错误使用error terminal，并要求异常类和消息摘要而非原始消息。
    document = _attempt_v2()
    document["events"][-1] = {
        "event_type": "finalization_failed",
        "recorded_at": "2026-09-04T10:00:06Z",
        "event_digest": HASH,
        "phase": "finalization",
        "transaction_id": "TX-001",
        "code": "E_FINALIZER_FAILED",
        "exception_class": "RuntimeError",
        "message_digest": HASH,
    }
    for field in ("pre_terminal_events_hash", "finalization_commit_ref", "finalization_commit_hash", "finalization_receipt_ref", "finalization_receipt_hash"):
        document.pop(field)
    document["terminal"]["status"] = "error"
    _validate("execution-attempt-v2.schema.json", document)
    document["events"][-1].pop("message_digest")
    with pytest.raises(ValidationError):
        _validate("execution-attempt-v2.schema.json", document)


def test_run_result_v5_cannot_self_declare_pycharm_or_human_status() -> None:
    document = _run_result_v5()
    document["pycharm_integration"] = "passed"
    with pytest.raises(ValidationError):
        _validate("run-result-v5.schema.json", document)


def test_failed_receipt_requires_redacted_exception_identity() -> None:
    _validate("run-finalization-receipt-v1.schema.json", _receipt(failed=True))
    document = _receipt(failed=True)
    document.pop("message_digest")
    with pytest.raises(ValidationError):
        _validate("run-finalization-receipt-v1.schema.json", document)


@pytest.mark.parametrize("field,value", [("pytest_session_exitstatus", 1), ("observed_process_exit_code", 1), ("post_run_recovery", True)])
def test_acceptance_pass_is_blocked_by_nonzero_exit_or_recovery(field: str, value: int | bool) -> None:
    document = _acceptance()
    document[field] = value
    with pytest.raises(ValidationError):
        _validate("pycharm-acceptance-result-v1.schema.json", document)


def test_session_pass_requires_zero_pytest_exitstatus() -> None:
    document = _session_result()
    document["pytest_exitstatus"] = 1
    with pytest.raises(ValidationError):
        _validate("pytest-session-result-v1.schema.json", document)


def test_loader_accepts_v22_execute_and_keeps_v21_inventory_only(tmp_path: Path) -> None:
    v22_path = tmp_path / "project-v2.2.json"
    v22_path.write_text(json.dumps(_project_v22(), ensure_ascii=False), encoding="utf-8")
    loaded = load_project_config(v22_path, purpose="execute")
    assert loaded["execution_ready"] is True
    assert loaded["config_issues"] == []

    v21_path = tmp_path / "project-v2.1.json"
    v21_path.write_text(json.dumps(load_strict_json(FIXTURES / "project-v2.1-valid.json"), ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ProjectConfigError, match="E_UI_TEST_CONFIG_MIGRATION_REQUIRED"):
        load_project_config(v21_path, purpose="execute")
    historical = load_project_config(v21_path, purpose="inventory")
    assert historical["execution_ready"] is False
    assert historical["config_issues"] == ["E_UI_TEST_CONFIG_MIGRATION_REQUIRED"]


def test_historical_schema_bytes_are_unchanged() -> None:
    expected = {
        "ui-test-project-v2.1.schema.json": "cab34267c448c69392f81e8348c6a457c9a9581f37025d0dc90f8183a461a43b",
        "execution-context-v2.schema.json": "df9d9e5fa08a4a33b32e63a013744b1048cb9fee3d67bbacf34573c1e0c0869c",
        "execution-attempt-v1.schema.json": "9f25389c8e8ba1053fab986a1d1216953ab108e92168dbd9f2e3444724f2d53d",
        "run-result-v4.schema.json": "ebc35375b660385e93b669ec1e33730d12850307d86a833454033d9cdb6fa192",
    }
    actual = {name: hashlib.sha256((SCHEMAS / name).read_bytes()).hexdigest() for name in expected}
    assert actual == expected
