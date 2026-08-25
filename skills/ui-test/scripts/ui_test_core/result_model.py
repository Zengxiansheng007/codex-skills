"""Canonical RunResult aggregation and completion evaluation."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

PASS = {"passed"}
FAIL = {"failed", "blocked", "policy-failed", "security-failed"}


def aggregate_run(step_results: list[dict], evidence_refs: list[str] | None = None, conflicts: list[dict] | None = None) -> dict:
    evidence_refs = evidence_refs or []
    conflicts = conflicts or []
    required = [step for step in step_results if step.get("required", True)]
    findings: list[str] = []
    if any(step.get("status") in {"policy-failed", "security-failed", "blocked"} for step in required):
        overall = "blocked"
        findings.append("policy-or-security-block")
    elif any(step.get("status") in FAIL for step in required):
        overall = "failed"
        findings.append("required-step-failed")
    elif conflicts:
        overall = "failed"
        findings.append("evidence-conflict")
    elif any(not step.get("evidence_refs") for step in required):
        overall = "failed"
        findings.append("required-evidence-missing")
    elif any(step.get("status") in {"degraded", "flaky"} for step in required):
        overall = "degraded"
        findings.append("degraded-or-flaky")
    elif required and all(step.get("status") in PASS for step in required):
        overall = "passed"
    else:
        overall = "failed"
        findings.append("no-complete-required-result")
    return {"schema_version": "1.0", "overall_status": overall, "step_results": step_results, "evidence_refs": evidence_refs, "conflicts": conflicts, "findings": findings}


def validate_branch_isolation(runs: Iterable[dict]) -> list[dict]:
    problems = []
    fields = ("run_id", "context_id", "evidence_namespace", "report_namespace")
    values = {field: [] for field in fields}
    for run in runs:
        for field in fields:
            values[field].append(run.get(field))
    for field, items in values.items():
        duplicates = [value for value, count in Counter(items).items() if value and count > 1]
        if duplicates or any(not value for value in items):
            problems.append({"code": "E_BRANCH_ISOLATION", "field": field})
    return problems


def evaluate_completion(*, run_result: dict, required_requirements: set[str], passed_requirements: set[str], sensitive_scan_ok: bool, migration_ok: bool, state_valid: bool, risk_isolated: bool, p0_p1_findings: list[dict]) -> dict:
    missing = sorted(required_requirements - passed_requirements)
    blockers = []
    if run_result.get("overall_status") != "passed": blockers.append("run-not-passed")
    if missing: blockers.append("requirement-coverage-missing")
    if not sensitive_scan_ok: blockers.append("sensitive-scan-failed")
    if not migration_ok: blockers.append("migration-failed")
    if not state_valid: blockers.append("illegal-state")
    if not risk_isolated: blockers.append("risk-mixed")
    if any(item.get("severity") in {"P0", "P1"} for item in p0_p1_findings): blockers.append("open-p0-p1")
    return {"completed": not blockers, "status": "completed" if not blockers else "blocked", "blockers": blockers, "missing_requirements": missing}
