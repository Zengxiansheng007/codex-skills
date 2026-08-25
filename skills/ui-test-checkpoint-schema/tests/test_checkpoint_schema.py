import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.checkpoint_schema import build_checkpoint_bundle, build_handoff_packet, build_rag_packet, build_ui_test_packet, validate_checkpoint


FIXTURES = ROOT / "fixtures"


class CheckpointSchemaTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_valid_checkpoint_samples_validate(self):
        payload = self.load("checkpoint_samples_valid.json")
        self.assertEqual(len(payload), 7)
        for checkpoint in payload:
            validate_checkpoint(checkpoint)

    def test_valid_checkpoint_samples_remain_utf8_readable(self):
        payload = self.load("checkpoint_samples_valid.json")
        self.assertEqual(payload[0]["name"], "治理与准入基线")
        self.assertEqual(payload[6]["name"], "提交与结果验证")

    def test_cp6_requires_cleanup_policy(self):
        checkpoint = self.load("invalid_missing_cleanup_policy.json")
        with self.assertRaisesRegex(ValueError, "cleanup_policy required for write checkpoints"):
            validate_checkpoint(checkpoint)

    def test_invalid_stage_rejected(self):
        checkpoint = self.load("invalid_wrong_stage.json")
        with self.assertRaisesRegex(ValueError, "stage must be one of"):
            validate_checkpoint(checkpoint)

    def test_invalid_failure_attribution_rejected(self):
        checkpoint = self.load("invalid_bad_failure_attribution.json")
        with self.assertRaisesRegex(ValueError, "invalid failure_attribution.layer"):
            validate_checkpoint(checkpoint)

    def test_bundle_builds_downstream_views(self):
        checkpoint = self.load("checkpoint_samples_valid.json")[6]
        bundle = build_checkpoint_bundle(checkpoint)
        self.assertIn("checkpoint", bundle)
        self.assertIn("ui_test_packet", bundle)
        self.assertIn("handoff_packet", bundle)
        self.assertIn("rag_packet", bundle)
        self.assertEqual(bundle["summary"]["checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertEqual(bundle["handoff_packet"]["source_packet_id"], checkpoint["checkpoint_id"])
        self.assertEqual(bundle["ui_test_packet"]["objective"], checkpoint["name"])

    def test_ui_test_packet_preserves_step_evidence(self):
        checkpoint = self.load("checkpoint_samples_valid.json")[4]
        packet = build_ui_test_packet(checkpoint)
        self.assertTrue(packet["steps"])
        self.assertTrue(packet["artifact_refs"])
        self.assertEqual(packet["next_action"], "review")

    def test_handoff_packet_is_stable_for_same_input(self):
        checkpoint = self.load("checkpoint_samples_valid.json")[5]
        packet1 = build_handoff_packet(checkpoint)
        packet2 = build_handoff_packet(checkpoint)
        self.assertEqual(packet1, packet2)
        self.assertIn("handoff_id", packet1)

    def test_rag_packet_carries_source_context(self):
        checkpoint = self.load("checkpoint_samples_valid.json")[0]
        packet = build_rag_packet(checkpoint)
        self.assertEqual(packet["source_checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertIn("source_baseline", packet)
        self.assertIn("execution_context", packet)


if __name__ == "__main__":
    unittest.main()
