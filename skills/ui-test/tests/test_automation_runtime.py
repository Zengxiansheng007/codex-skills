import unittest

from scripts.ui_test_core.automation_runtime import FlowDefinition, UiTestRuntime, exploration_entry_decision
from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.r2_policy import R2RunGuard, create_approval_record


class FakeContext:
    next_id = 0
    def __init__(self):
        type(self).next_id += 1
        self.context_id = f"ctx-{self.next_id}"
        self.events = []
        self.closed = False
    def close(self):
        self.closed = True


class AutomationRuntimeTests(unittest.TestCase):
    def test_each_manual_case_run_gets_fresh_context_and_full_flow(self):
        contexts = []
        def factory():
            context = FakeContext()
            contexts.append(context)
            return context
        flow = FlowDefinition("flow.login-and-open-create", 1, lambda context: context.events.extend(["login", "menu-navigation", "open-create"]))
        case = {"branch_id": "system", "precondition_flow_refs": [{"id": flow.flow_id, "version": 1}], "execute_feature": lambda context: context.events.append("feature")}
        runtime = UiTestRuntime(context_factory=factory, flows={flow.flow_id: flow}, case_registry={"CASE-A": case})
        first = runtime.execute_case(case_id="CASE-A", branch_id="system")
        second = runtime.execute_case(case_id="CASE-A", branch_id="system")
        self.assertNotEqual(first["context_id"], second["context_id"])
        self.assertEqual(first["navigation_mode"], "full-flow")
        self.assertEqual(contexts[0].events, ["login", "menu-navigation", "open-create", "feature"])
        self.assertTrue(all(context.closed for context in contexts))
        self.assertTrue(all(not item["business_cleanup_attempted"] for item in runtime.executions))

    def test_midscene_can_direct_route_only_with_current_ready_context(self):
        ready = {"session_id": "S1", "run_id": "R1", "handoff_status": "ready"}
        decision = exploration_entry_decision(module_ready_context=ready, current_session_id="S1", current_run_id="R1", formal_playwright=False)
        self.assertEqual(decision["mode"], "checkpoint-direct-route")
        self.assertFalse(decision["midscene_entry_clicks_allowed"])
        formal = exploration_entry_decision(module_ready_context=ready, current_session_id="S1", current_run_id="R1", formal_playwright=True)
        self.assertEqual(formal["mode"], "full-flow")
        mismatch = exploration_entry_decision(module_ready_context=ready, current_session_id="S2", current_run_id="R1", formal_playwright=False)
        self.assertTrue(mismatch["midscene_entry_clicks_allowed"])

    def test_r2_approval_is_current_run_ui_only_and_one_shot(self):
        approval = create_approval_record(approval_id="APR-1", run_id="RUN-1", case_id="CASE-A", environment="test", allowed_action="create-announcement", approved=True)
        self.assertEqual(validate_document(approval, "r2-approval-record.schema.json"), [])
        guard = R2RunGuard("RUN-1", "CASE-A", approval)
        self.assertTrue(guard.authorize(run_id="RUN-1", case_id="CASE-A", environment="test", action="create-announcement", channel="visible-ui")["allowed"])
        self.assertEqual(guard.authorize(run_id="RUN-1", case_id="CASE-A", environment="test", action="create-announcement", channel="visible-ui")["code"], "E_DOUBLE_SUBMIT_BLOCKED")
        outcome = guard.record_outcome("write_succeeded_verification_failed", retained_test_data={"cleanup_status": "not_planned_this_release"})
        self.assertFalse(outcome["retry_submit_allowed"])
        self.assertFalse(outcome["automatic_cleanup"])

    def test_r2_blocks_api_production_and_cross_run_reuse(self):
        approval = create_approval_record(approval_id="APR-1", run_id="RUN-1", case_id="CASE-A", environment="test", allowed_action="create-announcement", approved=True)
        for values, expected in [
            ({"run_id": "RUN-1", "case_id": "CASE-A", "environment": "test", "action": "create-announcement", "channel": "api"}, "E_R2_UI_TEST_ONLY"),
            ({"run_id": "RUN-1", "case_id": "CASE-A", "environment": "production", "action": "create-announcement", "channel": "visible-ui"}, "E_R2_UI_TEST_ONLY"),
            ({"run_id": "RUN-2", "case_id": "CASE-A", "environment": "test", "action": "create-announcement", "channel": "visible-ui"}, "E_R2_APPROVAL_BOUNDARY_MISMATCH"),
        ]:
            guard = R2RunGuard("RUN-1", "CASE-A", approval)
            self.assertEqual(guard.authorize(**values)["code"], expected)


if __name__ == "__main__":
    unittest.main()
