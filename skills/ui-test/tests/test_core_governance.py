import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.ui_test_core.checkpoint_governance import (
    SemanticReadonlySignature, build_module_ready_context, checkpoint_identity,
    promotion_status, rebuild_scope, stale_decision, validate_module_ready_context,
    verify_module_signature,
)
from scripts.ui_test_core.migration import migrate_run_result, migration_issue_list
from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.preflight import capability_manifest, check_midscene_lock
from scripts.ui_test_core.result_model import aggregate_run, evaluate_completion, validate_branch_isolation
from scripts.ui_test_core.state_machine import transition


class StateTests(unittest.TestCase):
    def test_completion_requires_gate(self):
        self.assertFalse(transition("report", "done")["ok"])
        self.assertTrue(transition("report", "done", completion_passed=True)["ok"])

    def test_illegal_transitions(self):
        self.assertFalse(transition("blocked", "done", completion_passed=True)["ok"])
        self.assertFalse(transition("done", "plan")["ok"])
        self.assertFalse(transition("plan", "preflight", actor="claude")["ok"])


class ResultTests(unittest.TestCase):
    def test_required_failure_wins(self):
        result = aggregate_run([{"status":"failed","required":True,"evidence_refs":["e1"]},{"status":"passed","required":True,"evidence_refs":["e2"],"tool":"midscene"}])
        self.assertEqual(result["overall_status"], "failed")

    def test_missing_evidence_blocks_pass(self):
        self.assertEqual(aggregate_run([{"status":"passed","required":True,"evidence_refs":[]}])["overall_status"], "failed")

    def test_branch_isolation(self):
        self.assertEqual(validate_branch_isolation([{"run_id":"r1","context_id":"c1","evidence_namespace":"e1","report_namespace":"p1"},{"run_id":"r2","context_id":"c2","evidence_namespace":"e2","report_namespace":"p2"}]), [])
        self.assertTrue(validate_branch_isolation([{"run_id":"r1","context_id":"same","evidence_namespace":"e1","report_namespace":"p1"},{"run_id":"r2","context_id":"same","evidence_namespace":"e2","report_namespace":"p2"}]))

    def test_completion_fail_closed(self):
        run = {"overall_status":"passed"}
        ok = evaluate_completion(run_result=run, required_requirements={"FR1"}, passed_requirements={"FR1"}, sensitive_scan_ok=True, migration_ok=True, state_valid=True, risk_isolated=True, p0_p1_findings=[])
        self.assertTrue(ok["completed"])
        blocked = evaluate_completion(run_result=run, required_requirements={"FR1","FR2"}, passed_requirements={"FR1"}, sensitive_scan_ok=True, migration_ok=True, state_valid=True, risk_isolated=True, p0_p1_findings=[])
        self.assertFalse(blocked["completed"])


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.scope = {"project_group":"pg","product":"prod","system":"sys","module_path":["mod"],"function":"fn","checkpoint":"cp","environment":"public","risk_level":"r0-read-only"}

    def test_identity_ignores_display_alias(self):
        self.assertEqual(checkpoint_identity(self.scope, "module-1")["checkpoint_id"], checkpoint_identity(self.scope, "module-1")["checkpoint_id"])

    def test_promotion_two_independent_sessions(self):
        self.assertEqual(promotion_status([{"session_id":"s1","deterministic_pass":True}]), "validated")
        self.assertEqual(promotion_status([{"session_id":"s1","deterministic_pass":True},{"session_id":"s2","deterministic_pass":True}]), "eligible")
        self.assertEqual(promotion_status([{"session_id":"s1","deterministic_pass":True},{"session_id":"s1","deterministic_pass":True,"retry_of":"a"}]), "validated")

    def test_signature_and_context(self):
        sig = verify_module_signature(True, ["title", "checkbox-list"])
        self.assertTrue(sig["ok"])
        identity = checkpoint_identity(self.scope, "module-1")
        context = build_module_ready_context(session_id="s1",run_id="r1",identity=identity,signature=sig,auth_reference_digest="sha256-abc",policy_fingerprint="pf",generated_at="now",expires_at="later",evidence_refs=["e1"])
        self.assertEqual(context["handoff_status"], "ready")
        self.assertTrue(validate_module_ready_context(context, session_id="s1", run_id="r1", context_id=context["context_id"])["ok"])
        self.assertFalse(validate_module_ready_context(context, session_id="s2", run_id="r1")["ok"])
        self.assertFalse(validate_module_ready_context({**context, "token": "redacted"}, session_id="s1", run_id="r1")["ok"])
        self.assertFalse(verify_module_signature(True, ["title"])["ok"])
        self.assertFalse(verify_module_signature(True, ["title", "list"], host_verified=False)["ok"])
        self.assertFalse(verify_module_signature(True, ["title", "list"], authenticated_session_verified=False)["ok"])

    def test_r2_checkpoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "E_CHECKPOINT_RISK_UNSUPPORTED"):
            checkpoint_identity({**self.scope, "risk_level": "r2-ui-write-test"}, "module-1")

    def test_stale_and_local_rebuild(self):
        self.assertEqual(stale_decision(signature_conflict=True)["status"], "stale")
        failures = [{"root_cause":"selector","independent_session":True},{"root_cause":"selector","independent_session":True}]
        self.assertEqual(stale_decision(failed_attempts=failures)["status"], "stale")
        self.assertEqual(rebuild_scope(["CP1","CP3","CP4","CP5"], "CP4"), ["CP4","CP5"])

    def test_semantic_readonly_signature(self):
        path_hash = hashlib.sha256(b"/list").hexdigest()
        policy = SemanticReadonlySignature("POST", path_hash, "application/json", ("page",), ("pageNum","pageSize"), 4)
        request = {"method":"POST","path_sha256":path_hash,"content_type":"application/json; charset=utf-8","query_keys":["page"],"payload_keys":["pageSize","pageNum"]}
        self.assertTrue(policy.matches(request, 4))
        self.assertFalse(policy.matches(request, 5))
        self.assertFalse(policy.matches({**request,"raw_url":"https://example.invalid/list?page=1"}, 1))


class PreflightMigrationTests(unittest.TestCase):
    def test_midscene_lock(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "pnpm-lock.yaml"
            lock.write_text("'@midscene/core@1.10.2':\n'@midscene/web@1.10.2(playwright@1.61.1)':\n", encoding="utf-8")
            self.assertTrue(check_midscene_lock(lock)["ok"])

    def test_budget(self):
        self.assertTrue(capability_manifest(python_ok=True,node_ok=True,browser_ok=True,lock_ok=True,model_gateway_ok=True,permissions_ok=True,free_bytes=2*1024**3,risk_level="r0-read-only",requested_bytes=512*1024**2)["ok"])
        oversized = capability_manifest(python_ok=True,node_ok=True,browser_ok=True,lock_ok=True,model_gateway_ok=True,permissions_ok=True,free_bytes=2*1024**3,risk_level="r0-read-only",requested_bytes=512*1024**2+1)
        self.assertTrue(oversized["ok"])
        self.assertIn("W_ARTIFACT_BUDGET_EXCEEDED", oversized["warnings"])

    def test_migration_is_idempotent_and_does_not_invent_pass(self):
        old = {"run_id":"r1","status":"passed","steps":[{"id":"s1","result":"passed"}]}
        migrated = migrate_run_result(old, "old-summary")
        self.assertEqual(migrated["overall_status"], "unknown")
        self.assertEqual(migrate_run_result(migrated), migrated)
        issues = migration_issue_list(old, source_ref="old-summary", source_type="run-result", target_sidecar_ref="old-summary.sidecar.json")
        self.assertTrue(issues["blocking_completion"])
        self.assertIn("issue_id", issues["issues"][0])
        self.assertEqual(validate_document(issues, "migration-issue-list.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
