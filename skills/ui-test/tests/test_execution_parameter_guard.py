import json

import pytest

from scripts.ui_test_core.execution_data_session import ExecutionDataError, ExecutionDataSession
from scripts.ui_test_core.execution_parameter_guard import ExecutionParameterGuard
from scripts.ui_test_core.failure_repair_store import FailureRepairEventStore
from tests.fixtures_v2 import compiled_v2


def _session(compiled, test_data_path, run_id="RUN-001"):
    return ExecutionDataSession(
        run_id=run_id,
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=test_data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only-credential",
        sequence_resolver=lambda key: 7,
    )


def test_session_seals_reference_safe_snapshot_and_one_shot_permit(tmp_path):
    test_data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(test_data_path)
    session = _session(compiled, test_data_path)
    session.start()
    assert session.consume("version") == 7
    assert session.consume("login-account") == "memory-only-credential"
    session.record_derived("actual-title", "0902123示例", derived_from=["title-template", "time-suffix-digits"])
    snapshot = session.seal_snapshot(tmp_path / "run" / "resolved-test-data.json", sealed_at="2026-09-02T01:00:00Z")
    persisted = json.dumps(snapshot, ensure_ascii=False)
    assert "memory-only-credential" not in persisted
    credential = next(item for item in snapshot["parameters"] if item["source_type"] == "credential")
    assert credential["reference_only"] is True and "value" not in credential
    sequence = next(item for item in snapshot["parameters"] if item["source_type"] == "sequence")
    assert sequence["value"] == 7
    assert next(item for item in snapshot["parameters"] if item["parameter_id"] == "actual-title")["value"] == "0902123示例"
    permit = session.authorize_business_write()
    permit.consume()
    with pytest.raises(ExecutionDataError, match="E_BUSINESS_WRITE_PERMIT_ALREADY_CONSUMED"):
        permit.consume()


def test_drift_records_unfinished_and_blocks_before_browser_context(tmp_path):
    test_data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(test_data_path)
    document = json.loads(test_data_path.read_text(encoding="utf-8"))
    document["parameters"]["content_template"] = "changed-{title}"
    test_data_path.write_text(json.dumps(document), encoding="utf-8")
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    guard = ExecutionParameterGuard(_session(compiled, test_data_path, "RUN-DRIFT"), store, source_file_ref="cases/demo/tests/test-data.json")
    browser_context_created = False
    with pytest.raises(ExecutionDataError, match="E_EXECUTION_TEST_DATA_DRIFT"):
        guard.start()
    assert browser_context_created is False
    unfinished = json.loads((tmp_path / "diagnostics" / "unfinished-repairs.json").read_text(encoding="utf-8"))
    assert len(unfinished["items"]) == 1
    assert unfinished["items"][0]["category"] == "parameter-drift"
    assert list((tmp_path / "diagnostics" / "failure-repair-history").glob("*.jsonl"))


def test_snapshot_is_required_before_business_write(tmp_path):
    test_data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(test_data_path)
    session = _session(compiled, test_data_path)
    session.start()
    with pytest.raises(ExecutionDataError, match="E_EXECUTION_SNAPSHOT_REQUIRED"):
        session.authorize_business_write()
