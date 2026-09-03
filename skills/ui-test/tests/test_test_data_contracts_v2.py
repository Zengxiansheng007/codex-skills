import json

import pytest

from scripts.ui_test_core.strict_json import StrictJsonError, loads_strict
from scripts.ui_test_core.test_data_contracts import (
    TestDataError as _TestDataError,
    load_test_data,
    resolve_json_pointer,
    resolve_parameter_manifest,
)
from tests.fixtures_v2 import make_test_data_document, write_test_data


def test_strict_json_rejects_duplicate_keys_and_non_finite_numbers():
    with pytest.raises(StrictJsonError, match="E_JSON_DUPLICATE_KEY"):
        loads_strict('{"a":1,"a":2}')
    with pytest.raises(StrictJsonError, match="E_JSON_NON_FINITE"):
        loads_strict('{"a":NaN}')


def test_rfc6901_vectors_and_invalid_escape():
    document = {"": 0, "a/b": 1, "m~n": 2, "array": ["zero", "one"]}
    assert resolve_json_pointer(document, "") == document
    assert resolve_json_pointer(document, "/") == 0
    assert resolve_json_pointer(document, "/a~1b") == 1
    assert resolve_json_pointer(document, "/m~0n") == 2
    assert resolve_json_pointer(document, "/array/1") == "one"
    with pytest.raises(_TestDataError, match="E_JSON_POINTER_ESCAPE_INVALID"):
        resolve_json_pointer(document, "/bad~2key")


def test_test_data_hash_ignores_whitespace_and_key_order(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    document = make_test_data_document()
    first.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    second.write_text(json.dumps(dict(reversed(list(document.items()))), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    one = load_test_data(first, case_id="DEMO-CASE-A", branch_id="primary")
    two = load_test_data(second, case_id="DEMO-CASE-A", branch_id="primary")
    assert one["test_data_hash"] == two["test_data_hash"]


def test_test_data_rejects_scope_and_prohibited_credential_keys(tmp_path):
    path = tmp_path / "test-data.json"
    document = make_test_data_document()
    document["parameters"]["account_password"] = "not-persisted"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(_TestDataError, match="E_TEST_DATA_PROHIBITED_KEY"):
        load_test_data(path, case_id="DEMO-CASE-A", branch_id="primary")
    clean = write_test_data(path, make_test_data_document())
    assert clean["case_id"] == "DEMO-CASE-A"
    with pytest.raises(_TestDataError, match="E_TEST_DATA_SCOPE_MISMATCH"):
        load_test_data(path, case_id="OTHER", branch_id="primary")


def test_manifest_expands_only_business_and_ordinary_runtime_values(tmp_path):
    loaded = write_test_data(tmp_path / "test-data.json")
    manifest = resolve_parameter_manifest(
        parameter_bindings=[
            {"parameter_id": "business", "label": "标题", "ref": "test-data:/parameters/title_template"},
            {"parameter_id": "runtime", "label": "主机", "ref": "value:SERVICE_HOST"},
            {"parameter_id": "credential", "label": "账号", "ref": "credential:shared-login"},
            {"parameter_id": "sequence", "label": "版本", "ref": "sequence:popup-version"}
        ],
        test_data=loaded,
        runtime_values={"SERVICE_HOST": {"value": "sample.internal", "classification": "ordinary", "sensitive": False}},
        credential_keys={"shared-login"},
        sequence_keys={"popup-version"}
    )
    by_id = {item["parameter_id"]: item for item in manifest["parameters"]}
    assert by_id["business"]["value"] == "{date_mmdd}{time_suffix}{record_type}"
    assert by_id["runtime"]["value"] == "sample.internal"
    assert "value" not in by_id["credential"] and by_id["credential"]["reference_only"] is True
    assert "value" not in by_id["sequence"] and by_id["sequence"]["reference_only"] is True


def test_sensitive_runtime_value_cannot_expand(tmp_path):
    loaded = write_test_data(tmp_path / "test-data.json")
    with pytest.raises(_TestDataError, match="E_RUNTIME_VALUE_NOT_EXPANDABLE"):
        resolve_parameter_manifest(
            parameter_bindings=[{"parameter_id": "x", "label": "X", "ref": "value:X"}],
            test_data=loaded,
            runtime_values={"X": {"value": "hidden", "classification": "security-sensitive", "sensitive": True}}
        )
