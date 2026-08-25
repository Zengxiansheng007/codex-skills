"""Dry-run-first, deterministic adapters for legacy UI-Test assets."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from .case_contracts import canonical_hash
from .packet_validator import validate_packet


def migrate_run_result(source: dict[str, Any], source_ref: str = "legacy") -> dict[str, Any]:
    if source.get("schema_version") == "1.0" and "step_results" in source and "overall_status" in source:
        return copy.deepcopy(source)
    steps = source.get("step_results") or source.get("steps") or source.get("results") or []
    normalized = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            step = {"legacy_value": step}
        status = step.get("status") or step.get("result") or "unknown"
        if status not in {"passed", "failed", "blocked", "degraded", "flaky", "unknown"}:
            status = "unknown"
        normalized.append({
            "step_id": step.get("step_id") or step.get("id") or f"legacy-{index + 1}",
            "status": status,
            "required": step.get("required", True),
            "evidence_refs": step.get("evidence_refs", []),
            "provenance": {"source_ref": source_ref, "legacy_index": index},
        })
    claimed = source.get("overall_status") or source.get("status") or source.get("result") or "unknown"
    missing_evidence = any(item["required"] and not item["evidence_refs"] for item in normalized)
    overall = "passed" if claimed == "passed" and normalized and not missing_evidence and all(item["status"] == "passed" for item in normalized) else "unknown"
    if any(item["status"] in {"failed", "blocked"} for item in normalized):
        overall = "failed"
    return {
        "schema_version": "1.0", "run_id": source.get("run_id") or "unknown",
        "case_id": source.get("case_id") or "unknown", "branch_id": source.get("branch_id") or "unknown",
        "overall_status": overall, "step_results": normalized, "evidence_refs": source.get("evidence_refs", []),
        "conflicts": [], "retry_history": source.get("retry_history", []),
        "fallback_history": source.get("fallback_history", []), "lineage": {"migrated_from": source_ref},
        "redaction_status": "clear", "completion_evaluator": {"completed": False, "reason": "migration-requires-review"},
    }


def migrate_packet_dry_run(source: dict[str, Any], *, source_ref: str, target_sidecar_ref: str) -> dict[str, Any]:
    original = copy.deepcopy(source)
    source_version = str(source.get("schema_version") or "unknown")
    issues = migration_issue_list(
        source,
        source_ref=source_ref,
        source_type="ui-test-packet",
        target_sidecar_ref=target_sidecar_ref,
        check_common_fields=False,
    )
    candidate: dict[str, Any] | None = None
    if source_version == "2.0":
        candidate = copy.deepcopy(source)
    elif source_version == "1.0" or source_version == "unknown":
        candidate = _adapt_packet_to_v2(source)
        issues["issues"].append(_issue(
            "packet-version-adapted", "P2", "ui-test-packet", source_ref, target_sidecar_ref,
            "review-candidate-sidecar", "clear", False,
        ))
    else:
        issues["issues"].append(_issue(
            "packet-version-unsupported", "P1", "ui-test-packet", source_ref, target_sidecar_ref,
            "provide-version-adapter", "clear", True,
        ))
    if candidate is not None:
        for error in validate_packet(candidate):
            issues["issues"].append(_issue(
                error["code"].removeprefix("E_").lower().replace("_", "-"),
                "P1", "ui-test-packet", source_ref, target_sidecar_ref,
                f"repair-candidate-at-{error['path']}", "clear", True,
            ))
    issues["issues"] = _dedupe_and_sort_issues(issues["issues"])
    issues["blocking_completion"] = any(item["blocking_completion"] for item in issues["issues"])
    if source != original:
        raise RuntimeError("E_MIGRATION_SOURCE_MUTATED")
    return {
        "schema_version": "ui-test.packet-migration-dry-run.v1",
        "migration_mode": "dry-run",
        "source_ref": source_ref,
        "source_hash": canonical_hash(source),
        "source_unchanged": True,
        "candidate_packet": candidate,
        "issue_list": issues,
        "ready_for_sidecar": candidate is not None and not issues["blocking_completion"],
        "source_overwrite_permitted": False,
    }


def migration_issue_list(
    source: dict[str, Any], *, source_ref: str, source_type: str, target_sidecar_ref: str,
    check_common_fields: bool = True,
) -> dict[str, Any]:
    issues = []
    source_version = str(source.get("schema_version") or "unknown")
    if source_version == "unknown":
        issues.append(_issue("schema-version-unknown", "P1", source_type, source_ref, target_sidecar_ref, "manual-review", "clear", True))
    if check_common_fields and "scope" not in source:
        issues.append(_issue("scope-missing", "P1", source_type, source_ref, target_sidecar_ref, "map-scope-or-mark-unknown", "clear", True))
    if check_common_fields and not (source.get("evidence_refs") or source.get("evidence_index")):
        issues.append(_issue("evidence-missing", "P2", source_type, source_ref, target_sidecar_ref, "attach-missing-reason", "clear", False))
    if _contains_sensitive_marker(source):
        issues.append(_issue("sensitive-marker", "P0", source_type, source_ref, target_sidecar_ref, "quarantine", "suspected", True))
    issues = _dedupe_and_sort_issues(issues)
    return {
        "schema_version": "ui-test.migration-issue-list.v1", "migration_mode": "dry-run",
        "source_ref": source_ref, "source_type": source_type, "source_version": source_version,
        "source_hash": canonical_hash(source), "source_unchanged": True,
        "target_sidecar_ref": target_sidecar_ref, "issues": issues,
        "blocking_completion": any(item["blocking_completion"] for item in issues),
    }


def evaluate_pilot_delete(*, exact_inventory: list[dict[str, Any]] | None, reference_check_passed: bool, pilot_status: str, action: str) -> dict[str, Any]:
    if action != "delete-pilot-unmigratable":
        return {"allowed": False, "code": "E_DELETE_ACTION_UNKNOWN"}
    if pilot_status != "first-pilot-active":
        return {"allowed": False, "code": "E_DELETE_PILOT_WINDOW_CLOSED"}
    if not exact_inventory or any(not item.get("asset_ref") or not item.get("disposition_reason") for item in exact_inventory):
        return {"allowed": False, "code": "E_DELETE_INVENTORY_REQUIRED"}
    if not reference_check_passed or any(item.get("referenced") for item in exact_inventory):
        return {"allowed": False, "code": "E_DELETE_REFERENCE_CHECK_FAILED"}
    return {"allowed": True, "code": "OK", "exact_asset_refs": sorted(item["asset_ref"] for item in exact_inventory), "recursive_root_delete": False, "one_time_exception": True}


def _adapt_packet_to_v2(source: dict[str, Any]) -> dict[str, Any]:
    scope = source.get("scope") if isinstance(source.get("scope"), dict) else {}
    module_value = scope.get("module_path", scope.get("module", source.get("module_path", source.get("module"))))
    module_path = module_value if isinstance(module_value, list) else [module_value] if isinstance(module_value, str) and module_value else []
    risk = source.get("risk_level") or scope.get("risk_level") or "r0-read-only"
    adapted_scope = {
        "project_group": scope.get("project_group") or source.get("project_group") or source.get("project") or "",
        "product": scope.get("product") or source.get("product") or "",
        "system": scope.get("system") or source.get("system") or "",
        "module_path": module_path,
        "function": scope.get("function") or source.get("function") or "",
        "checkpoint": scope.get("checkpoint") or source.get("checkpoint") or "unknown",
        "environment": scope.get("environment") or source.get("environment") or "public",
        "risk_level": scope.get("risk_level") or risk,
    }
    case = source.get("case") if isinstance(source.get("case"), dict) else {"case_id": source.get("case_id") or ""}
    branch = source.get("branch") if isinstance(source.get("branch"), dict) else {"branch_id": source.get("branch_id") or "main"}
    run = source.get("run") if isinstance(source.get("run"), dict) else {
        "run_id": source.get("run_id") or "migration-dry-run", "started_at": source.get("started_at") or "1970-01-01T00:00:00Z"
    }
    result = {
        "schema_version": "2.0", "packet_id": source.get("packet_id") or "MIGRATION-CANDIDATE",
        "packet_type": "ui-test-packet", "scope": adapted_scope, "risk_level": risk,
        "state": source.get("state") or "requirements-review", "case": case, "branch": branch, "run": run,
        "steps": _adapt_steps(source.get("steps")),
        "lineage": copy.deepcopy(source.get("lineage")) if isinstance(source.get("lineage"), dict) else {"anchor_id": "migration-review", "source_refs": []},
        "evidence_policy": copy.deepcopy(source.get("evidence_policy")) if isinstance(source.get("evidence_policy"), dict) else {"screenshot_on_ui_change": True, "redaction_required": True},
        "retry_policy": copy.deepcopy(source.get("retry_policy")) if isinstance(source.get("retry_policy"), dict) else {"max_attempts": 0, "fallback_allowed": False},
        "next_action": source.get("next_action") or "blocked",
    }
    for optional in ("priority", "source_case_ref", "source_hash", "build_fingerprint", "effective_risk_level", "execution_policy_ref"):
        if optional in source:
            result[optional] = copy.deepcopy(source[optional])
    return result


def _adapt_steps(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        source_steps = [step for section in ("setup", "feature", "assertions") for step in value.get(section, [])]
    elif isinstance(value, list):
        source_steps = value
    else:
        return []
    allowed = {"step_id", "action", "risk_level", "required", "intent", "postcondition"}
    return [{key: copy.deepcopy(item[key]) for key in allowed if key in item} for item in source_steps if isinstance(item, dict)]


def _issue(kind: str, severity: str, source_type: str, source_ref: str, target_sidecar_ref: str, recommended_action: str, sensitive_status: str, blocking_completion: bool) -> dict[str, Any]:
    normalized_kind = kind.upper().replace("-", "_")
    digest = hashlib.sha256(f"{source_type}:{source_ref}:{kind}:{target_sidecar_ref}".encode("utf-8")).hexdigest()[:16]
    return {
        "issue_id": f"MIG-{digest}", "severity": severity, "problem_code": f"E_MIGRATION_{normalized_kind}",
        "source_type": source_type, "source_ref": source_ref, "target_sidecar_ref": target_sidecar_ref,
        "recommended_action": recommended_action, "sensitive_status": sensitive_status,
        "blocking_completion": blocking_completion, "provenance": {"algorithm": "stable-sha256-v1"},
    }


def _dedupe_and_sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted({item["issue_id"]: item for item in issues}.values(), key=lambda item: (item["severity"], item["problem_code"], item["issue_id"]))


def _contains_sensitive_marker(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_sensitive_marker(key) or _contains_sensitive_marker(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_sensitive_marker(item) for item in value)
    text = str(value).lower()
    return any(marker in text for marker in ("password", "token", "cookie", "authorization", "storage_state", "bearer "))
