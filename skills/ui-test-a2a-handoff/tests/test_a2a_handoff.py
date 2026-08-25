import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.a2a_handoff import build_handoff_packet, build_prompt_packet, pack, validate_packet


FIXTURES = ROOT / "fixtures"


class A2AHandoffTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_validate_packet_accepts_valid_source(self):
        packet = self.load("source_packet_valid.json")
        validate_packet(packet)

    def test_validate_packet_rejects_missing_packet_id(self):
        packet = self.load("source_packet_invalid_missing_id.json")
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_handoff_packet_preserves_history(self):
        packet = self.load("source_packet_valid.json")
        handoff = build_handoff_packet(packet)
        self.assertEqual(handoff["source_packet_id"], packet["packet_id"])
        self.assertTrue(handoff["failure_history"])
        self.assertTrue(handoff["retry_history"])
        self.assertTrue(handoff["required_fix_points"])
        self.assertEqual(handoff["next_action"], "revise_prompt")
        self.assertIn("handoff_id", handoff)

    def test_prompt_packet_is_deterministic(self):
        packet = self.load("source_packet_valid.json")
        handoff = build_handoff_packet(packet)
        prompt1 = build_prompt_packet(packet, handoff)
        prompt2 = build_prompt_packet(packet, handoff)
        self.assertEqual(prompt1, prompt2)
        self.assertEqual(prompt1["source_packet_id"], packet["packet_id"])
        self.assertIn("expected_verification", prompt1)

    def test_pack_returns_all_contracts(self):
        packet = self.load("source_packet_valid.json")
        result = pack(packet)
        self.assertIn("handoff_packet", result)
        self.assertNotIn("hand_off", result)
        self.assertIn("prompt_packet", result)
        self.assertIn("artifact_refs", result)
        self.assertEqual(result["summary"]["source_packet_id"], packet["packet_id"])

    def test_validate_packet_rejects_missing_steps(self):
        packet = self.load("source_packet_valid.json")
        packet.pop("steps")
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_validate_packet_rejects_non_read_only_safety(self):
        packet = self.load("source_packet_valid.json")
        packet["safety"]["read_only"] = False
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_validate_packet_rejects_empty_forbidden_actions(self):
        packet = self.load("source_packet_valid.json")
        packet["safety"]["forbidden_actions"] = []
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_sensitive_bearer_refs_rejected(self):
        packet = self.load("source_packet_valid.json")
        packet["artifact_refs"].append({"type": "trace_path", "path": "Bear" + "er abc.def.ghi"})
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_sensitive_refs_rejected(self):
        packet = self.load("source_packet_valid.json")
        packet["artifact_refs"].append({"type": "note", "text": "sk-abc123"})
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_artifact_refs_are_trimmed_to_stable_keys(self):
        packet = self.load("source_packet_valid.json")
        packet["artifact_refs"].append({
            "type": "report",
            "path": "reports/run.html",
            "title": "long prose that should be dropped",
            "note": "keep only stable refs",
        })
        handoff = build_handoff_packet(packet)
        self.assertTrue(all(set(ref.keys()) <= {"type", "path", "packet_id", "report_id", "screenshot_path", "trace_path", "json_path", "ref_id"} if isinstance(ref, dict) else True for ref in handoff["artifact_refs"]))


if __name__ == "__main__":
    unittest.main()
