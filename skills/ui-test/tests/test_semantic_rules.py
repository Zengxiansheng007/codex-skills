"""Tests for ST-TOTAL-0402 Semantic Rule Registry and Issue List.

Covers: scope consistency, A/B content-component variant, assertion target
mismatch, P0 responsibility, R2 one-submit boundary, shared-data index_ref,
and <br> parameter atomization.
"""

from __future__ import annotations

import unittest

from scripts.ui_test_core.case_contracts import lower_to_case_ir, validate_source_case
from scripts.ui_test_core.semantic_rules import (
    RULE_IDS,
    has_blocking_issues,
    validate_p0_suite,
    validate_semantics,
)
from tests.fixtures_semantic import (
    fixture_a_plain_valid,
    fixture_a_popup_version_assertion,
    fixture_a_rich_content_component,
    fixture_b_plain_content_component,
    fixture_b_rich_valid,
    fixture_br_parameter_aggregation,
    fixture_missing_p0_responsibility,
    fixture_missing_shared_data_index_ref,
    fixture_r2_multi_submit,
)


class SemanticRuleRegistryTests(unittest.TestCase):
    def test_rule_registry_contains_all_required_rule_ids(self):
        expected = {
            "SEM-SCOPE-001",
            "SEM-VARIANT-001",
            "SEM-ASSERT-001",
            "SEM-P0-001",
            "SEM-R2-001",
            "SEM-DATA-001",
            "SEM-ATOM-001",
        }
        self.assertTrue(expected.issubset(set(RULE_IDS)))

    def test_positive_a_plain_has_no_blocking_issues(self):
        issues = validate_semantics(fixture_a_plain_valid())
        self.assertFalse(has_blocking_issues(issues), [i["issue_id"] for i in issues if i["blocking"]])

    def test_positive_b_rich_has_no_blocking_issues(self):
        issues = validate_semantics(fixture_b_rich_valid())
        self.assertFalse(has_blocking_issues(issues), [i["issue_id"] for i in issues if i["blocking"]])

    def test_project_popup_branch_alias_is_validated(self):
        sc = fixture_b_rich_valid()
        sc["branch_id"] = "popup-announcement"
        sc["steps"]["assertions"][0]["expected_result"] = "plain content matches"
        issues = validate_semantics(sc)
        self.assertIn("SEM-ASSERT-002", {i["rule_id"] for i in issues if i["blocking"]})

    def test_a_with_rich_content_component_is_blocked(self):
        issues = validate_semantics(fixture_a_rich_content_component())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-VARIANT-001", rule_ids)

    def test_a_with_popup_version_assertion_is_blocked(self):
        issues = validate_semantics(fixture_a_popup_version_assertion())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-ASSERT-001", rule_ids)

    def test_b_with_plain_content_component_is_blocked(self):
        issues = validate_semantics(fixture_b_plain_content_component())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-VARIANT-001", rule_ids)

    def test_missing_p0_responsibility_is_blocked(self):
        issues = validate_semantics(fixture_missing_p0_responsibility())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-P0-001", rule_ids)

    def test_missing_shared_data_index_ref_is_blocked(self):
        issues = validate_semantics(fixture_missing_shared_data_index_ref())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-DATA-001", rule_ids)

    def test_br_parameter_aggregation_is_blocked(self):
        issues = validate_semantics(fixture_br_parameter_aggregation())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-ATOM-001", rule_ids)

    def test_r2_multi_submit_is_blocked(self):
        issues = validate_semantics(fixture_r2_multi_submit())
        rule_ids = {i["rule_id"] for i in issues if i["blocking"]}
        self.assertIn("SEM-R2-002", rule_ids)

    def test_chinese_popup_version_assertion_is_blocked(self):
        sc = fixture_a_plain_valid()
        sc["steps"]["assertions"][0]["expected_result"] = "弹窗公告版本为最新"
        issues = validate_semantics(sc)
        self.assertIn("SEM-ASSERT-001", {i["rule_id"] for i in issues if i["blocking"]})

    def test_p0_joint_coverage_accepts_a_and_b_families(self):
        issues = validate_p0_suite([fixture_a_plain_valid(), fixture_b_rich_valid()])
        self.assertFalse(has_blocking_issues(issues), issues)

    def test_p0_joint_coverage_rejects_uncovered_family(self):
        sc = fixture_a_plain_valid()
        sc["test_points"][0]["responsibility"] = "not-applicable"
        sc["test_points"][0]["coverage_method"] = "not-applicable"
        issues = validate_p0_suite([sc])
        self.assertIn("SEM-P0-002", {i["rule_id"] for i in issues if i["blocking"]})


class IssueSchemaTests(unittest.TestCase):
    def test_every_issue_has_all_required_keys(self):
        fixtures = [
            fixture_a_plain_valid(),
            fixture_b_rich_valid(),
            fixture_a_rich_content_component(),
            fixture_a_popup_version_assertion(),
            fixture_b_plain_content_component(),
            fixture_missing_p0_responsibility(),
            fixture_missing_shared_data_index_ref(),
            fixture_br_parameter_aggregation(),
            fixture_r2_multi_submit(),
        ]
        required_keys = {
            "issue_id", "rule_id", "severity", "case_id", "branch_id",
            "source_path", "message", "expected", "actual", "suggested_fix",
            "blocking", "evidence_refs",
        }
        for sc in fixtures:
            for issue in validate_semantics(sc):
                missing = required_keys - set(issue.keys())
                self.assertFalse(missing, f"Issue {issue.get('issue_id')} missing keys: {missing}")

    def test_issue_list_is_stably_sorted(self):
        issues = validate_semantics(fixture_a_rich_content_component())
        sev_order = {"P0": 0, "P1": 1, "P2": 2, "info": 3}
        keys = [
            (sev_order.get(i["severity"], 99), i["case_id"], i.get("branch_id") or "", i["rule_id"], i["source_path"], i["issue_id"])
            for i in issues
        ]
        self.assertEqual(keys, sorted(keys))


class LoweringIntegrationTests(unittest.TestCase):
    def test_valid_a_plain_lowers_without_error(self):
        ir = lower_to_case_ir(fixture_a_plain_valid())
        self.assertEqual(ir["case_id"], "FIXTURE-A-PLAIN-001")

    def test_valid_b_rich_lowers_without_error(self):
        ir = lower_to_case_ir(fixture_b_rich_valid())
        self.assertEqual(ir["case_id"], "FIXTURE-B-RICH-001")

    def test_a_rich_content_blocks_lowering(self):
        with self.assertRaises(ValueError):
            lower_to_case_ir(fixture_a_rich_content_component())

    def test_missing_p0_responsibility_blocks_lowering(self):
        with self.assertRaises(ValueError):
            lower_to_case_ir(fixture_missing_p0_responsibility())

    def test_br_aggregation_blocks_lowering(self):
        with self.assertRaises(ValueError):
            lower_to_case_ir(fixture_br_parameter_aggregation())

    def test_existing_source_case_still_lowers(self):
        from tests.test_case_contracts import source_case
        ir = lower_to_case_ir(source_case())
        self.assertEqual(ir["case_id"], "BOPS-ANNOUNCEMENT-P0-A")


if __name__ == "__main__":
    unittest.main()
