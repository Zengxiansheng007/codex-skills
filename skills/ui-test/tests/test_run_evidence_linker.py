import copy

import pytest

from scripts.ui_test_core.execution_data_session import ExecutionDataSession
from scripts.ui_test_core.run_evidence_linker import (
    RunEvidenceLinkError,
    bind_run_result_v3,
    build_evidence_index_v2,
    build_run_result_v4,
    build_run_result_v5,
    verify_run_evidence_links,
    verify_run_result_v4_links,
    verify_run_result_v5_links,
)
from tests.fixtures_v2 import compiled_v2


def test_snapshot_run_result_and_evidence_are_hash_bound(tmp_path):
    data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(data_path)
    run_root = tmp_path / "runs" / "RUN-001"
    session = ExecutionDataSession(
        run_id="RUN-001",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    session.start()
    session.consume("version")
    snapshot_path = run_root / "resolved-test-data.json"
    session.seal_snapshot(snapshot_path, sealed_at="2026-09-02T01:00:00Z")
    base = {
        "run_id": "RUN-001",
        "case_id": "DEMO-CASE-A",
        "branch_id": "primary",
        "overall_status": "passed",
        "evidence_refs": ["steps/S-001.json"]
    }
    result = bind_run_result_v3(
        base, run_root=run_root, snapshot_path=snapshot_path, legacy_fixture=True
    )
    evidence = build_evidence_index_v2(result, run_result_ref="run-result.json")
    assert verify_run_evidence_links(result, evidence, run_root=run_root) == []
    tampered = copy.deepcopy(evidence)
    tampered["resolved_test_data_hash"] = "sha256:" + "0" * 64
    assert any("resolved_test_data_hash" in item for item in verify_run_evidence_links(result, tampered, run_root=run_root))


def test_legacy_v3_builder_is_read_only_without_explicit_fixture_mode(tmp_path):
    with pytest.raises(RunEvidenceLinkError, match="E_RUN_RESULT_V3_HISTORICAL_READ_ONLY"):
        bind_run_result_v3({}, run_root=tmp_path, snapshot_path=tmp_path / "missing.json")


def test_v4_binds_snapshot_context_attempt_approval_and_own_hash(tmp_path):
    data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(data_path)
    run_root = tmp_path / "runs" / "RUN-V4"
    session = ExecutionDataSession(
        run_id="RUN-V4",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    session.start()
    session.consume("version")
    snapshot_path = run_root / "reports" / "resolved-test-data.json"
    session.seal_snapshot(snapshot_path, sealed_at="2026-09-04T00:00:00Z")
    digest = "sha256:" + "a" * 64
    result = build_run_result_v4(
        run_root=run_root,
        snapshot_path=snapshot_path,
        execution_context_ref="attempts/a/execution-context.json",
        execution_context_hash=digest,
        attempt_ref="attempts/a",
        attempt_hash=digest,
        approval_ref="approval-record.json",
        approval_hash=digest,
        run_id="RUN-V4",
        node_id="test_demo.py::test_v4",
        case_id="DEMO-CASE-A",
        branch_id="primary",
        overall_status="passed",
        write_state="write_succeeded_verified",
        submit_count=1,
        layered_status={name: "passed" for name in ("unit", "collection", "release_verification", "qualification", "pycharm_integration", "human_r2")},
        legacy_fixture=True,
    )
    assert verify_run_result_v4_links(
        result,
        run_root=run_root,
        expected_execution_context_ref="attempts/a/execution-context.json",
        expected_execution_context_hash=digest,
        expected_attempt_ref="attempts/a",
        expected_attempt_hash=digest,
        expected_approval_ref="approval-record.json",
        expected_approval_hash=digest,
    ) == []
    tampered = copy.deepcopy(result)
    tampered["attempt_hash"] = "sha256:" + "b" * 64
    assert "E_RUN_RESULT_HASH_MISMATCH" in verify_run_result_v4_links(tampered, run_root=run_root)
    escaped = copy.deepcopy(result)
    escaped["execution_context_ref"] = "../outside.json"
    assert "E_RUN_RESULT_REF_ESCAPE:execution_context_ref" in verify_run_result_v4_links(escaped, run_root=run_root)


def test_legacy_v4_builder_is_read_only_without_explicit_fixture_mode(tmp_path):
    with pytest.raises(RunEvidenceLinkError, match="E_RUN_RESULT_V4_HISTORICAL_READ_ONLY"):
        build_run_result_v4(
            run_root=tmp_path,
            snapshot_path=tmp_path / "missing.json",
            execution_context_ref="attempts/a/context.json",
            execution_context_hash="sha256:" + "a" * 64,
            attempt_ref="attempts/a",
            attempt_hash="sha256:" + "a" * 64,
            approval_ref="approval.json",
            approval_hash="sha256:" + "a" * 64,
            run_id="RUN",
            node_id="node",
            case_id="CASE",
            branch_id="branch",
            overall_status="failed",
            write_state="write_failed",
            submit_count=0,
            layered_status={},
        )


def test_invalid_snapshot_ref_is_rejected_before_any_read(tmp_path, monkeypatch):
    run_root, run_result, _digest, _phases = _build_v5(tmp_path)
    run_result["resolved_test_data_ref"] = "../outside.json"

    def forbidden_read(_path):
        raise AssertionError("invalid ref must not be opened")

    monkeypatch.setattr(
        "scripts.ui_test_core.run_evidence_linker._verified_snapshot", forbidden_read
    )
    issues = verify_run_result_v5_links(run_result, run_root=run_root)
    assert "E_RUN_RESULT_REF_ESCAPE:resolved_test_data_ref" in issues


def _build_v5(tmp_path):
    data_path = tmp_path / "test-data-v5.json"
    compiled, _ = compiled_v2(data_path)
    run_root = tmp_path / "runs" / "RUN-V5"
    session = ExecutionDataSession(
        run_id="RUN-V5",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    session.start()
    session.consume("version")
    snapshot_path = run_root / "reports" / "resolved-test-data.json"
    session.seal_snapshot(snapshot_path, sealed_at="2026-09-04T13:00:00Z")
    digest = "sha256:" + "c" * 64
    phases = {"setup": "passed", "call": "passed", "teardown": "passed"}
    result = build_run_result_v5(
        run_root=run_root,
        snapshot_path=snapshot_path,
        transaction_id="TX-V5-001",
        session_id="SESSION-V5-001",
        execution_context_ref="attempts/a/execution-context.json",
        execution_context_hash=digest,
        attempt_ref="attempts/a",
        pre_terminal_events_hash=digest,
        approval_ref="approval-record.json",
        approval_hash=digest,
        run_id="RUN-V5",
        node_id="test_demo.py::test_v5",
        case_id="DEMO-CASE-A",
        branch_id="primary",
        pytest_phase_status=phases,
        overall_status="passed",
        write_state="write_succeeded_verified",
        submit_count=1,
    )
    return run_root, result, digest, phases


def test_v5_binds_transaction_session_phase_and_evidence_without_self_attestation(tmp_path):
    run_root, result, digest, phases = _build_v5(tmp_path)

    assert "pycharm_integration" not in result
    assert "human_r2" not in result
    assert "layered_status" not in result
    assert verify_run_result_v5_links(
        result,
        run_root=run_root,
        expected_transaction_id="TX-V5-001",
        expected_session_id="SESSION-V5-001",
        expected_run_id="RUN-V5",
        expected_node_id="test_demo.py::test_v5",
        expected_execution_context_ref="attempts/a/execution-context.json",
        expected_execution_context_hash=digest,
        expected_attempt_ref="attempts/a",
        expected_pre_terminal_events_hash=digest,
        expected_approval_ref="approval-record.json",
        expected_approval_hash=digest,
        expected_pytest_phase_status=phases,
    ) == []

    evidence = build_evidence_index_v2(result, run_result_ref="finalization/objects/run-result.json")
    assert verify_run_evidence_links(result, evidence, run_root=run_root) == []


def test_v5_verifier_rejects_hash_drift_ref_escape_and_self_attestation(tmp_path):
    run_root, result, digest, _ = _build_v5(tmp_path)
    tampered = copy.deepcopy(result)
    tampered["pre_terminal_events_hash"] = "sha256:" + "d" * 64
    issues = verify_run_result_v5_links(
        tampered,
        run_root=run_root,
        expected_pre_terminal_events_hash=digest,
    )
    assert "E_PRE_TERMINAL_EVENTS_HASH_MISMATCH" in issues
    assert "E_RUN_RESULT_HASH_MISMATCH" in issues

    escaped = copy.deepcopy(result)
    escaped["attempt_ref"] = "../outside"
    assert "E_RUN_RESULT_REF_ESCAPE:attempt_ref" in verify_run_result_v5_links(escaped, run_root=run_root)

    self_attested = copy.deepcopy(result)
    self_attested["pycharm_integration"] = "passed"
    self_issues = verify_run_result_v5_links(self_attested, run_root=run_root)
    assert "E_RUN_RESULT_V5_SCHEMA_INVALID" in self_issues
    assert "E_RUN_RESULT_V5_SELF_ATTESTATION_FORBIDDEN:pycharm_integration" in self_issues


def test_v5_builder_rejects_passed_when_any_pytest_phase_is_not_passed(tmp_path):
    data_path = tmp_path / "test-data-invalid-v5.json"
    compiled, _ = compiled_v2(data_path)
    run_root = tmp_path / "runs" / "RUN-V5-INVALID"
    session = ExecutionDataSession(
        run_id="RUN-V5-INVALID",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    session.start()
    session.consume("version")
    snapshot_path = run_root / "reports" / "resolved-test-data.json"
    session.seal_snapshot(snapshot_path, sealed_at="2026-09-04T13:00:00Z")
    digest = "sha256:" + "c" * 64

    with pytest.raises(RunEvidenceLinkError, match="E_RUN_RESULT_V5_PASSED_WITHOUT_COMPLETE_EVIDENCE"):
        build_run_result_v5(
            run_root=run_root,
            snapshot_path=snapshot_path,
            transaction_id="TX-V5-INVALID",
            session_id="SESSION-V5-INVALID",
            execution_context_ref="attempts/a/execution-context.json",
            execution_context_hash=digest,
            attempt_ref="attempts/a",
            pre_terminal_events_hash=digest,
            approval_ref="approval-record.json",
            approval_hash=digest,
            run_id="RUN-V5-INVALID",
            node_id="test_demo.py::test_invalid_v5",
            case_id="DEMO-CASE-A",
            branch_id="primary",
            pytest_phase_status={"setup": "passed", "call": "passed", "teardown": "failed"},
            overall_status="passed",
            write_state="write_succeeded_verified",
            submit_count=1,
        )
