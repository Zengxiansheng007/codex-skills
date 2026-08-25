import copy
import unittest

from scripts.ui_test_core.case_contracts import canonical_hash, lower_to_case_ir, validate_document, validate_source_case


def source_case():
    return {
        "schema_version": "ui-test.source-case.v1",
        "case_id": "BOPS-ANNOUNCEMENT-P0-A",
        "case_version": 1,
        "title": "Create system announcement",
        "display_name": "创建系统公告核心冒烟",
        "status": "approved",
        "priority": "P0",
        "p0_suite_id": "BOPS-ANNOUNCEMENT-CREATE-P0",
        "branch_id": "system-announcement",
        "scope": {"project_group": "tianjin", "product": "ops-platform", "product_aliases": ["ops"], "system": "ops-config", "module_path": ["message", "announcement"], "function": "create"},
        "risk": {"risk_level": "R2", "write_action": "create-announcement", "max_submit_count": 1, "environment_allowlist": ["test"], "ui_only": True, "forbidden_actions": ["api-create", "production"]},
        "precondition_group": "announcement-create-common",
        "precondition_flow_refs": [{"id": "flow.login-and-open-create", "version": 1}],
        "special_preconditions": [],
        "page_object_refs": [{"id": "page.announcement-create", "version": 1}],
        "component_refs": [{"id": "component.plain-content", "version": 1}],
        "test_points": [{"test_point_id": "announcement-content/plain", "responsibility": "primary", "coverage_method": "operation", "variant": "plain-text", "assertion_refs": ["A-CONTENT"]}],
        "steps": {
            "setup": [{
                "step_id": "S-LOGIN", "intent": "reach create page", "action": "flow", "binding_ref": "flow.login-and-open-create",
                "parameters": [{"label": "登录账号", "display_value": "shared_account.test_zwz", "source_type": "shared-data", "index_ref": "D:\\UI-Test\\tianjin__天津项目组\\ops-platform__运营管理平台\\_shared\\data\\account-index.yaml#shared_account.test_zwz", "sensitive": True}],
                "expected_result": "create page ready", "risk_level": "R1", "required": True, "evidence": ["screenshot"], "forbidden_actions": []
            }],
            "feature": [{
                "step_id": "S-FILL", "intent": "fill content", "action": "fill", "binding_ref": "component.plain-content.fill",
                "parameters": [{"label": "公告内容", "display_value": "示例公告内容", "source_type": "literal", "sensitive": False}],
                "expected_result": "content visible", "risk_level": "R1", "required": True, "evidence": ["field-state"], "forbidden_actions": []
            }],
            "assertions": [{"step_id": "S-ASSERT", "intent": "verify content", "action": "assert", "binding_ref": "component.plain-content.assert", "expected_result": "content matches", "risk_level": "R1", "required": True, "evidence": ["field-state"], "forbidden_actions": []}]
        },
        "data_rules": {"expiry_offset_days": 1},
        "generation": {"human": True, "midscene": True, "resolved": True, "playwright": True},
        "source_refs": ["REQ-ANNOUNCEMENT-CREATE"]
    }


class CaseContractTests(unittest.TestCase):
    def test_source_case_is_valid_and_lowers_to_valid_ir(self):
        source = source_case()
        self.assertEqual(validate_source_case(source), [])
        ir = lower_to_case_ir(source)
        self.assertEqual(validate_document(ir, "case-ir.schema.json"), [])
        self.assertEqual(ir["normalized_steps"][0]["section"], "setup")
        self.assertEqual(ir["binding_refs"], sorted(ir["binding_refs"]))

    def test_hash_ignores_key_order_but_changes_on_semantic_change(self):
        source = source_case()
        reordered = dict(reversed(list(source.items())))
        self.assertEqual(canonical_hash(source), canonical_hash(reordered))
        changed = copy.deepcopy(source)
        changed["title"] = "Changed business title"
        self.assertNotEqual(canonical_hash(source), canonical_hash(changed))

    def test_p0_requires_suite_and_branch(self):
        source = source_case()
        source.pop("p0_suite_id")
        self.assertTrue(validate_source_case(source))

    def test_r2_requires_ui_only_single_submit(self):
        source = source_case()
        source["risk"]["max_submit_count"] = 2
        source["risk"]["ui_only"] = False
        self.assertTrue(validate_source_case(source))

    def test_primary_point_cannot_be_not_applicable(self):
        source = source_case()
        source["test_points"][0]["coverage_method"] = "not-applicable"
        codes = {item["code"] for item in validate_source_case(source)}
        self.assertIn("TEST_POINT_COVERAGE_REQUIRED", codes)

    def test_runtime_approval_and_credentials_are_forbidden(self):
        source = source_case()
        source["approval_token"] = "runtime-only"
        codes = {item["code"] for item in validate_source_case(source)}
        self.assertIn("SOURCE_CASE_RUNTIME_STATE_FORBIDDEN", codes)

    def test_step_ids_are_unique_across_sections(self):
        source = source_case()
        source["steps"]["feature"][0]["step_id"] = "S-LOGIN"
        codes = {item["code"] for item in validate_source_case(source)}
        self.assertIn("SOURCE_STEP_ID_DUPLICATE", codes)

    def test_shared_data_parameters_require_index_ref(self):
        source = source_case()
        source["steps"]["setup"][0]["parameters"][0].pop("index_ref")
        codes = {item["code"] for item in validate_source_case(source)}
        self.assertIn("STEP_SHARED_DATA_INDEX_REQUIRED", codes)


if __name__ == "__main__":
    unittest.main()
