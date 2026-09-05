"""Requirement traceability and final completion gate."""

from __future__ import annotations

from typing import Any, Iterable

from .pycharm_acceptance import validate_pycharm_acceptance_chain


def validate_rtm(rows: Iterable[dict[str, Any]], required_ids: set[str]) -> dict[str, Any]:
    rows = list(rows)
    seen = {str(row.get("requirement_id")) for row in rows if row.get("requirement_id")}
    missing = sorted(required_ids - seen)
    invalid = [row.get("requirement_id") for row in rows if not row.get("story_id") or not row.get("test_refs") or not row.get("evidence_refs")]
    return {"valid": not missing and not invalid, "missing": missing, "invalid": invalid, "row_count": len(rows)}


def evaluate_release(
    *,
    rtm: dict[str, Any],
    run_result: dict[str, Any],
    tests_ok: bool,
    sensitive_scan: dict[str, Any],
    public_pilot: dict[str, Any],
    migration_ok: bool | None = None,
    migration_status: str | None = None,
    global_install_authorized: bool = False,
    xmind_golden: dict[str, Any] | None = None,
    finalization_receipt: dict[str, Any] | None = None,
    pytest_session_result: dict[str, Any] | None = None,
    acceptance_result: dict[str, Any] | None = None,
    acceptance_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = []
    if not rtm.get("valid"): blockers.append("rtm-invalid")
    if run_result.get("overall_status") != "passed": blockers.append("run-result-not-passed")
    if run_result.get("schema_version") == "ui-test.run-result.v5":
        # V5只表达节点内业务事实，不能再被当作PyCharm或人工R2完成证明。
        if (finalization_receipt or {}).get("status") != "committed":
            blockers.append("finalization-receipt-not-committed")
        if (finalization_receipt or {}).get("recovery_mode") != "none":
            blockers.append("finalization-recovered-post-run")
        if (pytest_session_result or {}).get("pytest_exitstatus") != 0:
            blockers.append("pytest-session-exit-not-zero")
        acceptance = acceptance_result or {}
        acceptance_status = acceptance.get("overall_status", acceptance.get("verdict"))
        if acceptance_status != "passed" or acceptance.get("observed_process_exit_code") != 0:
            blockers.append("external-pycharm-acceptance-missing")
        chain = dict(acceptance_chain or {})
        required_chain = {
            "run_result", "finalization_commit", "finalization_receipt", "pytest_session_result",
            "acceptance_result", "approval_record", "execution_context", "terminal", "process_evidence",
        }
        if (
            set(chain) != required_chain
            or chain.get("run_result") != run_result
            or chain.get("acceptance_result") != acceptance
            or validate_pycharm_acceptance_chain(**chain)
        ):
            blockers.append("external-pycharm-acceptance-chain-invalid")
    if not tests_ok: blockers.append("tests-failed")
    if sensitive_scan.get("status") not in {"clear", "passed"}: blockers.append("sensitive-scan-failed")
    resolved_migration_status = migration_status or ("passed" if migration_ok else "failed")
    if resolved_migration_status not in {"passed", "failed", "deferred"}:
        blockers.append("migration-status-invalid")
    elif resolved_migration_status != "passed":
        blockers.append(f"migration-{resolved_migration_status}")
    if not public_pilot.get("passed"): blockers.append("public-pilot-failed")
    if not (xmind_golden or {}).get("passed"):
        blockers.append("xmind-golden-pending")
    return {"status": "completed" if not blockers else "blocked", "completed": not blockers, "blockers": blockers, "global_install": "authorized" if global_install_authorized else "waiting-separate-authorization"}
