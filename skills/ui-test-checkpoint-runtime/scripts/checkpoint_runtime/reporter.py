from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import stable_sha256, write_json
from .models import RuntimePlan, utc_now_iso
from .policy import reportable_auth_ref


class EvidenceReporter:
    def build_report(self, plan: RuntimePlan, auth_ref: dict[str, Any], mode: str = "dry-run", execution_result: dict[str, Any] | None = None) -> dict[str, Any]:
        status = "blocked" if plan.blocked else "planned"
        if execution_result:
            status = execution_result.get("result", status)
        evidence_note = (
            "Dry-run mode does not execute browser actions or capture private UI evidence."
            if mode == "dry-run"
            else "Live public mode captured browser evidence against public sites only."
        )
        evidence_index = {
            "schema_version": "checkpoint-runtime.evidence-index.v1",
            "run_id": plan.run_id,
            "correlation_id": plan.correlation_id,
            "artifacts": execution_result.get("artifacts", []) if execution_result else [],
            "redaction": {
                "storage_state_included": False,
                "cookies_included": False,
                "tokens_included": False,
            },
            "note": evidence_note,
        }
        return {
            "schema_version": "checkpoint-runtime.report.v1",
            "run_id": plan.run_id,
            "correlation_id": plan.correlation_id,
            "generated_at": utc_now_iso(),
            "mode": mode,
            "target": {
                "system_id": plan.target.system_id,
                "module_id": plan.target.module_id,
                "function_button_id": plan.target.function_button_id,
                "environment_alias": plan.target.environment_alias,
                "project_group": plan.target.project_group,
                "product": plan.target.product,
                "function": plan.target.function,
                "checkpoint": plan.target.checkpoint,
                "risk_level": plan.target.risk_level,
            },
            "result": status,
            "executed_chain": [item.get("checkpoint_id") for item in plan.chain],
            "blocked": plan.blocked or bool(execution_result and execution_result.get("blocked_requests")),
            "block_reason": plan.block_reason,
            "failure_attribution": plan.failure_attribution or (execution_result or {}).get("failure_attribution"),
            "auth_ref": reportable_auth_ref(auth_ref),
            "evidence": evidence_index,
            "playwright": self._sanitize_execution_result(execution_result),
            "module_ready_context": (execution_result or {}).get("module_ready_context"),
            "report_hash": None,
            "promotion_recommendation": (
                "validated" if execution_result and execution_result.get("result") == "passed"
                else "blocked" if execution_result
                else "not-applicable-dry-run"
            ),
        }

    def write_report(self, out_path: Path, report: dict[str, Any]) -> None:
        report["report_hash"] = stable_sha256({key: value for key, value in report.items() if key != "report_hash"})
        write_json(out_path, report)

    @staticmethod
    def _sanitize_execution_result(execution_result: dict[str, Any] | None) -> dict[str, Any] | None:
        if not execution_result:
            return None
        return {
            "schema_version": execution_result.get("schema_version"),
            "result": execution_result.get("result"),
            "assertions": execution_result.get("assertions", []),
            "blocked_requests": execution_result.get("blocked_requests", []),
            "request_failures": execution_result.get("request_failures", []),
            "node_exit_code": execution_result.get("node_exit_code"),
            "module_signature": execution_result.get("module_signature"),
            "module_ready_context": execution_result.get("module_ready_context"),
            "semantic_readonly_post_count": execution_result.get("semantic_readonly_post_count", 0),
            "semantic_readonly_post_decisions": execution_result.get("semantic_readonly_post_decisions", []),
        }
