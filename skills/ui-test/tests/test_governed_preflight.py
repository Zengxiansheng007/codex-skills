import tempfile
import unittest

from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.preflight import governed_asset_preflight, governed_post_write_gate
from scripts.ui_test_core.project_config import load_project_config
from tests.test_packet_validator import load as load_packet
from tests.test_project_paths import project_v2, selection, write_config


class GovernedPreflightTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = load_project_config(write_config(directory.name, project_v2()))
        self.packet = load_packet("packet_valid.json")
        self.packet["scope"].update({
            "project_group": "tianjin", "product": "ops-platform", "system": "bops-ops-platform",
            "module_path": ["operations-config", "message-management", "announcement-management"],
            "function": "create", "environment": "test", "risk_level": "r0-read-only",
        })

    def test_valid_preflight_returns_governed_path_plan(self):
        result = governed_asset_preflight(
            config=self.config, packet=self.packet, release_status="in_sync", documents={"source": "clear"},
            asset_requests=[{"asset_type": "source_case", "selection": selection()}], migration_issue_lists=[],
        )
        self.assertTrue(result["ok"], result["issues"])
        self.assertTrue(result["formal_write_allowed"])
        self.assertEqual(validate_document(result, "preflight-result.schema.json"), [])

    def test_preflight_fails_closed_for_config_packet_secret_path_migration_and_status(self):
        packet = dict(self.packet)
        packet["schema_version"] = "1.0"
        result = governed_asset_preflight(
            config=None, packet=packet, release_status="manual_drift",
            documents={"authorization": "synthetic"},
            asset_requests=[{"asset_type": "source_case", "selection": selection(output_dir=r"C:\temp")}],
            migration_issue_lists=[{"blocking_completion": True}],
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertFalse(result["formal_write_allowed"])
        self.assertTrue({"E_CONFIG_NOT_WRITE_READY", "E_PACKET_MIGRATION_REQUIRED", "E_RELEASE_NOT_IN_SYNC", "E_SECRET_DETECTED", "E_MIGRATION_BLOCKING_ISSUES"}.issubset(codes))

    def test_preflight_rejects_caller_selected_output(self):
        result = governed_asset_preflight(
            config=self.config, packet=self.packet, release_status="in_sync", documents={},
            asset_requests=[{"asset_type": "source_case", "selection": selection(output_dir=r"C:\temp")}],
        )
        self.assertIn("E_CALLER_ROOT_FORBIDDEN", {item["code"] for item in result["issues"]})

    def test_post_write_blocks_c_drive_wrong_root_and_drift(self):
        result = governed_post_write_gate(
            release_status="in_sync",
            artifacts=[
                {"ui_test_project_asset": True, "asset_type": "source_case", "path": r"C:\temp\source.json", "sync_status": "in_sync"},
                {"ui_test_project_asset": True, "asset_type": "experience_candidate", "path": r"D:\UI-Test\candidate.json", "sync_status": "manual_drift"},
            ],
            formal_references=[],
        )
        codes = {item["code"] for item in result["issues"]}
        self.assertFalse(result["completion_allowed"])
        self.assertTrue({"E_UI_TEST_ASSET_ON_C_DRIVE", "E_PATH_ROOT_TYPE_MISMATCH", "E_DERIVED_ASSET_NOT_IN_SYNC"}.issubset(codes))
        self.assertEqual(validate_document(result, "preflight-result.schema.json"), [])

    def test_post_write_ignores_non_ui_test_c_drive_file(self):
        result = governed_post_write_gate(
            release_status="in_sync",
            artifacts=[{"ui_test_project_asset": False, "asset_type": "ordinary_workspace_document", "path": r"C:\workspace\notes.md"}],
            formal_references=[{"ui_test_project_asset": True, "asset_type": "source_case", "path": r"D:\UI-Test\project\source.json", "sync_status": "in_sync"}],
        )
        self.assertTrue(result["completion_allowed"], result["issues"])


if __name__ == "__main__":
    unittest.main()
