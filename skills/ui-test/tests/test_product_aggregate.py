import copy
import unittest

from scripts.ui_test_core.case_contracts import lower_to_case_ir, validate_document
from scripts.ui_test_core.product_aggregate import AggregateError, render_product_aggregate
from tests.fixtures_semantic import fixture_a_plain_valid, fixture_b_rich_valid


def _entry(source_case):
    case_ir = lower_to_case_ir(source_case)
    return {"case_ir": case_ir, "manifest": {"status": "in_sync", "source_hash": case_ir["source_hash"]}}


class ProductAggregateTests(unittest.TestCase):
    def test_markdown_and_outline_are_generated_from_both_cases(self):
        result = render_product_aggregate(
            [_entry(fixture_b_rich_valid()), _entry(fixture_a_plain_valid())],
            display_registry=_registry(product="运维管理系统", system="运维管理系统"),
        )
        markdown = next(value for name, value in result["outputs"].items() if name.endswith(".md"))
        self.assertIn("运维管理系统.总测试用例.outline.json", result["outputs"])
        outline = result["outline"]
        self.assertIn("# 天津项目组", markdown)
        self.assertIn("  - 运维管理系统", markdown)
        self.assertIn("  - 运维管理系统", markdown)
        self.assertIn("公共前置操作", markdown)
        self.assertEqual(markdown.count("公共前置操作"), 1)
        self.assertIn("\u53c2\u6570/\u6570\u636e", markdown)
        self.assertIn("\u9884\u671f\uff1a", markdown)
        self.assertNotIn("锛?", markdown)
        self.assertIn("FIXTURE-A-PLAIN-001", markdown)
        self.assertIn("FIXTURE-B-RICH-001", markdown)
        self.assertEqual(validate_document(outline, "product-outline.schema.json"), [])
        self.assertEqual(validate_document(result["manifest"], "product-aggregate-manifest.schema.json"), [])
        case_nodes = _find_nodes(outline, "case")
        self.assertEqual(len(case_nodes), 2)
        operations = _find_nodes(outline, "operation")
        parameter_nodes = _find_nodes(outline, "parameters")
        self.assertEqual(len(operations), len(parameter_nodes))
        self.assertTrue(all(node["children"] for node in parameter_nodes))

    def test_each_parameter_is_atomic_and_does_not_use_br(self):
        source = fixture_a_plain_valid()
        source["steps"]["feature"][0]["parameters"][0]["display_value"] = "A; B"
        result = render_product_aggregate([_entry(source)], display_registry=_registry())
        markdown = next(value for name, value in result["outputs"].items() if name.endswith(".md"))
        self.assertNotIn("<br>", markdown)
        self.assertIn("A; B", markdown)

    def test_stale_case_is_rejected(self):
        entry = _entry(fixture_a_plain_valid())
        entry["manifest"]["status"] = "dependency_stale"
        with self.assertRaisesRegex(AggregateError, "E_AGGREGATE_CASE_NOT_IN_SYNC"):
            render_product_aggregate([entry], display_registry=_registry())

    def test_source_hash_mismatch_is_rejected(self):
        entry = _entry(fixture_a_plain_valid())
        entry["manifest"]["source_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(AggregateError, "E_AGGREGATE_SOURCE_HASH_MISMATCH"):
            render_product_aggregate([entry], display_registry=_registry())

    def test_uncovered_p0_family_is_rejected(self):
        source = fixture_a_plain_valid()
        source["test_points"].append({
            "test_point_id": "uncovered-family/example",
            "responsibility": "not-applicable",
            "coverage_method": "not-applicable",
            "variant": "plain-text",
            "assertion_refs": [],
        })
        with self.assertRaisesRegex(AggregateError, "E_AGGREGATE_P0_COVERAGE"):
            render_product_aggregate([_entry(source)], display_registry=_registry())

    def test_scope_mismatch_is_rejected(self):
        a = fixture_a_plain_valid()
        b = copy.deepcopy(a)
        b["case_id"] = "OTHER-CASE"
        b["scope"]["module_path"] = ["announcement", "other-module"]
        with self.assertRaisesRegex(AggregateError, "E_AGGREGATE_SCOPE_MISMATCH"):
            render_product_aggregate([_entry(a), _entry(b)], display_registry=_registry())

    def test_product_and_system_same_display_name_are_kept_as_two_nodes(self):
        result = render_product_aggregate([_entry(fixture_a_plain_valid())], display_registry=_registry(product="运维管理系统", system="运维管理系统"))
        root = result["outline"]
        self.assertEqual(root["children"][0]["label"], "运维管理系统")
        self.assertEqual(root["children"][0]["children"][0]["label"], "运维管理系统")

    def test_special_precondition_is_rendered_only_under_its_case(self):
        source = fixture_a_plain_valid()
        source["special_preconditions"] = [{
            "step_id": "S-SPECIAL", "intent": "prepare special state", "action": "assert",
            "expected_result": "special state ready", "risk_level": "R1", "required": True,
            "parameters": [], "evidence": [], "forbidden_actions": [],
        }]
        result = render_product_aggregate([_entry(source)], display_registry=_registry())
        markdown = next(value for name, value in result["outputs"].items() if name.endswith(".md"))
        self.assertIn("特殊前置操作", markdown)


def _find_nodes(node, node_type):
    found = []
    if node.get("node_type") == node_type:
        found.append(node)
    for child in node.get("children", []):
        found.extend(_find_nodes(child, node_type))
    return found


def _registry(product="测试产品", system="测试系统"):
    return {
        "project_groups": {"test-group": "天津项目组"},
        "products": {"test-platform": product},
        "systems": {"test-config": system},
        "modules": {"message": "消息管理", "announcement": "公告管理"},
        "functions": {"create": "创建"},
    }


if __name__ == "__main__":
    unittest.main()
