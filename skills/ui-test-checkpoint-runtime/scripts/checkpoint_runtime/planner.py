from __future__ import annotations

from typing import Any

from .failure import failure_attribution
from .models import RuntimePlan, RuntimeTarget
from .policy import action_is_forbidden, auth_is_expired, risk_allowed


def _checkpoint_by_id(checkpoint_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item.get("checkpoint_id"): item
        for item in checkpoint_index.get("checkpoints", [])
        if isinstance(item, dict) and item.get("checkpoint_id")
    }


class RecoveryPlanner:
    def build_plan(
        self,
        target: RuntimeTarget,
        module_manifest: dict[str, Any],
        checkpoint_index: dict[str, Any],
        auth_ref: dict[str, Any],
        run_id: str,
        correlation_id: str,
    ) -> RuntimePlan:
        if auth_is_expired(auth_ref):
            return RuntimePlan(
                target=target,
                chain=[],
                run_id=run_id,
                correlation_id=correlation_id,
                blocked=True,
                block_reason="auth-ref-expired",
                failure_attribution=failure_attribution("auth-expired", "auth_ref_expired", "auth_ref is expired or lacks expires_at"),
            )

        by_id = _checkpoint_by_id(checkpoint_index)
        chain_ids = list(module_manifest.get("entry_chain", []))
        if target.function_button_id:
            button = self._find_button(module_manifest, target.function_button_id)
            if button is None:
                return RuntimePlan(
                    target=target,
                    chain=[],
                    run_id=run_id,
                    correlation_id=correlation_id,
                    blocked=True,
                    block_reason="unknown-function-button",
                    failure_attribution=failure_attribution("requirement-ambiguity", "missing_button", target.function_button_id),
                )
            risk_level = button.get("risk_level")
            allowed_action = button.get("allowed_action")
            forbidden_actions = button.get("forbidden_actions", [])
            if not risk_allowed(risk_level) or action_is_forbidden(allowed_action, forbidden_actions):
                return RuntimePlan(
                    target=target,
                    chain=[],
                    run_id=run_id,
                    correlation_id=correlation_id,
                    blocked=True,
                    block_reason="blocked-write-checkpoint",
                    failure_attribution=failure_attribution(
                        "safety-policy",
                        "blocked_write_action",
                        f"button {target.function_button_id} is not an R0/R1 read-only action",
                    ),
                )
            checkpoint_ref = button.get("checkpoint_ref", "")
            checkpoint_id = checkpoint_ref.split("/")[-2] if "/" in checkpoint_ref else f"CP4-{target.function_button_id}"
            chain_ids.append(checkpoint_id)

        chain: list[dict[str, Any]] = []
        for checkpoint_id in chain_ids:
            item = by_id.get(checkpoint_id, {"checkpoint_id": checkpoint_id, "status": "unknown"})
            if item.get("status") in {"stale", "failed", "blocked"}:
                return RuntimePlan(
                    target=target,
                    chain=chain,
                    run_id=run_id,
                    correlation_id=correlation_id,
                    blocked=True,
                    block_reason=f"checkpoint-{item.get('status')}",
                    failure_attribution=failure_attribution("test-asset", "checkpoint_stale", f"{checkpoint_id} status is {item.get('status')}"),
                )
            if not risk_allowed(item.get("risk_level", "R1")):
                return RuntimePlan(
                    target=target,
                    chain=chain,
                    run_id=run_id,
                    correlation_id=correlation_id,
                    blocked=True,
                    block_reason="risk-not-allowed",
                    failure_attribution=failure_attribution("safety-policy", "risk_not_allowed", checkpoint_id),
                )
            chain.append(item)
        return RuntimePlan(target=target, chain=chain, run_id=run_id, correlation_id=correlation_id)

    @staticmethod
    def _find_button(module_manifest: dict[str, Any], button_id: str) -> dict[str, Any] | None:
        for button in module_manifest.get("function_buttons", []):
            if isinstance(button, dict) and button.get("button_id") == button_id:
                return button
        return None
