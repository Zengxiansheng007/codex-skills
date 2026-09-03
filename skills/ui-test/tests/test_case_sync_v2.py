import copy

from scripts.ui_test_core.case_sync import apply_sync_plan, dry_run
from scripts.ui_test_core.release_verifier import verify_release
from tests.fixtures_v2 import compiled_v2


def test_dry_run_is_write_free_and_apply_is_idempotent(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    target = tmp_path / "formal-copy"
    plan = dry_run(compiled, target, operation_id="op-one")
    assert not target.exists()
    result = apply_sync_plan(plan, lambda: copy.deepcopy(compiled), target)
    assert result["status"] == "applied"
    assert result["active_build"] == compiled["manifest"]["build_fingerprint"]
    state = verify_release(result["release_path"], current_identity=compiled["identity"])
    assert state["release_integrity"] == "valid"
    second_plan = dry_run(compiled, target, operation_id="op-two")
    second = apply_sync_plan(second_plan, lambda: copy.deepcopy(compiled), target)
    assert second["status"] == "in_sync" and second["no_op"] is True


def test_apply_rejects_plan_tampering_and_input_change(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    target = tmp_path / "formal-copy"
    plan = dry_run(compiled, target)
    tampered = copy.deepcopy(plan)
    tampered["branch_id"] = "other"
    assert apply_sync_plan(tampered, lambda: compiled, target)["status"] == "plan_stale"
    changed = copy.deepcopy(compiled)
    changed["identity"]["test_data_hash"] = "sha256:" + "0" * 64
    assert apply_sync_plan(plan, lambda: changed, target)["status"] == "plan_stale"


def test_generation_failure_keeps_active_and_cleans_unique_staging(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    target = tmp_path / "formal-copy"
    plan = dry_run(compiled, target, operation_id="op-fail")
    result = apply_sync_plan(plan, lambda: copy.deepcopy(compiled), target, fail_after_artifacts=1)
    assert result["status"] == "generation_failed"
    assert not (target / "active.json").exists()
    staging = target / "_staging"
    assert list(staging.iterdir()) == []

