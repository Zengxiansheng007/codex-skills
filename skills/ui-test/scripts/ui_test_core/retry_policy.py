"""Bounded retry/fallback records with explicit changed-variable lineage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


NON_IDEMPOTENT_ACTIONS = {"submit", "update", "delete", "approve", "publish"}


@dataclass(frozen=True)
class RetryBudget:
    max_attempts: int = 3
    max_fallbacks: int = 1


def run_bounded(operation: Callable[[int], dict[str, Any]], budget: RetryBudget | None = None) -> dict[str, Any]:
    budget = budget or RetryBudget()
    attempts = []
    for number in range(1, budget.max_attempts + 1):
        result = dict(operation(number) or {})
        result.setdefault("attempt", number)
        attempts.append(result)
        if result.get("status") == "passed":
            return {"status": "passed" if number == 1 else "flaky", "attempts": attempts, "fallback_used": False}
    return {"status": "failed", "attempts": attempts, "fallback_used": False, "failure_code": "E_RETRY_EXHAUSTED"}


def record_fallback(*, reason: str, changed_variable: str, scope: str, result: str, attempt: int) -> dict[str, Any]:
    return {"reason": reason, "changed_variable": changed_variable, "scope": scope, "result": result, "attempt": attempt}


@dataclass
class ActionTokenLedger:
    consumed: set[str]

    def __init__(self) -> None:
        self.consumed = set()

    def consume(self, *, run_id: str, step_id: str, action: str, action_key: str) -> dict[str, Any]:
        key = f"{run_id}:{step_id}:{action}:{action_key}"
        if action in NON_IDEMPOTENT_ACTIONS and key in self.consumed:
            return {"allowed": False, "code": "E_DOUBLE_SUBMIT_BLOCKED", "action": action}
        if action in NON_IDEMPOTENT_ACTIONS:
            self.consumed.add(key)
        return {"allowed": True, "code": "OK", "action": action}


def retry_scope_for_action(action: str, phase: str) -> dict[str, Any]:
    if action in NON_IDEMPOTENT_ACTIONS and phase == "submit-action":
        return {"retry_allowed": False, "code": "E_NON_IDEMPOTENT_RETRY_FORBIDDEN"}
    if phase in {"pre-submit", "post-submit-query", "post-submit-assertion"}:
        return {"retry_allowed": True, "code": "OK"}
    return {"retry_allowed": action not in NON_IDEMPOTENT_ACTIONS, "code": "OK" if action not in NON_IDEMPOTENT_ACTIONS else "E_RETRY_SCOPE_REQUIRED"}
