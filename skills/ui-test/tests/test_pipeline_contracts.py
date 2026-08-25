import json
import tempfile
import unittest
from pathlib import Path

from scripts.ui_test_core.completion import evaluate_release, validate_rtm
from scripts.ui_test_core.evidence import attachment
from scripts.ui_test_core.experience_store import consumption_feedback, is_forbidden_reuse, lookup
from scripts.ui_test_core.execution_policy import evaluate_packet_policy
from scripts.ui_test_core.metrics import checkpoint_metrics, project_run_metrics
from scripts.ui_test_core.midscene_adapter import MidsceneAdapter
from scripts.ui_test_core.project_config import ProjectConfigError, load_project_config
from scripts.ui_test_core.retry_policy import ActionTokenLedger, RetryBudget, retry_scope_for_action, run_bounded
from scripts.ui_test_core.risk_policy import split_by_risk, validate_action_risk
from scripts.ui_test_core.routing import legacy_route_decision, route_packet
from scripts.ui_test_core.secret_governance import quarantine_record, scan_value
from scripts.ui_test_core.verifier import reconcile_midscene, verify_postcondition


ROOT = Path(__file__).resolve().parents[1]


def valid_packet():
    return json.loads((ROOT / "assets" / "fixtures" / "packet_valid.json").read_text(encoding="utf-8"))


class RoutingSafetyTests(unittest.TestCase):
    def test_current_and_legacy_share_schema_decision(self):
        current = route_packet(valid_packet())
        legacy = legacy_route_decision(valid_packet())
        self.assertTrue(current["ok"])
        self.assertTrue(legacy["ok"])
        self.assertEqual(current["packet_schema_version"], legacy["packet_schema_version"])
        self.assertEqual(legacy["replacement"], "ui-test")
        self.assertFalse(legacy["payload_forwarded"])

    def test_invalid_route_returns_problem_details(self):
        packet = valid_packet()
        packet["scope"].pop("product")
        result = route_packet(packet)
        self.assertFalse(result["ok"])
        self.assertEqual(result["problem"]["status"], 422)
        self.assertIn("code", result["problem"])

    def test_risk_split_preserves_parent_lineage(self):
        packet = valid_packet()
        packet["steps"].append({"step_id": "S2", "action": "submit", "risk_level": "r2-ui-write-test", "required": True})
        children = split_by_risk(packet)
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child["lineage"]["parent_packet_id"] == packet["packet_id"] for child in children))
        self.assertNotEqual(children[0]["packet_id"], children[1]["packet_id"])

    def test_r2_is_ui_only_and_r3_blocked(self):
        self.assertEqual(validate_action_risk("submit", "r2-ui-write-test", "test")["execution_mode"], "ui-only")
        self.assertFalse(validate_action_risk("publish", "r3-high-impact", "test")["allowed"])

    def test_execution_policy_is_separate_from_risk_classification(self):
        packet = valid_packet()
        packet["scope"]["environment"] = "test"
        packet["steps"].append({"step_id": "S2", "action": "submit", "risk_level": "r2-ui-write-test", "required": True})
        policy = {"policy_id": "POL-1", "allow_actions": ["navigate", "assert", "submit"], "deny_actions": [], "task_authorization": "approved"}
        self.assertTrue(evaluate_packet_policy(packet, policy, channel="ui")["allowed"])
        self.assertFalse(evaluate_packet_policy(packet, policy, channel="api")["allowed"])
        packet["scope"]["environment"] = "production"
        self.assertFalse(evaluate_packet_policy(packet, policy, channel="ui")["allowed"])

    def test_secret_scan_and_quarantine_do_not_echo_value(self):
        value = "Bear" + "er " + ("x" * 16)
        findings = scan_value({"note": value})
        record = quarantine_record("fixture.json", findings)
        self.assertTrue(findings)
        self.assertNotIn(value, json.dumps(record))
        self.assertFalse(record["raw_values_persisted"])


class ConfigExecutionTests(unittest.TestCase):
    def test_project_config_is_versioned_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.json"
            path.write_text(json.dumps({
                "schema_version": "1.0",
                "scope": {"project_group": "pg", "product": "prod", "environment": "test"},
                "systems": [{"system_id": "sys", "modules": [{"module_id": "mod", "aliases": ["Module"], "direct_route_ref": "route.mod"}]}],
                "runtime_env_keys": ["MISSING_FOR_TEST"],
                "checkpoint_runtime": {"root_ref": "runtime-root"},
                "knowledge_space": {"knowledge_space_id": "ks-public", "root_ref": "KS_PUBLIC"},
                "wait_strategy": {"default_ref": "slow-network"},
                "semantic_post_signatures": [],
                "execution_policies": [{"policy_id": "POL-TEST", "allow_actions": ["navigate"], "deny_actions": []}]
            }), encoding="utf-8")
            config = load_project_config(path, purpose="inventory")
            self.assertTrue(config["config_fingerprint"].startswith("sha256:"))
            self.assertFalse(config["runtime_env_present"]["MISSING_FOR_TEST"])
            self.assertFalse(config["write_ready"])

    def test_v1_project_config_cannot_authorize_writes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.json"
            path.write_text(json.dumps({
                "schema_version": "1.0",
                "scope": {"project_group": "pg", "product": "prod", "environment": "test"},
                "systems": [{"system_id": "sys", "modules": [{"module_id": "mod", "aliases": ["Module"], "direct_route_ref": "route.mod"}]}],
                "runtime_env_keys": [],
                "checkpoint_runtime": {"root_ref": "runtime-root"},
                "knowledge_space": {"knowledge_space_id": "ks-public", "root_ref": "KS_PUBLIC"},
                "wait_strategy": {}, "semantic_post_signatures": [], "execution_policies": []
            }), encoding="utf-8")
            with self.assertRaisesRegex(ProjectConfigError, "E_CONFIG_UPGRADE_REQUIRED"):
                load_project_config(path)

    def test_project_config_rejects_secret_key(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.json"
            path.write_text(json.dumps({
                "schema_version": "1.0",
                "scope": {"project_group": "pg", "product": "prod", "environment": "test"},
                "systems": [{"system_id": "sys", "modules": [{"module_id": "mod", "aliases": ["Module"], "direct_route_ref": "route.mod"}]}],
                "runtime_env_keys": [],
                "checkpoint_runtime": {"root_ref": "runtime-root"},
                "knowledge_space": {"knowledge_space_id": "ks-public", "root_ref": "KS_PUBLIC"},
                "wait_strategy": {"default_ref": "slow-network"},
                "semantic_post_signatures": [],
                "execution_policies": [],
                "pass" + "word": "<redacted>"
            }), encoding="utf-8")
            with self.assertRaises(ProjectConfigError):
                load_project_config(path)

    def test_midscene_adapter_requires_ready_context_and_records_progress(self):
        adapter = MidsceneAdapter()
        context = {"handoff_status": "ready"}
        self.assertTrue(adapter.preflight("1.10.2", True, context)["ok"])
        progress = []
        result = adapter.explore(page=object(), context=context, intent="inspect module", executor=lambda **_: {"status": "passed"}, progress=progress.append)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual([item["event"] for item in progress], ["started", "finished"])

    def test_midscene_claim_conflict_is_degraded(self):
        verification = verify_postcondition({"url": "/wrong"}, {"url": "/target"})
        result = reconcile_midscene({"status": "passed"}, verification)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["failure_layer"], "ai-recognition")

    def test_retry_is_bounded_and_flaky_is_preserved(self):
        result = run_bounded(lambda attempt: {"status": "failed" if attempt == 1 else "passed"}, RetryBudget(max_attempts=2))
        self.assertEqual(result["status"], "flaky")
        self.assertEqual(len(result["attempts"]), 2)

    def test_non_idempotent_submit_token_cannot_be_reused(self):
        ledger = ActionTokenLedger()
        first = ledger.consume(run_id="run", step_id="submit", action="submit", action_key="one-shot")
        second = ledger.consume(run_id="run", step_id="submit", action="submit", action_key="one-shot")
        self.assertTrue(first["allowed"])
        self.assertFalse(second["allowed"])
        self.assertFalse(retry_scope_for_action("submit", "submit-action")["retry_allowed"])
        self.assertTrue(retry_scope_for_action("submit", "post-submit-query")["retry_allowed"])


class EvidenceExperienceCompletionTests(unittest.TestCase):
    def test_attachment_has_hash_or_governed_missing_reason(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "evidence.txt"
            path.write_text("evidence", encoding="utf-8")
            self.assertTrue(attachment(attachment_id="a", step_id="s", kind="text", path=str(path))["sha256"].startswith("sha256:"))
            with self.assertRaises(ValueError):
                attachment(attachment_id="a", step_id="s", kind="text", missing_reason="unknown")

    def test_experience_lookup_requires_exact_eight_fields(self):
        scope = {"project_group": "pg", "product": "prod", "system": "sys", "module": "mod", "function": "fn", "checkpoint": "cp", "environment": "test", "risk_level": "r1-read-only"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidate.json"
            path.write_text(json.dumps({"experience_id": "EXP-1", "experience_status": "candidate", "scope": scope}), encoding="utf-8")
            self.assertEqual(len(lookup(td, scope)), 1)
            self.assertEqual(lookup(td, {key: value for key, value in scope.items() if key != "product"}), [])
        feedback = consumption_feedback(experience_id="EXP-1", run_id="run-1", checkpoint_version=1, outcome="used", evidence_refs=["EV-1"])
        self.assertEqual(feedback["permission_effect"], "none")
        self.assertTrue(is_forbidden_reuse({"experience_status": "negative"}, scope)["blocked"])
        self.assertTrue(is_forbidden_reuse({"experience_status": "candidate", "forbidden_reuse": [{"scope": scope, "reason": "stale-route"}]}, scope)["blocked"])

    def test_checkpoint_health_thresholds(self):
        self.assertEqual(checkpoint_metrics([{"eligible_sample": True, "status": "passed"}] * 9)["health"], "insufficient")
        self.assertEqual(checkpoint_metrics([{"eligible_sample": True, "status": "passed"}] * 15)["health"], "provisional")
        self.assertEqual(checkpoint_metrics([{"eligible_sample": True, "status": "passed", "entry_midscene_calls": 0}] * 20)["health"], "healthy")

    def test_run_metrics_reject_sensitive_labels(self):
        run_result = {"step_results": [{"tool": "midscene", "attempts": [{"duration_ms": 10}], "fallback_used": True}], "conflicts": [{}], "checkpoint_metrics": {"hit_count": 1, "sample_count": 1}, "budget_warnings": ["W"]}
        metrics = project_run_metrics(run_result, labels={"module": "public"})
        self.assertTrue(any(item["metric_name"] == "midscene.calls" for item in metrics))
        with self.assertRaises(ValueError):
            project_run_metrics(run_result, labels={"url": "https://example.invalid"})

    def test_completion_requires_rtm_tests_scan_migration_and_pilot(self):
        rtm = validate_rtm([{"requirement_id": "FR1", "story_id": "ST1", "test_refs": ["T1"], "evidence_refs": ["E1"]}], {"FR1"})
        result = evaluate_release(rtm=rtm, run_result={"overall_status": "passed"}, tests_ok=True, sensitive_scan={"status": "clear"}, migration_ok=True, public_pilot={"passed": True}, xmind_golden={"passed": True})
        self.assertTrue(result["completed"])
        self.assertEqual(result["global_install"], "waiting-separate-authorization")

    def test_completion_distinguishes_deferred_migration_from_failure(self):
        rtm = validate_rtm([{"requirement_id": "FR1", "story_id": "ST1", "test_refs": ["T1"], "evidence_refs": ["E1"]}], {"FR1"})
        result = evaluate_release(rtm=rtm, run_result={"overall_status": "passed"}, tests_ok=True, sensitive_scan={"status": "clear"}, migration_status="deferred", public_pilot={"passed": True}, xmind_golden={"passed": True})
        self.assertFalse(result["completed"])
        self.assertIn("migration-deferred", result["blockers"])
        self.assertNotIn("migration-failed", result["blockers"])

    def test_completion_blocks_without_xmind_golden(self):
        rtm = validate_rtm([{"requirement_id": "FR1", "story_id": "ST1", "test_refs": ["T1"], "evidence_refs": ["E1"]}], {"FR1"})
        result = evaluate_release(rtm=rtm, run_result={"overall_status": "passed"}, tests_ok=True, sensitive_scan={"status": "clear"}, migration_ok=True, public_pilot={"passed": True})
        self.assertFalse(result["completed"])
        self.assertIn("xmind-golden-pending", result["blockers"])


if __name__ == "__main__":
    unittest.main()
