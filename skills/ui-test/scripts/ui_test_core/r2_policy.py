"""Run-scoped UI-only R2 approval and one-shot write state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .case_contracts import canonical_hash


def create_approval_record(*, approval_id: str, run_id: str, case_id: str, environment: str, allowed_action: str, approved: bool) -> dict[str, Any]:
    boundary = {"run_id": run_id, "case_id": case_id, "environment": environment, "allowed_action": allowed_action, "channel": "visible-ui", "max_submit_count": 1}
    return {
        "schema_version": "ui-test.r2-approval-record.v1", "approval_id": approval_id,
        **boundary, "decision": "approved" if approved else "denied", "boundary_hash": canonical_hash(boundary),
        "credential_values_persisted": False, "reusable_across_runs": False,
    }


@dataclass
class R2RunGuard:
    run_id: str
    case_id: str
    approval: dict[str, Any]
    submit_count: int = 0
    write_state: str = "not_attempted"
    events: list[dict[str, Any]] = field(default_factory=list)

    def authorize(self, *, run_id: str, case_id: str, environment: str, action: str, channel: str) -> dict[str, Any]:
        boundary = {"run_id": run_id, "case_id": case_id, "environment": environment, "allowed_action": action, "channel": "visible-ui", "max_submit_count": 1}
        if environment != "test" or channel != "visible-ui":
            return self._deny("E_R2_UI_TEST_ONLY")
        if run_id != self.run_id or case_id != self.case_id or self.approval.get("boundary_hash") != canonical_hash(boundary):
            return self._deny("E_R2_APPROVAL_BOUNDARY_MISMATCH")
        if self.approval.get("decision") != "approved":
            return self._deny("E_R2_APPROVAL_REQUIRED")
        if action != self.approval.get("allowed_action"):
            return self._deny("E_R2_ACTION_NOT_APPROVED")
        if self.submit_count >= 1 or self.write_state != "not_attempted":
            return self._deny("E_DOUBLE_SUBMIT_BLOCKED")
        self.submit_count = 1
        self.write_state = "submitted_unknown"
        event = {"allowed": True, "code": "OK", "run_id": run_id, "action": action, "submit_count": self.submit_count}
        self.events.append(event)
        return event

    def record_outcome(self, outcome: str, *, retained_test_data: dict[str, Any] | None = None) -> dict[str, Any]:
        allowed = {"write_succeeded_verified", "write_succeeded_verification_failed", "write_failed", "write_outcome_unknown"}
        if outcome not in allowed or self.submit_count != 1:
            raise ValueError("E_R2_OUTCOME_INVALID")
        self.write_state = outcome
        return {
            "write_state": outcome, "submit_count": self.submit_count,
            "retry_submit_allowed": False, "post_submit_allowed_actions": ["query", "assert", "screenshot", "manual-diagnosis"],
            "retained_test_data": retained_test_data or [], "automatic_cleanup": False,
        }

    def _deny(self, code: str) -> dict[str, Any]:
        event = {"allowed": False, "code": code, "run_id": self.run_id, "submit_count": self.submit_count}
        self.events.append(event)
        return event
