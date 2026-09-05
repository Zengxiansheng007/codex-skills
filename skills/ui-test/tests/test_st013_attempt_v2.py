"""ST-013 AttemptV2 finalization 状态与恢复门禁。"""

from __future__ import annotations

import json

import pytest

from scripts.ui_test_core.attempt_recovery import AttemptRecovery
from scripts.ui_test_core.execution_attempt_store import (
    ExecutionAttemptStore,
    ExecutionAttemptStoreError,
)


RUN_ID = "RUN-ST013-001"
NODE_ID = "test_st013.py::test_node"
DIGEST = "sha256:" + "a" * 64


def _store(tmp_path):
    return ExecutionAttemptStore(
        evidence_root=tmp_path / "evidence",
        now_func=lambda: "2026-09-04T00:00:00Z",
    )


def _start_v2(store: ExecutionAttemptStore) -> None:
    store.create_attempt_start(
        run_id=RUN_ID,
        node_id=NODE_ID,
        case_id="CASE-ST013",
        branch_id="branch-a",
        risk_level="r2-ui-write-test",
        execution_origin="pycharm",
        approval_source="pycharm-project-policy",
        stable_runner_digest=DIGEST,
        project_config_digest=DIGEST,
        schema_version="ui-test.execution-attempt.v2",
        session_id="SESSION-ST013-001",
        finalization_mode="transaction-v1",
    )
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="admitted",
        phase="setup",
        code="ADMITTED",
    )


def test_legacy_attempt_and_context_writers_require_explicit_fixture_mode(tmp_path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ExecutionAttemptStoreError, match="E_ATTEMPT_V1_HISTORICAL_READ_ONLY"):
        store.create_attempt_start(
            run_id="RUN-LEGACY",
            node_id="legacy.py::test_node",
            case_id="CASE-LEGACY",
            branch_id="primary",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest=DIGEST,
            project_config_digest=DIGEST,
        )
    store.create_attempt_start(
        run_id="RUN-LEGACY",
        node_id="legacy.py::test_node",
        case_id="CASE-LEGACY",
        branch_id="primary",
        risk_level="r0-read-only",
        execution_origin="cli",
        approval_source="explicit-cli",
        stable_runner_digest=DIGEST,
        project_config_digest=DIGEST,
        legacy_fixture=True,
    )
    with pytest.raises(ExecutionAttemptStoreError, match="E_EXECUTION_CONTEXT_V2_HISTORICAL_READ_ONLY"):
        store.write_execution_context(
            run_id="RUN-LEGACY",
            node_id="legacy.py::test_node",
            context_document={"schema_version": "ui-test.execution-context.v2"},
        )


def test_v2_passed_terminal_requires_commit_receipt_and_event(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)

    with pytest.raises(ExecutionAttemptStoreError) as captured:
        store.create_terminal(run_id=RUN_ID, node_id=NODE_ID, status="passed")
    assert captured.value.code == "E_TERMINAL_FINALIZATION_CLOSURE_REQUIRED"

    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_started",
        phase="finalization",
        code="FINALIZATION_STARTED",
        transaction_id="FIN-ST013-001",
    )
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_committed",
        phase="finalization",
        code="FINALIZATION_COMMITTED",
        transaction_id="FIN-ST013-001",
    )
    with pytest.raises(ExecutionAttemptStoreError) as readback_required:
        store.create_terminal(
            run_id=RUN_ID,
            node_id=NODE_ID,
            status="passed",
            code="PYTEST_PASSED",
            commit_manifest_ref=f"runs/{RUN_ID}/finalization/finalization-commit.json",
            commit_manifest_hash=DIGEST,
            receipt_ref=f"runs/{RUN_ID}/finalization/finalization-receipt.json",
            receipt_hash=DIGEST,
            pre_terminal_events_hash=DIGEST,
        )
    assert readback_required.value.code == "E_TERMINAL_FINALIZATION_READBACK_REQUIRED"
    assert store.read_terminal(run_id=RUN_ID, node_id=NODE_ID) is None


def test_v2_finalization_failure_is_redacted_and_never_passed(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_started",
        phase="finalization",
        code="FINALIZATION_STARTED",
        transaction_id="FIN-ST013-002",
    )
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_failed",
        phase="finalization",
        code="E_FINALIZER_FAILED",
        exception_class="RuntimeError",
        message_digest=DIGEST,
        transaction_id="FIN-ST013-002",
    )
    store.create_terminal(
        run_id=RUN_ID,
        node_id=NODE_ID,
        status="failed",
        code="E_FINALIZER_FAILED",
    )

    events = store.read_events(run_id=RUN_ID, node_id=NODE_ID)
    failure = next(event for event in events if event["event_type"] == "finalization_failed")
    assert failure["exception_class"] == "RuntimeError"
    assert failure["message_digest"] == DIGEST
    assert "message" not in failure
    assert store.read_terminal(run_id=RUN_ID, node_id=NODE_ID)["status"] == "failed"
    assert store.project_attempt(
        run_id=RUN_ID,
        node_id=NODE_ID,
        case_id="CASE-ST013",
        branch_id="branch-a",
    )["terminal"]["status"] == "failed"


def test_recovery_after_commit_event_never_synthesizes_passed(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_started",
        phase="finalization",
        code="FINALIZATION_STARTED",
    )
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_committed",
        phase="finalization",
        code="FINALIZATION_COMMITTED",
    )

    summary = AttemptRecovery(store=store).scan_and_recover()
    assert summary["unresolved_attempts"][0]["finalization_state"] == "receipt_without_terminal"
    assert store.read_terminal(run_id=RUN_ID, node_id=NODE_ID) is None
    recovery_path = next((tmp_path / "evidence" / "attempts").glob("*/recovery.jsonl"))
    recovery = json.loads(recovery_path.read_text(encoding="utf-8").splitlines()[0])
    assert recovery["event_type"] == "unresolved"
    assert recovery["code"] == "E_PREVIOUS_FINALIZATION_UNRESOLVED"


def test_finalization_refs_reject_parent_traversal_before_terminal_write(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_committed",
        phase="finalization",
        code="FINALIZATION_COMMITTED",
    )
    with pytest.raises(ExecutionAttemptStoreError, match="E_TERMINAL_FINALIZATION_REF_INVALID"):
        store.create_terminal(
            run_id=RUN_ID,
            node_id=NODE_ID,
            status="passed",
            commit_manifest_ref="../commit.json",
            commit_manifest_hash=DIGEST,
            receipt_ref="reports/receipt.json",
            receipt_hash=DIGEST,
            pre_terminal_events_hash=DIGEST,
        )
    assert store.read_terminal(run_id=RUN_ID, node_id=NODE_ID) is None


def test_planned_committed_event_hash_equals_complete_pre_terminal_closure(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_started",
        phase="finalization",
        code="FINALIZATION_STARTED",
        transaction_id="FIN-ST013-003",
    )
    planned = {
        "event_type": "finalization_committed",
        "recorded_at": "2026-09-04T00:00:01Z",
        "phase": "finalization",
        "code": "FINALIZATION_COMMITTED",
        "transaction_id": "FIN-ST013-003",
    }
    expected = store.compute_pre_terminal_hash(
        run_id=RUN_ID, node_id=NODE_ID, additional_events=[planned]
    )
    store.append_event(
        run_id=RUN_ID,
        node_id=NODE_ID,
        event_type="finalization_committed",
        phase="finalization",
        code="FINALIZATION_COMMITTED",
        transaction_id="FIN-ST013-003",
        recorded_at=planned["recorded_at"],
    )
    assert store.compute_pre_terminal_hash(run_id=RUN_ID, node_id=NODE_ID) == expected


def test_attempt_local_failure_receipt_covers_missing_project_target(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    ref, receipt = store.write_finalization_failure_receipt(
        run_id=RUN_ID,
        node_id=NODE_ID,
        session_id="SESSION-ST013-001",
        transaction_id="FIN-ST013-FALLBACK",
        error_code="E_FINALIZATION_TARGET_REQUIRED",
        exception_class="FinalizationTransactionError",
        message_digest=DIGEST,
    )
    assert ref.endswith("/finalization-failure-receipt.json")
    assert receipt["status"] == "failed" and receipt["recovery_mode"] == "none"
    assert receipt["receipt_hash"].startswith("sha256:")
    duplicate_ref, duplicate = store.write_finalization_failure_receipt(
        run_id=RUN_ID,
        node_id=NODE_ID,
        session_id="SESSION-ST013-001",
        transaction_id="FIN-ST013-FALLBACK",
        error_code="E_FINALIZATION_TARGET_REQUIRED",
        exception_class="FinalizationTransactionError",
        message_digest=DIGEST,
    )
    assert duplicate_ref == ref and duplicate == receipt


def test_recovery_probe_distinguishes_commit_without_receipt(tmp_path) -> None:
    store = _store(tmp_path)
    _start_v2(store)
    summary = AttemptRecovery(store=store).scan_and_recover(
        finalization_probe=lambda _attempt: "commit_without_receipt"
    )
    assert summary["unresolved_attempts"][0]["finalization_state"] == "commit_without_receipt"
    assert store.read_terminal(run_id=RUN_ID, node_id=NODE_ID) is None
