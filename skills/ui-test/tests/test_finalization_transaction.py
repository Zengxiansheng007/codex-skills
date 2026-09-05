import copy

import pytest

from scripts.ui_test_core.case_contracts import canonical_hash
from scripts.ui_test_core.finalization_store import FinalizationStoreError
from scripts.ui_test_core.finalization_transaction import (
    FinalizationTransaction,
    FinalizationTransactionError,
    record_finalization_failure,
)


FIXED_TIME = "2026-09-04T13:30:00+00:00"
HASH = "sha256:" + "1" * 64


def _candidate(*, findings=None):
    run_result = {
        "schema_version": "ui-test.run-result.v5",
        "transaction_id": "TX-ST013-001",
        "session_id": "SESSION-ST013-001",
        "run_id": "RUN-ST013-001",
        "node_id": "tests/test_demo.py::test_case",
        "case_id": "CASE-ST013",
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
        "evidence_refs": [],
        "conflicts": [],
        "findings": list(findings or []),
        "retained_test_data": [],
        "cleanup_status": "not_planned_this_release",
        "business_cleanup_attempted": False,
    }
    run_result["run_result_hash"] = canonical_hash(run_result)
    evidence_index = {
        "schema_version": "ui-test.evidence-index.v2",
        "run_id": run_result["run_id"],
        "case_id": run_result["case_id"],
        "branch_id": run_result["branch_id"],
        "run_result_ref": "uncommitted/run-result.json",
        "run_result_hash": run_result["run_result_hash"],
        "resolved_test_data_ref": run_result["resolved_test_data_ref"],
        "resolved_test_data_hash": run_result["resolved_test_data_hash"],
        "evidence_refs": [],
        "read_only_projection": True,
    }
    return run_result, evidence_index


def _validator(run_result, evidence_index, run_root):
    # 附加 validator 用于证明调用点可继续执行项目级闭包校验。
    assert run_root.name.startswith("RUN-") or "事务" in str(run_root)
    assert evidence_index["run_result_hash"] == run_result["run_result_hash"]
    return []


def _transaction(tmp_path, *, with_validator=True):
    return FinalizationTransaction(
        tmp_path / "长路径-事务" / "RUN-ST013-001",
        candidate_validator=_validator if with_validator else None,
        clock=lambda: FIXED_TIME,
    )


def _raise_at(target):
    def inject(stage):
        if stage == target:
            raise OSError("injected")

    return inject


def _commit(transaction, run_result, evidence_index, **kwargs):
    return transaction.commit(
        transaction_id="TX-ST013-001",
        run_id="RUN-ST013-001",
        node_id="tests/test_demo.py::test_case",
        run_result=run_result,
        evidence_index=evidence_index,
        recorded_at=FIXED_TIME,
        **kwargs,
    )


def test_commit_publishes_content_addressed_objects_one_manifest_and_receipt(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    original_evidence = copy.deepcopy(evidence_index)

    outcome = _commit(transaction, run_result, evidence_index)

    assert outcome["status"] == "committed"
    assert transaction.store.commit_path.is_file()
    assert transaction.store.receipt_path.is_file()
    assert len(list(transaction.store.blob_root.glob("*.json"))) == 2
    assert list(transaction.store.root.glob("*commit*.json")) == [transaction.store.commit_path]
    assert outcome["manifest"]["atomic_publish"] is True
    assert outcome["manifest"]["run_result_ref"].startswith("objects/")
    assert outcome["receipt"]["recovery_mode"] == "none"
    assert evidence_index == original_evidence
    committed = transaction.read_committed()
    assert committed is not None
    assert committed["run_result"] == run_result
    assert committed["evidence_index"]["run_result_ref"] == outcome["manifest"]["run_result_ref"]


@pytest.mark.parametrize(
    "fault_stage,expected_objects",
    [
        ("after_stage_run_result", 0),
        ("after_stage_evidence_index", 0),
        ("after_install_run_result", 1),
        ("after_install_evidence_index", 2),
        ("before_commit", 2),
    ],
)
def test_precommit_faults_never_publish_an_acceptable_partial_result(tmp_path, fault_stage, expected_objects):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()

    with pytest.raises(OSError, match="injected"):
        _commit(transaction, run_result, evidence_index, fault_injector=_raise_at(fault_stage))

    assert not transaction.store.commit_path.exists()
    assert not transaction.store.receipt_path.exists()
    assert len(list(transaction.store.blob_root.glob("*.json"))) == expected_objects
    assert transaction.read_committed() is None


def test_commit_without_receipt_is_never_recovered_to_passed(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()

    with pytest.raises(OSError, match="injected"):
        _commit(transaction, run_result, evidence_index, fault_injector=_raise_at("after_commit"))

    assert transaction.store.commit_path.is_file()
    assert not transaction.store.receipt_path.exists()
    assert transaction.read_committed() is None

    recovered = _commit(transaction, run_result, evidence_index)
    assert recovered["status"] == "recovery-blocked"
    assert recovered["receipt"]["status"] == "failed"
    assert recovered["receipt"]["recovery_mode"] == "post-run"
    assert recovered["receipt"]["error_code"] == "E_FINALIZATION_POST_RUN_RECOVERY_REQUIRED"
    assert transaction.read_committed() is None
    assert _commit(transaction, run_result, evidence_index)["receipt"] == recovered["receipt"]


def test_identical_retry_is_idempotent_but_changed_candidate_conflicts(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    first = _commit(transaction, run_result, evidence_index)
    object_names = sorted(path.name for path in transaction.store.blob_root.glob("*.json"))

    duplicate = _commit(transaction, run_result, evidence_index)
    assert duplicate["status"] == "duplicate"
    assert duplicate["manifest"] == first["manifest"]
    assert duplicate["receipt"] == first["receipt"]
    assert sorted(path.name for path in transaction.store.blob_root.glob("*.json")) == object_names

    changed_run, changed_evidence = _candidate(findings=["changed"])
    with pytest.raises(FinalizationTransactionError, match="E_FINALIZATION_COMMIT_CONFLICT"):
        _commit(transaction, changed_run, changed_evidence)


def test_tampered_object_is_rejected_even_when_manifest_and_receipt_exist(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    outcome = _commit(transaction, run_result, evidence_index)
    run_ref = outcome["manifest"]["run_result_ref"]
    run_object = transaction.store.root.joinpath(*run_ref.split("/"))
    run_object.write_bytes(b'{"tampered":true}')

    with pytest.raises(FinalizationStoreError, match="E_FINALIZATION_BLOB_HASH_MISMATCH"):
        transaction.read_committed()


def test_invalid_candidate_fails_before_any_transaction_artifact(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    run_result["findings"] = ["tampered-without-rehash"]

    with pytest.raises(FinalizationTransactionError, match="E_FINALIZATION_RUN_RESULT_HASH_MISMATCH"):
        _commit(transaction, run_result, evidence_index)

    assert not transaction.store.root.exists()


def test_builtin_versioned_schema_validation_does_not_require_project_callback(tmp_path):
    transaction = _transaction(tmp_path, with_validator=False)
    run_result, evidence_index = _candidate()

    assert _commit(transaction, run_result, evidence_index)["status"] == "committed"


@pytest.mark.parametrize("schema_version", ["ui-test.run-result.v3", "ui-test.run-result.v4"])
def test_legacy_run_results_remain_read_only_and_cannot_enter_new_transaction(tmp_path, schema_version):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    run_result["schema_version"] = schema_version
    run_result["run_result_hash"] = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
    evidence_index["run_result_hash"] = run_result["run_result_hash"]

    with pytest.raises(FinalizationTransactionError, match="E_FINALIZATION_LEGACY_RUN_RESULT_READ_ONLY"):
        _commit(transaction, run_result, evidence_index)

    assert not transaction.store.root.exists()


def test_orphan_atomic_temp_file_is_never_treated_as_commit(tmp_path):
    transaction = _transaction(tmp_path)
    transaction.store.root.mkdir(parents=True)
    orphan = transaction.store.root / ".finalization-commit.json.interrupted.tmp"
    orphan.write_bytes(b'{"partial":')

    assert transaction.read_committed() is None
    assert not transaction.store.commit_path.exists()


def test_record_failure_is_atomic_idempotent_and_blocks_later_commit(tmp_path):
    transaction = _transaction(tmp_path)
    run_result, evidence_index = _candidate()
    message_digest = canonical_hash({"redacted": "failure-summary"})

    first = transaction.record_failure(
        transaction_id="TX-ST013-001",
        session_id="SESSION-ST013-001",
        run_id="RUN-ST013-001",
        node_id="tests/test_demo.py::test_case",
        error_code="E_FINALIZER_FAILED",
        exception_class="RuntimeError",
        message_digest=message_digest,
        recorded_at=FIXED_TIME,
    )

    assert first["status"] == "failed"
    assert first["receipt"]["status"] == "failed"
    assert first["receipt"]["message_digest"] == message_digest
    assert transaction.store.receipt_path.is_file()
    assert not transaction.store.commit_path.exists()
    assert transaction.read_committed() is None

    duplicate = transaction.record_failure(
        transaction_id="TX-ST013-001",
        session_id="SESSION-ST013-001",
        run_id="RUN-ST013-001",
        node_id="tests/test_demo.py::test_case",
        error_code="E_FINALIZER_FAILED",
        exception_class="RuntimeError",
        message_digest=message_digest,
        recorded_at="2026-09-04T13:31:00+00:00",
    )
    assert duplicate == {"status": "duplicate", "receipt": first["receipt"]}

    with pytest.raises(FinalizationTransactionError, match="E_FINALIZATION_RECEIPT_WITHOUT_COMMIT"):
        _commit(transaction, run_result, evidence_index)


def test_record_failure_conflicts_fail_closed_and_convenience_api_matches(tmp_path):
    run_root = tmp_path / "RUN-ST013-001"
    first = record_finalization_failure(
        run_root=run_root,
        transaction_id="TX-ST013-001",
        session_id="SESSION-ST013-001",
        run_id="RUN-ST013-001",
        node_id="tests/test_demo.py::test_case",
        error_code="E_FINALIZER_FAILED",
        exception_class="RuntimeError",
        message_digest=canonical_hash({"redacted": "first"}),
        recorded_at=FIXED_TIME,
    )
    assert first["status"] == "failed"

    with pytest.raises(FinalizationTransactionError, match="E_FINALIZATION_RECEIPT_CONFLICT"):
        record_finalization_failure(
            run_root=run_root,
            transaction_id="TX-ST013-001",
            session_id="SESSION-ST013-001",
            run_id="RUN-ST013-001",
            node_id="tests/test_demo.py::test_case",
            error_code="E_FINALIZER_FAILED",
            exception_class="OSError",
            message_digest=canonical_hash({"redacted": "second"}),
            recorded_at=FIXED_TIME,
        )
