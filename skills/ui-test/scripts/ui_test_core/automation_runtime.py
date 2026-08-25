"""Composable Flow/Page/Component runtime for independent pytest-playwright tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class AutomationRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class FlowDefinition:
    flow_id: str
    version: int
    execute: Callable[[Any], None]


class UiTestRuntime:
    def __init__(self, *, context_factory: Callable[[], Any], flows: dict[str, FlowDefinition], case_registry: dict[str, dict[str, Any]]) -> None:
        self.context_factory = context_factory
        self.flows = flows
        self.case_registry = case_registry
        self.executions: list[dict[str, Any]] = []

    def execute_case(self, *, case_id: str, branch_id: str | None) -> dict[str, Any]:
        case = self.case_registry.get(case_id)
        if case is None or case.get("branch_id") != branch_id:
            raise AutomationRuntimeError("E_CASE_RUNTIME_UNKNOWN")
        context = self.context_factory()
        context_id = str(getattr(context, "context_id", id(context)))
        trace = {"case_id": case_id, "branch_id": branch_id, "context_id": context_id, "navigation_mode": "full-flow", "flows": []}
        try:
            for reference in case.get("precondition_flow_refs", []):
                flow = self.flows.get(reference["id"])
                if flow is None or flow.version != reference["version"]:
                    raise AutomationRuntimeError("E_FLOW_VERSION_MISMATCH")
                flow.execute(context)
                trace["flows"].append({"id": flow.flow_id, "version": flow.version})
            case["execute_feature"](context)
            trace["status"] = "passed"
            return trace
        except Exception:
            trace["status"] = "failed"
            raise
        finally:
            close = getattr(context, "close", None)
            if callable(close):
                close()
            trace["context_closed"] = True
            trace["business_cleanup_attempted"] = False
            self.executions.append(trace)


def exploration_entry_decision(*, module_ready_context: dict[str, Any] | None, current_session_id: str, current_run_id: str, formal_playwright: bool) -> dict[str, Any]:
    if formal_playwright:
        return {"mode": "full-flow", "midscene_entry_clicks_allowed": False, "reason": "formal-playwright-always-replays-preconditions"}
    if not module_ready_context:
        return {"mode": "semantic-menu-exploration", "midscene_entry_clicks_allowed": True, "reason": "no-ready-context"}
    if module_ready_context.get("session_id") != current_session_id or module_ready_context.get("run_id") != current_run_id or module_ready_context.get("handoff_status") != "ready":
        return {"mode": "semantic-menu-exploration", "midscene_entry_clicks_allowed": True, "reason": "context-mismatch"}
    return {"mode": "checkpoint-direct-route", "midscene_entry_clicks_allowed": False, "reason": "current-session-module-ready"}
