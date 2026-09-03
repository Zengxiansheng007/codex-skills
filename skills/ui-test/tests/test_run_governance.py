import copy
import unittest

from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.migration import evaluate_pilot_delete
from scripts.ui_test_core.run_governance import aggregate_events, create_run_reconciliation, project_run_result


def run_identity():
    return {"run_id": "RUN-1", "case_id": "CASE-A", "branch_id": "system", "priority": "P0", "scope": {"project_group": "pg", "product": "prod", "system": "sys", "module_path": ["module"], "function": "create"}}


def passed_events():
    return [
        {"event_id": "E1", "sequence": 1, "step_id": "S1", "section": "setup", "status": "passed", "required": True, "tool": "playwright", "evidence_refs": ["EV1"]},
        {"event_id": "E2", "sequence": 2, "step_id": "S2", "section": "feature", "status": "passed", "required": True, "tool": "playwright", "evidence_refs": ["EV2"]},
        {"event_id": "E3", "sequence": 3, "step_id": "S3", "section": "assertions", "status": "passed", "required": True, "tool": "playwright", "evidence_refs": ["EV3"]},
    ]


class RunGovernanceTests(unittest.TestCase):
    def test_canonical_result_and_all_projections_are_consistent(self):
        result = aggregate_events(run=run_identity(), events=passed_events(), release_status="in_sync")
        self.assertEqual(result["overall_status"], "passed")
        self.assertEqual(validate_document(result, "run-result.schema.json"), [])
        projections = [project_run_result(result, item) for item in ("evidence-index", "report-model", "experience-candidate")]
        self.assertTrue(all(item["run_id"] == result["run_id"] and item["overall_status"] == result["overall_status"] for item in projections))
        self.assertTrue(all(item["read_only_projection"] for item in projections))

    def test_setup_failure_is_attributed_separately(self):
        events = passed_events()
        events[0]["status"] = "failed"
        result = aggregate_events(run=run_identity(), events=events, release_status="in_sync")
        self.assertIn("setup-navigation-failure", result["findings"])

    def test_write_success_verification_failure_never_resubmits_or_cleans(self):
        events = passed_events() + [{"event_id": "W1", "sequence": 4, "event_type": "write-outcome", "write_state": "write_succeeded_verification_failed", "submit_count": 1, "retained_test_data": {"object_ref": "sha256:synthetic", "cleanup_status": "not_planned_this_release"}}]
        result = aggregate_events(run=run_identity(), events=events, release_status="in_sync")
        self.assertEqual(result["overall_status"], "failed")
        self.assertEqual(result["submit_count"], 1)
        self.assertFalse(result["business_cleanup_attempted"])
        report = project_run_result(result, "report-model")
        self.assertEqual(report["cleanup_status"], "not_planned_this_release")

    def test_non_in_sync_release_blocks_consumption(self):
        result = aggregate_events(run=run_identity(), events=passed_events(), release_status="manual_drift")
        self.assertEqual(result["overall_status"], "blocked")

    def test_negative_experience_does_not_grant_permission(self):
        events = passed_events(); events[1]["status"] = "failed"
        experience = project_run_result(aggregate_events(run=run_identity(), events=events, release_status="in_sync"), "experience-candidate")
        self.assertEqual(experience["experience_status"], "negative")
        self.assertEqual(experience["permission_effect"], "none")
        self.assertTrue(experience["forbidden_reuse"])

    def test_first_pilot_delete_gate_requires_exact_unreferenced_inventory(self):
        inventory = [{"asset_ref": "legacy/a.py", "disposition_reason": "unmigratable", "referenced": False}]
        self.assertTrue(evaluate_pilot_delete(exact_inventory=inventory, reference_check_passed=True, pilot_status="first-pilot-active", action="delete-pilot-unmigratable")["allowed"])
        self.assertFalse(evaluate_pilot_delete(exact_inventory=None, reference_check_passed=True, pilot_status="first-pilot-active", action="delete-pilot-unmigratable")["allowed"])
        self.assertFalse(evaluate_pilot_delete(exact_inventory=inventory, reference_check_passed=True, pilot_status="completed", action="delete-pilot-unmigratable")["allowed"])

    def test_reconciliation_is_append_only_diagnostic_and_hash_bound(self):
        result = aggregate_events(run=run_identity(), events=passed_events(), release_status="in_sync")
        result["write_state"] = "write_outcome_unknown"  # Build a synthetic historical unknown outcome.
        result["run_result_hash"] = "sha256:" + "1" * 64  # Preserve a valid immutable source identity.
        before = copy.deepcopy(result)  # Prove the helper never rewrites canonical history.
        reconciliation = create_run_reconciliation(
            run_result=result,
            reconciled_write_state="write_failed",
            evidence=[{"ref": "evidence:after-submit.png", "sha256": "sha256:" + "2" * 64, "observation": "required-field-validation-visible"}],
            reason_code="client-validation-blocked-submission",
            created_at="2026-08-28T00:00:00Z",
        )
        self.assertEqual(result, before)  # Canonical RunResult remains byte-for-byte represented by the original object.
        self.assertEqual(reconciliation["reconciliation_effect"], "diagnostic-only")
        self.assertEqual(reconciliation["rerun_authorization_effect"], "none")
        self.assertEqual(validate_document(reconciliation, "run-reconciliation.schema.json"), [])

    def test_reconciliation_rejects_non_unknown_source(self):
        result = aggregate_events(run=run_identity(), events=passed_events(), release_status="in_sync")
        with self.assertRaisesRegex(ValueError, "E_RECONCILIATION_SOURCE_NOT_UNKNOWN"):
            create_run_reconciliation(run_result=result, reconciled_write_state="write_failed", evidence=[{"ref": "EV", "sha256": "sha256:" + "2" * 64, "observation": "validation"}], reason_code="not-unknown")

    def test_reconciliation_accepts_transient_submitted_unknown_from_historical_runtime(self):
        result = aggregate_events(run=run_identity(), events=passed_events(), release_status="in_sync")
        result["write_state"] = "submitted_unknown"  # Reproduce the historical post-submit verifier exception state.
        result["run_result_hash"] = "sha256:" + "3" * 64  # Preserve a valid historical identity.
        reconciliation = create_run_reconciliation(run_result=result, reconciled_write_state="write_succeeded_verified", evidence=[{"ref": "diagnostic:list-check.json", "sha256": "sha256:" + "4" * 64, "observation": "unique-title-visible-in-fresh-list-session"}], reason_code="fresh-read-only-list-verification", created_at="2026-08-28T00:00:00Z")
        self.assertEqual(reconciliation["original_write_state"], "submitted_unknown")
        self.assertEqual(validate_document(reconciliation, "run-reconciliation.schema.json"), [])


if __name__ == "__main__":
    unittest.main()
