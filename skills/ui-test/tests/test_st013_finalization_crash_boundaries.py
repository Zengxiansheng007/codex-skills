"""ST-013 使用真实子进程强退验证commit/receipt/terminal崩溃边界。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from scripts.ui_test_core.attempt_recovery import AttemptRecovery
from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
from scripts.ui_test_core.finalization_transaction import FinalizationTransaction


CHILD = textwrap.dedent(
    r"""
    import os
    import sys
    from pathlib import Path

    from scripts.ui_test_core.case_contracts import canonical_hash
    from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
    from scripts.ui_test_core.finalization_transaction import FinalizationTransaction

    root = Path(sys.argv[1])
    crash = sys.argv[2]
    run_id = "RUN-CRASH-001"
    node_id = "test_crash.py::test_node"
    session_id = "SESSION-CRASH-001"
    transaction_id = "FIN-CRASH-001"
    digest = "sha256:" + "a" * 64
    store = ExecutionAttemptStore(evidence_root=root / "evidence")
    store.create_attempt_start(
        run_id=run_id,
        node_id=node_id,
        case_id="CASE-CRASH",
        branch_id="primary",
        risk_level="r2-ui-write-test",
        execution_origin="pycharm",
        approval_source="pycharm-project-policy",
        stable_runner_digest=digest,
        project_config_digest=digest,
        schema_version="ui-test.execution-attempt.v2",
        session_id=session_id,
        finalization_mode="transaction-v1",
    )
    store.append_event(
        run_id=run_id,
        node_id=node_id,
        event_type="finalization_started",
        phase="finalization",
        code="FINALIZATION_STARTED",
        transaction_id=transaction_id,
    )
    pre_hash = store.compute_pre_terminal_hash(run_id=run_id, node_id=node_id)
    run_result = {
        "schema_version": "ui-test.run-result.v5",
        "transaction_id": transaction_id,
        "session_id": session_id,
        "run_id": run_id,
        "node_id": node_id,
        "case_id": "CASE-CRASH",
        "branch_id": "primary",
        "resolved_test_data_ref": "reports/resolved-test-data.json",
        "resolved_test_data_hash": digest,
        "execution_context_ref": "attempts/context.json",
        "execution_context_hash": digest,
        "attempt_ref": "attempts/attempt",
        "pre_terminal_events_hash": pre_hash,
        "approval_ref": "approval-record.json",
        "approval_hash": digest,
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
    }
    run_result["run_result_hash"] = canonical_hash(run_result)
    evidence = {
        "schema_version": "ui-test.evidence-index.v2",
        "run_id": run_id,
        "case_id": "CASE-CRASH",
        "branch_id": "primary",
        "run_result_ref": "objects/" + "0" * 64 + ".json",
        "run_result_hash": run_result["run_result_hash"],
        "resolved_test_data_ref": run_result["resolved_test_data_ref"],
        "resolved_test_data_hash": digest,
        "evidence_refs": [],
        "read_only_projection": True,
    }
    transaction = FinalizationTransaction(root / "run")

    def inject(stage):
        if crash == "after_commit" and stage == "after_commit":
            os._exit(23)

    transaction.commit(
        transaction_id=transaction_id,
        run_id=run_id,
        node_id=node_id,
        run_result=run_result,
        evidence_index=evidence,
        fault_injector=inject,
    )
    if crash == "after_receipt":
        os._exit(24)
    raise SystemExit(0)
    """
)


@pytest.mark.parametrize(
    ("crash_point", "exit_code", "expected_state"),
    [
        ("after_commit", 23, "commit_without_receipt"),
        ("after_receipt", 24, "receipt_without_terminal"),
    ],
)
def test_hard_exit_never_recovers_transaction_to_passed(
    tmp_path: Path, crash_point: str, exit_code: int, expected_state: str
) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", "-c", CHILD, str(tmp_path), crash_point],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == exit_code

    transaction = FinalizationTransaction(tmp_path / "run")
    commit = transaction.store.read_commit()
    receipt = transaction.store.read_receipt()
    assert commit is not None
    assert (receipt is None) is (crash_point == "after_commit")

    store = ExecutionAttemptStore(evidence_root=tmp_path / "evidence")

    def probe(_attempt):
        return (
            "receipt_without_terminal"
            if transaction.store.read_receipt() is not None
            else "commit_without_receipt"
        )

    recovery = AttemptRecovery(store=store).scan_and_recover(finalization_probe=probe)
    assert recovery["unresolved_attempts"][0]["finalization_state"] == expected_state
    assert store.read_terminal(run_id="RUN-CRASH-001", node_id="test_crash.py::test_node") is None
    recovery_file = next((tmp_path / "evidence" / "attempts").glob("*/recovery.jsonl"))
    record = json.loads(recovery_file.read_text(encoding="utf-8").splitlines()[0])
    assert record["recovered_from"] == expected_state

