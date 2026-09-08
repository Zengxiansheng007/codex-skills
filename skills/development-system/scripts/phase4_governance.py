"""Deterministic PH-4 promotion, installation and operations gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_compatibility(assessment: dict[str, Any]) -> dict[str, Any]:
    required_surfaces = {
        "skill", "references", "schemas", "scripts", "fixtures",
        "reports", "changeRecords", "handoffInterface",
    }
    surfaces = assessment.get("surfaces") or []
    covered = {str(item.get("surface")) for item in surfaces if isinstance(item, dict) and item.get("compatible") is True}
    blockers = list(assessment.get("blockers") or [])
    missing = sorted(required_surfaces - covered)
    if missing:
        blockers.append("missing-compatible-surfaces:" + ",".join(missing))
    for field in ("sourceHash", "targetBaselineHash", "backupPlanRef", "rollbackPlanRef"):
        if not assessment.get(field):
            blockers.append("missing:" + field)
    return {
        "compatible": not blockers,
        "state": "running" if not blockers else "repair-needed",
        "blockers": blockers,
        "assessmentHash": canonical_hash(assessment),
    }


def build_backup_manifest(data: dict[str, Any]) -> dict[str, Any]:
    files = data.get("files") or []
    manifest = {
        "manifestId": data.get("manifestId"),
        "targetPath": data.get("targetPath"),
        "targetBaselineHash": data.get("targetBaselineHash"),
        "files": files,
        "filesHash": canonical_hash(files),
        "createdAt": data.get("createdAt"),
        "rollbackPlanRef": data.get("rollbackPlanRef"),
        "restoreValidation": data.get("restoreValidation"),
    }
    missing = [key for key, value in manifest.items() if value in (None, "", [])]
    return {**manifest, "valid": not missing, "missing": missing, "manifestHash": canonical_hash(manifest)}


def evaluate_install_gate(
    request: dict[str, Any],
    approval: dict[str, Any] | None,
    compatibility: dict[str, Any],
    backup: dict[str, Any],
    now: str,
) -> dict[str, Any]:
    if not compatibility.get("compatible") or not backup.get("valid"):
        return {"state": "repair-needed", "allowed": False, "reason": "compatibility-or-backup-not-ready"}
    if not isinstance(approval, dict):
        return {"state": "blocked-user-decision", "allowed": False, "reason": "explicit-install-approval-missing"}
    observed = parse_time(now)
    valid_from = parse_time(approval.get("validFrom"))
    expires_at = parse_time(approval.get("expiresAt"))
    if approval.get("status") != "active" or not observed or not valid_from or not expires_at or not (valid_from <= observed < expires_at):
        return {"state": "blocked-user-decision", "allowed": False, "reason": "install-approval-inactive-or-expired"}
    exact_fields = (
        "sourceHash", "targetPath", "targetBaselineHash", "coverage",
        "backupManifestRef", "rollbackPlanRef",
    )
    mismatches = [field for field in exact_fields if request.get(field) != approval.get(field)]
    if not approval.get("userApprovalRef"):
        mismatches.append("userApprovalRef")
    if request.get("backupManifestHash") != backup.get("manifestHash"):
        mismatches.append("backupManifestHash")
    if mismatches:
        return {
            "state": "blocked-user-decision",
            "allowed": False,
            "reason": "install-approval-boundary-mismatch",
            "mismatches": sorted(set(mismatches)),
        }
    return {
        "state": "waiting-approval" if request.get("mode") == "live" else "running",
        "allowed": True,
        "reason": "exact-user-install-approval-match",
        "dryRunOnly": request.get("mode") != "live",
        "approvalId": approval.get("approvalId"),
        "auditRedacted": True,
    }


def build_operations_report(data: dict[str, Any]) -> dict[str, Any]:
    events = data.get("events") or []
    decisions = data.get("decisions") or []
    usage = data.get("resourceUsage") or {}
    budget = data.get("resourceBudget") or {}
    exceeded = sorted(key for key, limit in budget.items() if usage.get(key, 0) > limit)
    required = {
        "statusProjection", "retentionDays", "failureBudget",
        "maintenanceRefs", "eventHistoryRef", "decisionLogRef",
    }
    missing = sorted(key for key in required if data.get(key) in (None, "", []))
    reconstructible = bool(events) and bool(decisions) and not missing
    return {
        "state": "resource-limit-reached" if exceeded else ("running" if reconstructible else "repair-needed"),
        "reconstructible": reconstructible,
        "missing": missing,
        "resourceExceeded": exceeded,
        "eventCount": len(events),
        "decisionCount": len(decisions),
        "reportHash": canonical_hash({"events": events, "decisions": decisions, "usage": usage, "budget": budget}),
    }

