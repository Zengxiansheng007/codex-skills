"""Canonical event-folded RunResult and immutable downstream projections."""

from __future__ import annotations

import copy
from typing import Any

from .case_contracts import canonical_hash


def aggregate_events(*, run: dict[str, Any], events: list[dict[str, Any]], release_status: str) -> dict[str, Any]:
    ordered = sorted(events, key=lambda item: (item.get("sequence", 0), item.get("event_id", "")))
    steps: dict[str, dict[str, Any]] = {}
    evidence_refs: set[str] = set()
    findings: list[str] = []
    retained_data = []
    write_state = "not_attempted"
    submit_count = 0
    for event in ordered:
        step_id = event.get("step_id")
        if step_id:
            steps[step_id] = {
                "step_id": step_id, "section": event.get("section", "feature"), "status": event.get("status", "unknown"),
                "required": event.get("required", True), "tool": event.get("tool"), "evidence_refs": sorted(set(event.get("evidence_refs", []))),
                "failure_layer": event.get("failure_layer"),
            }
            evidence_refs.update(event.get("evidence_refs", []))
        if event.get("event_type") == "write-outcome":
            write_state = event.get("write_state", write_state)
            submit_count = max(submit_count, int(event.get("submit_count", 0)))
            if event.get("retained_test_data"):
                retained_data.append(copy.deepcopy(event["retained_test_data"]))
    required = [item for item in steps.values() if item["required"]]
    setup_failed = any(item["section"] == "setup" and item["status"] != "passed" for item in required)
    if release_status != "in_sync":
        overall = "blocked"; findings.append("release-not-in-sync")
    elif submit_count > 1:
        overall = "blocked"; findings.append("double-submit")
    elif write_state == "write_succeeded_verification_failed":
        overall = "failed"; findings.append("write-succeeded-verification-failed")
    elif setup_failed:
        overall = "failed"; findings.append("setup-navigation-failure")
    elif any(item["status"] in {"failed", "blocked", "policy-failed", "security-failed"} for item in required):
        overall = "failed"; findings.append("required-step-failed")
    elif any(not item["evidence_refs"] for item in required):
        overall = "failed"; findings.append("required-evidence-missing")
    elif required and all(item["status"] == "passed" for item in required):
        overall = "passed"
    else:
        overall = "failed"; findings.append("incomplete-required-results")
    result = {
        "schema_version": "ui-test.run-result.v2", **run, "overall_status": overall,
        "release_status": release_status, "step_results": list(steps.values()),
        "evidence_refs": sorted(evidence_refs), "conflicts": [], "findings": findings,
        "write_state": write_state, "submit_count": submit_count, "retained_test_data": retained_data,
        "cleanup_status": "not_planned_this_release" if retained_data else "not_applicable",
        "business_cleanup_attempted": False,
    }
    result["run_result_hash"] = canonical_hash(result)
    return result


def project_run_result(run_result: dict[str, Any], projection: str) -> dict[str, Any]:
    source_hash = canonical_hash(run_result)
    common = {"schema_version": f"ui-test.{projection}.v1", "projection": projection, "run_id": run_result["run_id"], "case_id": run_result["case_id"], "branch_id": run_result["branch_id"], "overall_status": run_result["overall_status"], "source_run_result_hash": source_hash, "read_only_projection": True}
    if projection == "evidence-index":
        return {**common, "evidence_refs": copy.deepcopy(run_result["evidence_refs"]), "step_evidence": {item["step_id"]: item["evidence_refs"] for item in run_result["step_results"]}}
    if projection == "report-model":
        return {**common, "sections": {"setup": [item for item in run_result["step_results"] if item["section"] == "setup"], "feature": [item for item in run_result["step_results"] if item["section"] == "feature"], "assertions": [item for item in run_result["step_results"] if item["section"] == "assertions"]}, "retained_test_data": copy.deepcopy(run_result["retained_test_data"]), "cleanup_status": run_result["cleanup_status"]}
    if projection == "experience-candidate":
        status = "negative" if run_result["overall_status"] != "passed" else "observed"
        return {**common, "experience_status": status, "permission_effect": "none", "promotion_effect": "none", "evidence_refs": copy.deepcopy(run_result["evidence_refs"]), "forbidden_reuse": [{"reason": "failed-run"}] if status == "negative" else []}
    raise ValueError("E_PROJECTION_UNKNOWN")
