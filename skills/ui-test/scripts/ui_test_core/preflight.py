"""Version, capability and budget preflight before browser/model startup."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .packet_validator import validate_packet
from .path_planner import PathPlanningError, plan_asset_path
from .secret_governance import scan_value


def check_midscene_lock(lock_path: str | Path, version: str = "1.10.2") -> dict:
    path = Path(lock_path)
    if not path.is_file():
        return {"ok": False, "code": "E_PREFLIGHT_FAILED", "reason": "lockfile-missing"}
    text = path.read_text(encoding="utf-8")
    web = bool(re.search(rf"@midscene/web@{re.escape(version)}(?:[\'\"(:])" , text))
    core = bool(re.search(rf"@midscene/core@{re.escape(version)}(?:[\'\"(:])" , text))
    return {"ok": web and core, "code": "OK" if web and core else "E_PREFLIGHT_FAILED", "midscene_web": web, "midscene_core": core, "version": version}


def capability_manifest(*, python_ok: bool, node_ok: bool, browser_ok: bool, lock_ok: bool, model_gateway_ok: bool, permissions_ok: bool, free_bytes: int, risk_level: str, requested_bytes: int) -> dict:
    budget = 1024**3 if risk_level == "r2-ui-write-test" else 512 * 1024**2
    budget_warning = requested_bytes > budget
    checks = {"python":python_ok,"node":node_ok,"browser":browser_ok,"lockfile":lock_ok,"model_gateway":model_gateway_ok,"permissions":permissions_ok,"disk":free_bytes >= requested_bytes}
    failed = sorted(name for name, ok in checks.items() if not ok)
    warnings = ["W_ARTIFACT_BUDGET_EXCEEDED"] if budget_warning else []
    return {"schema_version":"1.0","ok":not failed,"code":"OK" if not failed else "E_PREFLIGHT_FAILED","checks":checks,"failed_checks":failed,"warnings":warnings,"risk_level":risk_level,"budget_bytes":budget,"requested_bytes":requested_bytes,"redaction_status":"clear"}


def governed_asset_preflight(
    *, config: dict[str, Any] | None, packet: dict[str, Any] | None,
    asset_requests: list[dict[str, Any]], release_status: str,
    documents: dict[str, Any] | None = None, migration_issue_lists: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    plans: list[dict[str, Any]] = []
    if not isinstance(config, dict) or config.get("schema_version") != "2.0" or not config.get("write_ready"):
        issues.append(_gate_issue("E_CONFIG_NOT_WRITE_READY", "/config", "Project config v2 is required for formal writes."))
    if not isinstance(packet, dict):
        issues.append(_gate_issue("E_PACKET_MISSING", "/packet", "A valid Packet v2 is required."))
    else:
        issues.extend(_gate_issue(item["code"], item["path"], item["message"]) for item in validate_packet(packet))
    if release_status != "in_sync":
        issues.append(_gate_issue("E_RELEASE_NOT_IN_SYNC", "/release_status", "Only an in_sync active release may be consumed."))
    findings = scan_value(documents or {})
    issues.extend(_gate_issue("E_SECRET_DETECTED", item["path"], "Sensitive content is forbidden.") for item in findings)
    for index, request in enumerate(asset_requests):
        if not isinstance(config, dict) or not config.get("write_ready"):
            break
        try:
            plans.append(plan_asset_path(config, request.get("asset_type", ""), request.get("selection", {})))
        except PathPlanningError as error:
            issues.append(_gate_issue(str(error), f"/asset_requests/{index}", "Asset path planning failed."))
    for index, issue_list in enumerate(migration_issue_lists or []):
        if issue_list.get("blocking_completion"):
            issues.append(_gate_issue("E_MIGRATION_BLOCKING_ISSUES", f"/migration_issue_lists/{index}", "Migration has blocking issues."))
    issues = _dedupe_gate_issues(issues)
    return {
        "schema_version": "ui-test.preflight-result.v1", "stage": "preflight",
        "ok": not issues, "issues": issues, "path_plans": plans,
        "formal_write_allowed": not issues, "completion_allowed": False,
    }


def governed_post_write_gate(
    *, release_status: str, artifacts: list[dict[str, Any]], formal_references: list[dict[str, Any]],
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if release_status != "in_sync":
        issues.append(_gate_issue("E_RELEASE_NOT_IN_SYNC", "/release_status", "Only an in_sync active release may complete."))
    for collection_name, collection in (("artifacts", artifacts), ("formal_references", formal_references)):
        for index, record in enumerate(collection):
            if not record.get("ui_test_project_asset", False):
                continue
            path = str(record.get("path", ""))
            asset_type = str(record.get("asset_type", ""))
            if _is_c_drive(path):
                issues.append(_gate_issue("E_UI_TEST_ASSET_ON_C_DRIVE", f"/{collection_name}/{index}/path", "UI-Test project assets cannot persist on C drive."))
            if not _root_matches_asset_type(path, asset_type):
                issues.append(_gate_issue("E_PATH_ROOT_TYPE_MISMATCH", f"/{collection_name}/{index}/path", "Asset type does not match its governed root."))
            if record.get("sync_status", "in_sync") != "in_sync":
                issues.append(_gate_issue("E_DERIVED_ASSET_NOT_IN_SYNC", f"/{collection_name}/{index}/sync_status", "Formal derived asset is not in_sync."))
    issues = _dedupe_gate_issues(issues)
    return {
        "schema_version": "ui-test.preflight-result.v1", "stage": "post-write",
        "ok": not issues, "issues": issues, "formal_write_allowed": False,
        "completion_allowed": not issues,
    }


def _root_matches_asset_type(path: str, asset_type: str) -> bool:
    normalized = path.replace("/", "\\").lower()
    knowledge = asset_type.startswith(("experience_", "knowledge_"))
    return normalized.startswith("d:\\rag\\") if knowledge else normalized.startswith("d:\\ui-test\\")


def _is_c_drive(path: str) -> bool:
    return bool(re.match(r"(?i)^c:[\\/]", path.strip()))


def _gate_issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _dedupe_gate_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted({(item["code"], item["path"]): item for item in issues}.values(), key=lambda item: (item["code"], item["path"]))
