import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ui_test_core.case_contracts import lower_to_case_ir
from scripts.ui_test_core.compiler import (
    CompileError, affected_cases, build_dependency_graph, compile_case, create_compile_plan,
    retention_metadata, sync_release, validate_release,
)
from tests.test_case_contracts import source_case


def registry():
    return {"assets": [
        {"id": "flow.login-and-open-create", "type": "flow", "version": 1, "depends_on": ["page.login", "page.announcement-create"], "content": {"steps": ["login", "navigate"]}},
        {"id": "page.login", "type": "page", "version": 1, "depends_on": [], "content": {"class": "LoginPage"}},
        {"id": "page.announcement-create", "type": "page", "version": 1, "depends_on": ["component.plain-content"], "content": {"class": "AnnouncementCreatePage"}},
        {"id": "component.plain-content", "type": "component", "version": 1, "depends_on": [], "content": {"class": "PlainContent"}},
        {"id": "component.plain-content.fill", "type": "binding", "version": 1, "depends_on": ["component.plain-content"], "action": "fill", "risk_level": "R1", "target": "PlainContent.fill"},
        {"id": "component.plain-content.assert", "type": "binding", "version": 1, "depends_on": ["component.plain-content"], "action": "assert", "risk_level": "R1", "target": "PlainContent.assert_value"},
    ]}


def graph_and_ir():
    source = source_case()
    case_ir = lower_to_case_ir(source)
    refs = [item["id"] for item in source["precondition_flow_refs"] + source["page_object_refs"] + source["component_refs"]]
    refs += case_ir["binding_refs"]
    graph = build_dependency_graph(registry(), [{"case_id": source["case_id"], "dependency_refs": refs}, {"case_id": "OTHER", "dependency_refs": ["page.login"]}])
    return graph, case_ir


def compiled_case():
    graph, case_ir = graph_and_ir()
    return compile_case(case_ir, graph, compiler_version="1.0.0", renderer_version="1.0.0", schema_version="1", config_fingerprint="sha256:" + "a" * 64)


class CompilerTests(unittest.TestCase):
    def test_reverse_dependency_closure_is_precise(self):
        graph, _ = graph_and_ir()
        result = affected_cases(graph, ["component.plain-content"])
        self.assertEqual(result["affected_cases"], ["BOPS-ANNOUNCEMENT-P0-A"])
        self.assertIn("page.announcement-create", result["affected_assets"])
        self.assertNotIn("OTHER", result["affected_cases"])

    def test_dependency_cycle_is_rejected(self):
        value = registry()
        value["assets"][1]["depends_on"] = ["flow.login-and-open-create"]
        with self.assertRaisesRegex(CompileError, "E_DEPENDENCY_CYCLE"):
            build_dependency_graph(value, [])

    def test_all_renderers_share_identity_and_sections(self):
        compiled = compiled_case()
        metadata = compiled["outputs"]["midscene.json"]["metadata"]
        self.assertEqual(metadata["source_hash"], compiled["manifest"]["source_hash"])
        self.assertEqual(metadata["build_fingerprint"], compiled["manifest"]["build_fingerprint"])
        human = compiled["outputs"]["human.md"]
        self.assertIn("| \u53c2\u6570/\u6570\u636e |", human)
        self.assertIn("| \u5e8f\u53f7 | \u64cd\u4f5c | \u53c2\u6570/\u6570\u636e | \u9884\u671f\u7ed3\u679c |", human)
        self.assertIn("shared_account.test_zwz", human)
        self.assertIn("\u7d22\u5f15\uff1a", human)
        self.assertNotIn("锛?", human)
        self.assertEqual(compiled["outputs"]["midscene.json"]["sections"]["setup"][0]["parameters"][0]["index_ref"], "D:\\UI-Test\\tianjin__天津项目组\\ops-platform__运营管理平台\\_shared\\data\\account-index.yaml#shared_account.test_zwz")
        self.assertIn("pytest.mark.p0", compiled["outputs"]["playwright-test.py"])
        self.assertIn("ui_test_runtime.execute_case", compiled["outputs"]["playwright-test.py"])
        from scripts.ui_test_core.case_contracts import validate_document
        self.assertEqual(validate_document(compiled["manifest"], "case-manifest.schema.json"), [])
        self.assertEqual(validate_document(compiled["compile_receipt"], "compile-receipt.schema.json"), [])

    def test_binding_missing_and_incompatible_fail_closed(self):
        graph, case_ir = graph_and_ir()
        graph["case_refs"][case_ir["case_id"]].remove("component.plain-content.fill")
        with self.assertRaisesRegex(CompileError, "E_BINDING_MISSING"):
            compile_case(case_ir, graph, compiler_version="1", renderer_version="1", schema_version="1", config_fingerprint="c")
        graph, case_ir = graph_and_ir()
        graph["assets"]["component.plain-content.fill"]["action"] = "click"
        with self.assertRaisesRegex(CompileError, "E_BINDING_INCOMPATIBLE"):
            compile_case(case_ir, graph, compiler_version="1", renderer_version="1", schema_version="1", config_fingerprint="c")

    def test_plan_sync_noop_stale_concurrent_and_manual_drift(self):
        compiled = compiled_case()
        with tempfile.TemporaryDirectory() as directory:
            plan = create_compile_plan(compiled, None)
            first = sync_release(directory, plan, compiled)
            self.assertEqual(first["status"], "in_sync")
            second = sync_release(directory, create_compile_plan(compiled, compiled["manifest"]["build_fingerprint"]), compiled)
            self.assertTrue(second["no_op"])
            stale = copy.deepcopy(plan)
            stale["input_fingerprint"] = "sha256:" + "0" * 64
            self.assertEqual(sync_release(directory, stale, compiled)["status"], "plan_stale")
            self.assertEqual(sync_release(directory, create_compile_plan(compiled, None), compiled)["status"], "concurrent_update")
            release = Path(first["release_path"])
            (release / "human.md").write_text("manual change", encoding="utf-8")
            self.assertEqual(validate_release(directory)["status"], "manual_drift")

    def test_generation_failure_preserves_previous_active(self):
        first_compiled = compiled_case()
        with tempfile.TemporaryDirectory() as directory:
            first = sync_release(directory, create_compile_plan(first_compiled, None), first_compiled)
            graph, case_ir = graph_and_ir()
            graph["assets"]["page.announcement-create"]["version"] = 2
            second_compiled = compile_case(case_ir, graph, compiler_version="1.0.0", renderer_version="1.0.0", schema_version="1", config_fingerprint="sha256:" + "a" * 64)
            failed = sync_release(directory, create_compile_plan(second_compiled, first_compiled["manifest"]["build_fingerprint"]), second_compiled, fail_after_files=1)
            self.assertEqual(failed["status"], "generation_failed")
            active = json.loads((Path(directory) / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(active["build_fingerprint"], first_compiled["manifest"]["build_fingerprint"])

    def test_retention_and_hold_are_calculated_without_deletion(self):
        ordinary = retention_metadata("ordinary_raw_evidence", "2026-01-01T00:00:00Z")
        failure = retention_metadata("failure", "2026-01-01T00:00:00Z", reference_hold=True)
        governance = retention_metadata("governance_decision", "2026-01-01T00:00:00Z", product_retired_at="2030-01-01T00:00:00Z")
        self.assertTrue(ordinary["retain_until"].startswith("2026-06-30"))
        self.assertTrue(failure["hold"])
        self.assertTrue(governance["retain_until"].startswith("2031-01-01"))
        self.assertFalse(any(item["automatic_delete"] for item in (ordinary, failure, governance)))


if __name__ == "__main__":
    unittest.main()
