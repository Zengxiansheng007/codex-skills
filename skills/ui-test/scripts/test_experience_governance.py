import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_experience_packet.py")
SPEC = importlib.util.spec_from_file_location("experience_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def packet(**changes):
    value = {
        "experience_id": "EXP-TEST-001",
        "experience_version": 1,
        "experience_status": "candidate",
        "scope": {
            "project_group": "project-a", "product": "product-a", "system": "system-a",
            "module": "announcement", "function": "list", "checkpoint": "CP3",
            "environment": "test", "risk_level": "r1-read-only",
        },
        "category": "network", "trigger": "list-query", "strategy": "bounded-read-only-post",
        "source_run_ids": ["RUN-1"], "source_step_ids": ["CP3"],
        "source_checkpoint_ids": ["CP3"], "evidence_refs": ["EV-1"],
    }
    value.update(changes)
    return value


class ExperienceGovernanceTests(unittest.TestCase):
    def test_scope_keeps_project_group_and_product_independent(self):
        checked = MODULE.validate_packet(packet())
        self.assertEqual("project-a", checked["scope"]["project_group"])
        self.assertEqual("product-a", checked["scope"]["product"])

    def test_semantic_post_accepts_signature_without_values(self):
        signature = {
            "method": "POST", "path_sha256": "a" * 64, "query_keys": ["ctoken"],
            "body_keys": ["current", "pageSize"], "content_type": "application/json",
            "classification": "pagination", "max_per_session": 4,
        }
        checked = MODULE.validate_packet(packet(semantic_post=signature))
        self.assertTrue(checked["content_hash"].startswith("sha256:"))
        observed = {key: signature[key] for key in ("method", "path_sha256", "query_keys", "body_keys", "content_type")}
        self.assertTrue(MODULE.authorize_semantic_post(observed, signature, used_count=3)["allowed"])
        self.assertFalse(MODULE.authorize_semantic_post(observed, signature, used_count=4)["allowed"])

    def test_semantic_post_rejects_raw_url_and_values(self):
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(packet(semantic_post={
                "method": "POST", "path_sha256": "a" * 64, "query_keys": [], "body_keys": [],
                "content_type": "application/json", "classification": "query", "max_per_session": 1,
                "url": "https://private.invalid/api",
            }))

    def test_writeback_allows_candidate_only_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            policy = {
                "policy_id": "POL-TEST", "status": "active", "knowledge_space_id": "ks-test",
                "target_root": str(Path(temp).resolve()), "project_group": "project-a", "product": "product-a",
                "environment": "test", "allowed_actions": ["append-candidate"], "valid_from": "2026-08-17T00:00:00Z",
                "expires_at": "2026-11-15T00:00:00Z", "auto_renew": False, "approval_ref": "AUTH-TEST",
            }
            policy["boundary_hash"] = MODULE.canonical_hash(policy)
            # Exercise atomic append without permitting a test to write D:/RAG.
            target = Path(temp) / "candidate.json"
            result = MODULE._atomic_create(target, packet())
            self.assertEqual("created", result)
            self.assertEqual("idempotent", MODULE._atomic_create(target, packet()))
            self.assertEqual("candidate", json.loads(target.read_text(encoding="utf-8"))["experience_status"])
            MODULE.validate_policy(policy, now="2026-08-17T12:00:00Z")

    def test_active_cannot_be_written_automatically(self):
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(packet(experience_status="active"), for_writeback=True)

    def test_r2_cannot_be_written_automatically(self):
        value = packet()
        value["scope"] = dict(value["scope"], risk_level="r2-write-isolated")
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(value, for_writeback=True)

    def test_sensitive_value_and_production_marker_fail_closed(self):
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(packet(strategy="pass" + "word=not-a-real-value"))
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(packet(contains_production_data=True))


if __name__ == "__main__":
    unittest.main()
