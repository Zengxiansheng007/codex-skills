import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ui_test_core.path_planner import (
    PathPlanningError,
    is_ui_test_project_asset,
    plan_asset_path,
    validate_existing_path_containment,
)
from scripts.ui_test_core.project_config import ProjectConfigError, load_project_config


def project_v2():
    return {
        "schema_version": "2.0",
        "scope": {
            "project_group": "tianjin", "project_group_name": "天津项目组",
            "product": "ops-platform", "product_name": "运维管理系统", "product_aliases": ["运管平台"],
            "environment": "test"
        },
        "asset_governance": {
            "execution_asset_root": r"D:\UI-Test", "knowledge_root": r"D:\RAG",
            "staging_root": r"D:\UI-Test\_tmp", "forbidden_persistent_roots": ["C:\\"],
            "layout_version": 1,
            "levels": ["project_group", "product", "system", "module_path", "function", "case", "branch", "run"],
            "segment_naming": "stable-id__display-name", "asset_type_policy_version": "ui-test.asset-types.v1"
        },
        "systems": [{
            "system_id": "bops-ops-platform", "display_name": "运维管理系统",
            "modules": [{
                "module_id": "announcement-management", "display_name": "公告管理", "aliases": ["公告管理"],
                "module_path": [
                    {"module_id": "operations-config", "display_name": "运营配置"},
                    {"module_id": "message-management", "display_name": "消息管理"},
                    {"module_id": "announcement-management", "display_name": "公告管理"}
                ],
                "functions": [{"function_id": "create", "display_name": "创建"}],
                "direct_route_ref": "route.announcement.create"
            }]
        }],
        "runtime_env_keys": ["BOPS_ACCOUNT_USER"],
        "checkpoint_runtime": {"root_ref": "checkpoint-root"},
        "knowledge_space": {"knowledge_space_id": "tianjin-ops-ui-test-experience", "relative_path": r"10_knowledge_spaces\tianjin-ops-ui-test-experience"},
        "wait_strategy": {"default_ref": "slow-network"},
        "semantic_post_signatures": [],
        "execution_policies": []
    }


def write_config(directory, value=None):
    path = Path(directory) / "ui-test.project.json"
    path.write_text(json.dumps(value or project_v2(), ensure_ascii=False), encoding="utf-8")
    return path


def selection(**overrides):
    value = {
        "system": "bops-ops-platform",
        "module_path": ["operations-config", "message-management", "announcement-management"],
        "function": "create",
        "case_id": "BOPS-ANNOUNCEMENT-P0-A",
        "branch_id": "system-announcement",
        "run_id": "RUN-20260822-001", "year": "2026", "month": "08",
        "asset_id": "EV-001"
    }
    value.update(overrides)
    return value


class ProjectPathTests(unittest.TestCase):
    def test_v2_config_and_execution_path_are_governed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_project_config(write_config(directory))
        plan = plan_asset_path(config, "source_case", selection())
        self.assertEqual(plan["root_kind"], "execution")
        self.assertTrue(plan["target_path"].startswith(r"D:\UI-Test\tianjin__天津项目组\ops-platform__运维管理系统"))
        self.assertIn(r"ops-platform__运维管理系统\bops-ops-platform__运维管理系统", plan["target_path"])
        self.assertIn(r"operations-config__运营配置\message-management__消息管理\announcement-management__公告管理\create__创建", plan["target_path"])
        self.assertTrue(plan["target_path"].endswith(r"cases\BOPS-ANNOUNCEMENT-P0-A\branches\system-announcement\source\source-case.json"))

    def test_yaml_project_config_is_loaded_with_declared_dependency(self):
        import yaml

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ui-test.project.yaml"
            path.write_text(yaml.safe_dump(project_v2(), allow_unicode=True, sort_keys=False), encoding="utf-8")
            config = load_project_config(path)
        self.assertEqual(config["scope"]["project_group"], "tianjin")
        self.assertTrue(config["config_fingerprint"].startswith("sha256:"))

    def test_asset_type_selects_root_without_caller_root(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_project_config(write_config(directory))
        knowledge = plan_asset_path(config, "experience_candidate", selection())
        execution = plan_asset_path(config, "run_result", selection())
        staging = plan_asset_path(config, "staging", selection())
        self.assertEqual(knowledge["root"], r"D:\RAG")
        self.assertEqual(execution["root"], r"D:\UI-Test")
        self.assertIn(r"cases\BOPS-ANNOUNCEMENT-P0-A\branches\system-announcement\runs\2026\08\RUN-20260822-001", execution["target_path"])
        self.assertTrue(staging["target_path"].startswith(r"D:\UI-Test\_tmp\tianjin__天津项目组"))
        self.assertFalse(knowledge["caller_selected_root"])
        self.assertFalse(execution["caller_selected_root"])
        with self.assertRaisesRegex(PathPlanningError, "E_CALLER_ROOT_FORBIDDEN"):
            plan_asset_path(config, "source_case", selection(output_dir=r"C:\temp"))

    def test_root_type_mismatch_is_rejected_with_stable_code(self):
        bad = project_v2()
        bad["asset_governance"]["execution_asset_root"] = r"D:\RAG"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ProjectConfigError, "E_PATH_ROOT_TYPE_MISMATCH"):
                load_project_config(write_config(directory, bad))

    def test_unknown_business_scope_and_arbitrary_asset_type_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_project_config(write_config(directory))
        with self.assertRaisesRegex(PathPlanningError, "E_MODULE_PATH_UNKNOWN"):
            plan_asset_path(config, "source_case", selection(module_path=["unknown"]))
        with self.assertRaisesRegex(PathPlanningError, "E_ASSET_TYPE_UNKNOWN"):
            plan_asset_path(config, "caller-chosen-path", selection())

    def test_non_ui_test_c_drive_file_is_outside_planner_scope(self):
        self.assertFalse(is_ui_test_project_asset("ordinary_workspace_document"))
        self.assertFalse(is_ui_test_project_asset("global_skill_program"))

    def test_lexical_escape_and_reparse_point_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            with self.assertRaisesRegex(PathPlanningError, "E_PATH_OUTSIDE_ROOT"):
                validate_existing_path_containment(root, outside / "asset.json")
            link = root / "linked"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                with patch.object(Path, "is_symlink", return_value=True):
                    with self.assertRaisesRegex(PathPlanningError, "E_PATH_REPARSE_POINT_BLOCKED"):
                        validate_existing_path_containment(root, root / "asset.json")
                return
            with self.assertRaisesRegex(PathPlanningError, "E_PATH_REPARSE_POINT_BLOCKED|E_PATH_OUTSIDE_ROOT"):
                validate_existing_path_containment(root, link / "asset.json")


if __name__ == "__main__":
    unittest.main()
