import ast
import copy

from scripts.ui_test_core.case_contracts import canonical_hash, validate_document
from scripts.ui_test_core.compiler_v2 import compile_case_v2
from tests.fixtures_v2 import compiled_v2, source_case_v2, write_test_data


def test_compiler_v2_is_deterministic_and_manifest_complete(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    assert validate_document(compiled["manifest"], "case-manifest-v2.schema.json") == []
    assert set(compiled["manifest"]["artifacts"]) == set(compiled["outputs"])
    assert {"source-case.json", "test-data.json"}.issubset(compiled["outputs"])
    assert "manifest.json" not in compiled["manifest"]["artifacts"]
    for name, content in compiled["outputs"].items():
        assert compiled["manifest"]["artifacts"][name] == canonical_hash(content)
    ast.parse(compiled["outputs"]["playwright-test.py"])
    namespace = {}
    exec(compile(compiled["outputs"]["playwright-test.py"], "<generated>", "exec"), namespace)
    assert "CASE_PARAMETER_MANIFEST" in namespace
    assert "pytestmark" in namespace
    generated = compiled["outputs"]["playwright-test.py"]
    assert "pytest.mark.p0" in generated and "pytest.mark.r2" in generated
    assert "pytest.mark.case_id" in generated and "pytest.mark.branch_id" in generated
    calls = []
    runtime = type("Runtime", (), {"execute_case": lambda self, **kwargs: calls.append(kwargs)})()
    generated_test = next(value for key, value in namespace.items() if key.startswith("test_") and callable(value))
    generated_test(runtime)
    assert calls == [{"case_id": "DEMO-CASE-A", "branch_id": "primary", "parameter_manifest": compiled["parameter_manifest"]}]


def test_all_projections_share_parameter_manifest_and_references_only(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    manifest = compiled["parameter_manifest"]
    assert compiled["outputs"]["case-parameter-manifest.json"] == manifest
    assert compiled["outputs"]["midscene.json"]["metadata"]["parameter_manifest_hash"] == manifest["parameter_manifest_hash"]
    assert manifest["parameters"][0]["parameter_id"] in compiled["outputs"]["playwright-test.py"]
    by_type = {item["source_type"]: item for item in manifest["parameters"] if item["source_type"] in {"credential", "sequence"}}
    assert "value" not in by_type["credential"]
    assert "value" not in by_type["sequence"]


def test_compiler_does_not_mutate_inputs_and_semantic_change_changes_build(tmp_path):
    source = source_case_v2()
    loaded = write_test_data(tmp_path / "test-data.json")
    before_source = copy.deepcopy(source)
    before_data = copy.deepcopy(loaded)
    common = {
        "dependency_assets": {key: {"version": 1} for key in source["dependency_refs"]},
        "config_fingerprint": "sha256:" + "1" * 64,
        "runtime_values": {"SERVICE_HOST": {"value": "sample.internal", "classification": "ordinary", "sensitive": False}},
        "credential_keys": {"shared-login"},
        "sequence_keys": {"popup-version"}
    }
    first = compile_case_v2(source_case=source, test_data=loaded, **common)
    assert source == before_source and loaded == before_data
    changed = copy.deepcopy(loaded)
    changed["parameters"]["content_template"] = "changed-{title}"
    changed["test_data_hash"] = canonical_hash({key: value for key, value in changed.items() if key not in {"test_data_hash", "source_path"}})
    second = compile_case_v2(source_case=source, test_data=changed, **common)
    assert first["manifest"]["build_fingerprint"] != second["manifest"]["build_fingerprint"]
