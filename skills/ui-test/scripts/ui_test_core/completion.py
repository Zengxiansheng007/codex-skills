"""Requirement traceability and final completion gate."""

from __future__ import annotations

from typing import Any, Iterable


def validate_rtm(rows: Iterable[dict[str, Any]], required_ids: set[str]) -> dict[str, Any]:
    rows = list(rows)
    seen = {str(row.get("requirement_id")) for row in rows if row.get("requirement_id")}
    missing = sorted(required_ids - seen)
    invalid = [row.get("requirement_id") for row in rows if not row.get("story_id") or not row.get("test_refs") or not row.get("evidence_refs")]
    return {"valid": not missing and not invalid, "missing": missing, "invalid": invalid, "row_count": len(rows)}


def evaluate_release(*, rtm: dict[str, Any], run_result: dict[str, Any], tests_ok: bool, sensitive_scan: dict[str, Any], public_pilot: dict[str, Any], migration_ok: bool | None = None, migration_status: str | None = None, global_install_authorized: bool = False, xmind_golden: dict[str, Any] | None = None) -> dict[str, Any]:
    blockers = []
    if not rtm.get("valid"): blockers.append("rtm-invalid")
    if run_result.get("overall_status") != "passed": blockers.append("run-result-not-passed")
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
