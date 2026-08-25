import json
import unittest
from pathlib import Path

from scripts.ui_test_core.packet_validator import validate_packet
from scripts.ui_test_core.migration import migrate_packet_dry_run


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "assets" / "fixtures" / name).read_text(encoding="utf-8"))


class PacketValidatorTests(unittest.TestCase):
    def test_valid_packet(self):
        self.assertEqual(validate_packet(load("packet_valid.json")), [])

    def test_missing_product(self):
        errors = validate_packet(load("packet_invalid_missing_product.json"))
        self.assertIn("E_SCOPE_FIELD_MISSING", {e["code"] for e in errors})

    def test_unknown_action(self):
        errors = validate_packet(load("packet_invalid_unknown_action.json"))
        self.assertIn("E_ACTION_UNKNOWN", {e["code"] for e in errors})

    def test_r1_write_classification_is_blocked(self):
        errors = validate_packet(load("packet_invalid_r1_write.json"))
        self.assertIn("E_RISK_ACTION_CONFLICT", {e["code"] for e in errors})

    def test_mixed_r1_r2_packet_is_valid_when_effective_risk_is_highest_step(self):
        packet = load("packet_valid.json")
        packet["scope"]["environment"] = "test"
        packet["scope"]["risk_level"] = "r2-ui-write-test"
        packet["risk_level"] = "r2-ui-write-test"
        packet["effective_risk_level"] = "r2-ui-write-test"
        packet["steps"] = [
            {"step_id": "S01", "action": "navigate", "risk_level": "r1-read-only-authenticated", "required": True},
            {"step_id": "S02", "action": "fill", "risk_level": "r2-ui-write-test", "required": True},
            {"step_id": "S03", "action": "submit", "risk_level": "r2-ui-write-test", "required": True},
        ]
        self.assertEqual(validate_packet(packet), [])

    def test_effective_risk_must_match_highest_step(self):
        packet = load("packet_valid.json")
        packet["scope"]["risk_level"] = "r1-read-only-authenticated"
        packet["risk_level"] = "r1-read-only-authenticated"
        packet["effective_risk_level"] = "r1-read-only-authenticated"
        packet["steps"].append({"step_id": "S03", "action": "submit", "risk_level": "r2-ui-write-test", "required": True})
        errors = validate_packet(packet)
        self.assertIn("E_EFFECTIVE_RISK_MISMATCH", {e["code"] for e in errors})

    def test_secret_is_blocked(self):
        packet = load("packet_invalid_secret.json")
        packet["steps"][0]["intent"] = "Bearer " + ("x" * 30)
        errors = validate_packet(packet)
        self.assertIn("E_SECRET_DETECTED", {e["code"] for e in errors})

    def test_unknown_version_is_blocked(self):
        errors = validate_packet(load("packet_invalid_version.json"))
        self.assertIn("E_PACKET_VERSION_UNKNOWN", {e["code"] for e in errors})

    def test_v1_requires_central_migration(self):
        packet = load("packet_valid.json")
        packet["schema_version"] = "1.0"
        errors = validate_packet(packet)
        self.assertEqual(errors[0]["code"], "E_PACKET_MIGRATION_REQUIRED")

    def test_v1_dry_run_maps_module_to_module_path_without_mutating_source(self):
        source = load("packet_valid.json")
        source["schema_version"] = "1.0"
        source["scope"]["module"] = source["scope"].pop("module_path")[-1]
        before = json.dumps(source, sort_keys=True)
        result = migrate_packet_dry_run(source, source_ref="legacy.json", target_sidecar_ref="legacy.packet-v2.sidecar.json")
        self.assertEqual(result["candidate_packet"]["scope"]["module_path"], ["checkboxes"])
        self.assertEqual(json.dumps(source, sort_keys=True), before)
        self.assertTrue(result["source_unchanged"])
        self.assertFalse(result["source_overwrite_permitted"])
        self.assertTrue(result["ready_for_sidecar"])

    def test_unknown_legacy_version_fails_closed(self):
        source = load("packet_valid.json")
        source["schema_version"] = "7.0"
        result = migrate_packet_dry_run(source, source_ref="future.json", target_sidecar_ref="future.sidecar.json")
        self.assertIsNone(result["candidate_packet"])
        self.assertTrue(result["issue_list"]["blocking_completion"])
        self.assertIn("E_MIGRATION_PACKET_VERSION_UNSUPPORTED", {item["problem_code"] for item in result["issue_list"]["issues"]})


if __name__ == "__main__":
    unittest.main()
