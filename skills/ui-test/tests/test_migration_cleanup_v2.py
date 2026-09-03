from scripts.ui_test_core.migration_cleanup import create_cleanup_plan, create_migration_plan, dry_run_cleanup, inventory_tree


def test_inventory_migration_plan_and_zero_delete_cleanup(tmp_path):
    (tmp_path / "releases" / "old").mkdir(parents=True)
    (tmp_path / "releases" / "old" / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "cache.txt").write_text("x", encoding="utf-8")
    before = inventory_tree(tmp_path)
    migration = create_migration_plan(before, [{"case_id": "DEMO-CASE-A", "branch_id": "primary"}])
    assert migration["formal_apply_authorized"] is False
    cleanup = create_cleanup_plan(before)
    dispositions = {item["path"]: item["disposition"] for item in cleanup["items"]}
    assert dispositions["releases/old/manifest.json"] == "retain"
    assert dispositions[".pytest_cache/cache.txt"] == "cleanup-eligible"
    after = inventory_tree(tmp_path)
    result = dry_run_cleanup(cleanup, before, after)
    assert result["deleted_count"] == 0 and result["unchanged"] is True

