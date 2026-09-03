import copy
import json

from scripts.ui_test_core.release_verifier import verify_release
from tests.fixtures_v2 import compiled_v2


def _write_release(path, compiled):
    path.mkdir(parents=True)
    for name, content in {**compiled["outputs"], "manifest.json": compiled["manifest"]}.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def test_valid_release_and_current_input_drift_are_independent(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    release = tmp_path / "release"
    _write_release(release, compiled)
    state = verify_release(release, current_identity=compiled["identity"])
    assert state["release_integrity"] == "valid"
    assert state["input_sync"] == "in_sync"
    assert state["execution_gate"] == "ready"
    changed = copy.deepcopy(compiled["identity"])
    changed["test_data_hash"] = "sha256:" + "0" * 64
    drift = verify_release(release, current_identity=changed)
    assert drift["release_integrity"] == "valid"
    assert drift["input_sync"] == "out_of_sync"
    assert drift["execution_gate"] == "blocked"
    assert any(item["code"] == "E_CURRENT_INPUT_DRIFT" for item in drift["issues"])


def test_manifest_drives_missing_extra_and_hash_checks(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    release = tmp_path / "release"
    _write_release(release, compiled)
    (release / "human.md").unlink()
    (release / "extra.json").write_text("{}", encoding="utf-8")
    state = verify_release(release, current_identity=compiled["identity"])
    codes = {item["code"] for item in state["issues"]}
    assert "E_RELEASE_ARTIFACT_MISSING" in codes
    assert "E_RELEASE_ARTIFACT_UNDECLARED" in codes
    assert state["release_integrity"] == "manual_drift"


def test_receipt_identity_mismatch_is_invalid(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    release = tmp_path / "release"
    _write_release(release, compiled)
    receipt_path = release / "compile-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["branch_id"] = "other"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    state = verify_release(release, current_identity=compiled["identity"])
    assert state["release_integrity"] == "invalid"
    assert any(item["code"] == "E_RELEASE_RECEIPT_IDENTITY_MISMATCH" for item in state["issues"])

