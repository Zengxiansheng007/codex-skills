import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.ui_test_core.failure_repair_store import (
    FailureRepairEventStore,
    FailureRepairStoreError,
    make_event,
)


def _failure(key="failure-1"):
    return make_event(
        event_type="sync-required",
        idempotency_key=key,
        product_id="sample-product",
        case_id="DEMO-CASE-A",
        branch_id="primary",
        category="parameter-drift",
        summary="E_EXECUTION_TEST_DATA_DRIFT",
        source_files=["cases/demo/tests/test-data.json"],
        occurred_at=datetime(2026, 9, 2, 9, 0, tzinfo=timezone(timedelta(hours=8))),
        event_id=f"evt-{key}",
    )


def _repair(failure, key="repair-1"):
    event = make_event(
        event_type="sync-completed",
        idempotency_key=key,
        product_id="sample-product",
        case_id="DEMO-CASE-A",
        branch_id="primary",
        category="parameter-drift",
        summary="参数同步和发布验证已通过",
        source_files=["cases/demo/tests/test-data.json"],
        evidence=[
            {"type": "parameter-hash", "ref": "evidence/hash.json", "sha256": "sha256:" + "1" * 64},
            {"type": "sync-result", "ref": "evidence/sync.json", "sha256": "sha256:" + "2" * 64},
            {"type": "release-verification", "ref": "evidence/verify.json", "sha256": "sha256:" + "3" * 64}
        ],
        occurred_at=datetime(2026, 9, 2, 10, 0, tzinfo=timezone(timedelta(hours=8))),
        event_id=f"evt-{key}",
    )
    assert event["problem_fingerprint"] == failure["problem_fingerprint"]
    return event


def test_no_event_creates_no_daily_file(tmp_path):
    FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    assert not (tmp_path / "diagnostics" / "failure-repair-history").exists()


def test_failure_append_idempotency_and_repair_projection(tmp_path):
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    failure = _failure()
    assert store.append(failure)["status"] == "appended"
    assert store.append(failure)["status"] == "duplicate"
    unfinished_path = tmp_path / "diagnostics" / "unfinished-repairs.json"
    assert len(json.loads(unfinished_path.read_text(encoding="utf-8"))["items"]) == 1
    assert store.append(_repair(failure))["status"] == "appended"
    assert json.loads(unfinished_path.read_text(encoding="utf-8"))["items"] == []


def test_repair_without_complete_typed_evidence_is_rejected(tmp_path):
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    failure = _failure()
    store.append(failure)
    repair = _repair(failure)
    repair["evidence"] = repair["evidence"][:1]
    with pytest.raises(FailureRepairStoreError, match="E_REPAIR_EVIDENCE_INCOMPLETE"):
        store.append(repair)


def test_same_idempotency_recovers_after_append_failure(tmp_path):
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    failure = _failure("recover")
    with pytest.raises(FailureRepairStoreError, match="E_HISTORY_INJECTED_AFTER_APPEND"):
        store.append(failure, fail_after="append")
    recovered = store.append(failure)
    assert recovered["status"] == "duplicate"
    assert json.loads((tmp_path / "diagnostics" / "failure-repair-history" / "index.json").read_text(encoding="utf-8"))["event_count"] == 1


def test_invalid_existing_jsonl_blocks_append(tmp_path):
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    store.append(_failure())
    history = tmp_path / "diagnostics" / "failure-repair-history" / "2026-09-02.jsonl"
    with history.open("ab") as stream:
        stream.write(b"{invalid}\n")
    with pytest.raises(FailureRepairStoreError, match="E_HISTORY_JSONL_INVALID"):
        store.append(_failure("next"))


def test_china_log_date_is_derived_before_file_selection():
    event = make_event(
        event_type="failure-detected",
        idempotency_key="timezone",
        product_id="sample-product",
        case_id="DEMO-CASE-A",
        branch_id="primary",
        category="test-failure",
        summary="failed",
        occurred_at=datetime.fromisoformat("2026-09-01T17:30:00+00:00"),
    )
    assert event["log_date"] == "2026-09-02"
