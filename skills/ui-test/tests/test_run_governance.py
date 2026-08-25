import copy
import unittest

from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.migration import evaluate_pilot_delete
from scripts.ui_test_core.run_governance import aggregate_events, project_run_result


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


if __name__ == "__main__":
    unittest.main()
