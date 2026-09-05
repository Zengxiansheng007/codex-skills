"""ST-013 文件读回型 PyCharm Acceptance 与完整链校验。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.ui_test_core.case_contracts import canonical_hash
from scripts.ui_test_core.pycharm_acceptance import (
    PyCharmAcceptanceError,
    build_pycharm_acceptance_from_files,
    build_pycharm_process_evidence,
    validate_pycharm_acceptance_chain,
)


H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64


def _seal(document: dict, field: str) -> dict:
    document[field] = canonical_hash(document)
    return document


def _documents(*, helper_path_hash: str, helper_content_hash: str, exit_code: int = 0) -> dict[str, dict]:
    approval = {
        "schema_version": "ui-test.r2-approval-record.v2",
        "approval_id": "APR-001",
        "approval_source": "pycharm-project-policy",
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "environment": "test",
        "allowed_action": "create-announcement",
        "channel": "visible-ui",
        "max_submit_count": 1,
        "decision": "approved",
        "boundary_hash": H1,
        "credential_values_persisted": False,
        "reusable_across_runs": False,
        "risk_level": "r2-ui-write-test",
        "stable_runner_digest": H1,
        "active_build_fingerprint": H1,
        "active_attachment_digest": H1,
    }
    approval["boundary_hash"] = canonical_hash(
        {
            key: approval[key]
            for key in (
                "run_id", "case_id", "environment", "allowed_action", "channel", "max_submit_count"
            )
        }
    )
    context = {
        "schema_version": "ui-test.execution-context.v3",
        "session_id": "SESSION-001",
        "execution_origin": "pycharm",
        "origin_evidence": {
            "source_type": "jetbrains-runner-path",
            "evidence_digest": H1,
            "runner_path_hash": helper_path_hash,
            "runner_content_hash": helper_content_hash,
            "argv0": "_jb_pytest_runner.py",
            "invocation_marker": "runner-path-and-file",
        },
        "run_id": "RUN-001",
        "node_id": "test_case.py::test_case",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "risk_level": "r2-ui-write-test",
        "environment": "test",
        "approved": True,
        "approval_source": "pycharm-project-policy",
        "stable_runner_digest": H1,
        "active_build_fingerprint": H1,
        "active_attachment_digest": H1,
        "project_config_digest": H1,
        "finalization_policy_digest": H2,
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
    run = _seal(
        {
            "schema_version": "ui-test.run-result.v5",
            "transaction_id": "TX-001",
            "session_id": "SESSION-001",
            "run_id": "RUN-001",
            "node_id": "test_case.py::test_case",
            "case_id": "CASE-001",
            "branch_id": "primary",
            "resolved_test_data_ref": "reports/resolved-test-data.json",
            "resolved_test_data_hash": H1,
            "execution_context_ref": "attempts/attempt-001/execution-context.json",
            "execution_context_hash": canonical_hash(context),
            "attempt_ref": "attempts/attempt-001",
            "pre_terminal_events_hash": H2,
            "approval_ref": "approval-record.json",
            "approval_hash": canonical_hash(approval),
            "pytest_phase_status": {"setup": "passed", "call": "passed", "teardown": "passed"},
            "overall_status": "passed",
            "write_state": "write_succeeded_verified",
            "submit_count": 1,
            "step_results": [],
            "evidence_refs": [],
            "conflicts": [],
            "findings": [],
            "retained_test_data": [],
            "cleanup_status": "not_planned_this_release",
            "business_cleanup_attempted": False,
        },
        "run_result_hash",
    )
    commit = _seal(
        {
            "schema_version": "ui-test.finalization-commit.v1",
            "transaction_id": "TX-001",
            "session_id": "SESSION-001",
            "run_id": "RUN-001",
            "node_id": "test_case.py::test_case",
            "status": "committed",
            "candidate_hash": H1,
            "pre_terminal_events_hash": H2,
            "run_result_ref": "objects/" + canonical_hash(run).removeprefix("sha256:") + ".json",
            "run_result_hash": run["run_result_hash"],
            "evidence_index_ref": "objects/" + "2" * 64 + ".json",
            "evidence_index_hash": H2,
            "atomic_publish": True,
            "committed_at": "2026-09-04T10:00:06Z",
        },
        "commit_hash",
    )
    receipt = _seal(
        {
            "schema_version": "ui-test.run-finalization-receipt.v1",
            "transaction_id": "TX-001",
            "session_id": "SESSION-001",
            "run_id": "RUN-001",
            "node_id": "test_case.py::test_case",
            "status": "committed",
            "recovery_mode": "none",
            "commit_manifest_ref": "finalization/finalization-commit.json",
            "commit_manifest_hash": canonical_hash(commit),
            "run_result_ref": commit["run_result_ref"],
            "run_result_hash": run["run_result_hash"],
            "evidence_index_ref": commit["evidence_index_ref"],
            "evidence_index_hash": commit["evidence_index_hash"],
            "recorded_at": "2026-09-04T10:00:07Z",
        },
        "receipt_hash",
    )
    terminal = {
        "status": "passed",
        "is_unique_terminal": True,
        "recorded_at": "2026-09-04T10:00:07Z",
        "code": "PYTEST_PASSED",
        "commit_manifest_ref": "runs/RUN-001/finalization/finalization-commit.json",
        "commit_manifest_hash": canonical_hash(commit),
        "receipt_ref": "runs/RUN-001/finalization/finalization-receipt.json",
        "receipt_hash": canonical_hash(receipt),
        "pre_terminal_events_hash": H2,
        "recovery_mode": "none",
    }
    session = _seal(
        {
            "schema_version": "ui-test.pytest-session-result.v1",
            "session_id": "SESSION-001",
            "execution_origin": "pycharm",
            "origin_evidence_digest": H1,
            "nodes": [
                {
                    "run_id": "RUN-001",
                    "node_id": "test_case.py::test_case",
                    "terminal_ref": "attempts/attempt-001/terminal.json",
                    "terminal_hash": canonical_hash(terminal),
                    "finalization_status": "committed",
                    "receipt_ref": "runs/RUN-001/finalization/finalization-receipt.json",
                    "receipt_hash": canonical_hash(receipt),
                }
            ],
            "pytest_exitstatus": 0,
            "all_required_nodes_committed": True,
            "session_status": "passed",
            "recorded_at": "2026-09-04T10:00:08Z",
        },
        "session_result_hash",
    )
    process = _seal(
        {
            "schema_version": "ui-test.pycharm-process-evidence.v1",
            "session_id": "SESSION-001",
            "helper_path_hash": helper_path_hash,
            "helper_content_hash": helper_content_hash,
            "observed_process_exit_code": exit_code,
            "pytest_exitstatus": 0,
            "stdout_hash": H1,
            "stderr_hash": H2,
            "recorded_at": "2026-09-04T10:00:08Z",
        },
        "process_evidence_hash",
    )
    return {
        "approval": approval,
        "context": context,
        "run": run,
        "commit": commit,
        "receipt": receipt,
        "terminal": terminal,
        "session": session,
        "process": process,
    }


def _write(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def _build_from_files(tmp_path: Path, *, exit_code: int = 0) -> tuple[dict, dict[str, dict]]:
    helper = tmp_path / "helpers" / "pycharm" / "_jb_pytest_runner.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# synthetic helper identity\n", encoding="utf-8")
    helper_path_hash = "sha256:" + hashlib.sha256(str(helper.resolve()).lower().encode("utf-8")).hexdigest()
    helper_content_hash = "sha256:" + hashlib.sha256(helper.read_bytes()).hexdigest()
    documents = _documents(
        helper_path_hash=helper_path_hash,
        helper_content_hash=helper_content_hash,
        exit_code=exit_code,
    )
    documents["process"] = build_pycharm_process_evidence(
        helper_path=helper,
        session_id="SESSION-001",
        observed_process_exit_code=exit_code,
        pytest_exitstatus=0,
        stdout="synthetic stdout",
        stderr="",
        recorded_at="2026-09-04T10:00:08Z",
    )
    paths = {name: _write(tmp_path / "evidence" / f"{name}.json", document) for name, document in documents.items()}
    result = build_pycharm_acceptance_from_files(
        helper_path=helper,
        run_result_path=paths["run"],
        finalization_commit_path=paths["commit"],
        finalization_receipt_path=paths["receipt"],
        pytest_session_result_path=paths["session"],
        approval_record_path=paths["approval"],
        execution_context_path=paths["context"],
        terminal_path=paths["terminal"],
        process_evidence_path=paths["process"],
        authorization_ref="approvals/run-001.json",
        process_evidence_ref="console/session-001.json",
        finalization_commit_ref="runs/RUN-001/finalization/finalization-commit.json",
        finalization_receipt_ref="runs/RUN-001/finalization/finalization-receipt.json",
        pytest_session_result_ref="sessions/session-001.json",
        evaluation_authority="codex-independent-review",
        evaluated_at="2026-09-04T10:00:09Z",
    )
    return result, documents


def test_zero_original_process_exit_can_be_accepted_from_files(tmp_path: Path) -> None:
    result, _documents_map = _build_from_files(tmp_path)
    assert result["overall_status"] == "passed"
    assert result["pycharm_integration"] == "passed"
    assert result["human_r2"] == "passed"


def test_nonzero_original_process_exit_is_never_accepted(tmp_path: Path) -> None:
    result, _documents_map = _build_from_files(tmp_path, exit_code=1)
    assert result["overall_status"] == "failed"
    assert result["human_r2"] == "failed"


def test_tampered_process_or_result_file_is_rejected(tmp_path: Path) -> None:
    result, documents = _build_from_files(tmp_path)
    documents["run"]["findings"].append("tampered")
    issues = validate_pycharm_acceptance_chain(
        run_result=documents["run"],
        finalization_commit=documents["commit"],
        finalization_receipt=documents["receipt"],
        pytest_session_result=documents["session"],
        acceptance_result=result,
        approval_record=documents["approval"],
        execution_context=documents["context"],
        terminal=documents["terminal"],
        process_evidence=documents["process"],
    )
    assert "run-result-hash" in issues


def test_helper_content_must_match_process_evidence(tmp_path: Path) -> None:
    helper = tmp_path / "helpers" / "pycharm" / "_jb_pytest_runner.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# first\n", encoding="utf-8")
    path_hash = "sha256:" + hashlib.sha256(str(helper.resolve()).lower().encode("utf-8")).hexdigest()
    content_hash = "sha256:" + hashlib.sha256(helper.read_bytes()).hexdigest()
    documents = _documents(helper_path_hash=path_hash, helper_content_hash=content_hash)
    paths = {name: _write(tmp_path / "evidence" / f"{name}.json", document) for name, document in documents.items()}
    helper.write_text("# changed\n", encoding="utf-8")
    with pytest.raises(PyCharmAcceptanceError, match="E_ACCEPTANCE_HELPER_CONTENT_HASH_MISMATCH"):
        build_pycharm_acceptance_from_files(
            helper_path=helper,
            run_result_path=paths["run"],
            finalization_commit_path=paths["commit"],
            finalization_receipt_path=paths["receipt"],
            pytest_session_result_path=paths["session"],
            approval_record_path=paths["approval"],
            execution_context_path=paths["context"],
            terminal_path=paths["terminal"],
            process_evidence_path=paths["process"],
            authorization_ref="approvals/run.json",
            process_evidence_ref="console/session.json",
            finalization_commit_ref="runs/RUN-001/finalization/commit.json",
            finalization_receipt_ref="runs/RUN-001/finalization/receipt.json",
            pytest_session_result_ref="sessions/session.json",
            evaluation_authority="independent-qa",
        )
