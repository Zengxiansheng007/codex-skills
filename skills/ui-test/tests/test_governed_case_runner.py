import json

import pytest

from scripts.ui_test_core.execution_data_session import ExecutionDataError, ExecutionDataSession
from scripts.ui_test_core.execution_parameter_guard import ExecutionParameterGuard
from scripts.ui_test_core.failure_repair_store import FailureRepairEventStore
from scripts.ui_test_core.governed_case_runner import execute_governed_case
from tests.fixtures_v2 import compiled_v2


class FakeContext:
    def __init__(self, events):
        self.events = events

    def new_page(self):
        self.events.append("page")
        return object()

    def close(self):
        self.events.append("close")


class FakeDriver:
    def __init__(self, events):
        self.events = events

    def prepare(self, page, consume):
        self.events.append("prepare")
        consume("version")
        consume("login-account")
        return {"ready": True, "resolved_parameters": [{"parameter_id": "actual-title", "value": "sample", "derived_from": ["title-template"]}]}

    def submit_once(self, page, consume):
        self.events.append("submit")
        return {"write_state": "write_succeeded_verified"}


def _guard(tmp_path, compiled, data_path):
    session = ExecutionDataSession(
        run_id="RUN-GOVERNED",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    store = FailureRepairEventStore(tmp_path / "diagnostics", product_id="sample-product")
    return ExecutionParameterGuard(session, store, source_file_ref="cases/demo/tests/test-data.json")


def test_context_and_submit_follow_all_parameter_gates(tmp_path):
    data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(data_path)
    events = []
    result = execute_governed_case(
        guard=_guard(tmp_path, compiled, data_path),
        context_factory=lambda: (events.append("context") or FakeContext(events)),
        driver=FakeDriver(events),
        snapshot_path=tmp_path / "run" / "resolved-test-data.json",
    )
    assert events == ["context", "page", "prepare", "submit", "close"]
    assert result["business_write_count"] == 1


def test_drift_blocks_context_and_business_write(tmp_path):
    data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(data_path)
    document = json.loads(data_path.read_text(encoding="utf-8"))
    document["data_revision"] += 1
    data_path.write_text(json.dumps(document), encoding="utf-8")
    events = []
    with pytest.raises(ExecutionDataError, match="E_EXECUTION_TEST_DATA_DRIFT"):
        execute_governed_case(
            guard=_guard(tmp_path, compiled, data_path),
            context_factory=lambda: (events.append("context") or FakeContext(events)),
            driver=FakeDriver(events),
            snapshot_path=tmp_path / "run" / "resolved-test-data.json",
        )
    assert events == []
