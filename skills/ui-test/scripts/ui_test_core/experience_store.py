"""Read-only experience lookup and advisory feedback; no permission elevation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json


SCOPE_FIELDS = ("project_group", "product", "system", "module", "function", "checkpoint", "environment", "risk_level")


def lookup(root: str | Path, scope: dict[str, str]) -> list[dict[str, Any]]:
    if any(not scope.get(field) for field in SCOPE_FIELDS):
        return []
    matches = []
    for path in Path(root).rglob("*.json"):
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if candidate.get("scope") == {field: scope[field] for field in SCOPE_FIELDS}:
            blocked = is_forbidden_reuse(candidate, scope)
            matches.append({"experience_id": candidate.get("experience_id"), "experience_status": candidate.get("experience_status"), "path": str(path), "advisory_only": True, "consumption_blocked": blocked["blocked"], "blocked_reason": blocked.get("reason")})
    return sorted(matches, key=lambda item: (item.get("experience_id") or "", item.get("path") or ""))


def consumption_feedback(*, experience_id: str, run_id: str, checkpoint_version: int, outcome: str, evidence_refs: list[str]) -> dict[str, Any]:
    if outcome not in {"used", "not-used", "degraded", "stale", "blocked"}:
        raise ValueError("E_FEEDBACK_INVALID")
    return {"schema_version": "ui-test.experience-feedback.v1", "experience_id": experience_id, "run_id": run_id, "checkpoint_version": checkpoint_version, "outcome": outcome, "evidence_refs": list(evidence_refs), "permission_effect": "none"}


def is_forbidden_reuse(experience: dict[str, Any], scope: dict[str, str] | None = None) -> dict[str, Any]:
    if experience.get("experience_status") in {"negative", "quarantined", "superseded"}:
        return {"blocked": True, "reason": f"status:{experience.get('experience_status')}"}
    for condition in experience.get("forbidden_reuse", []):
        if not isinstance(condition, dict):
            continue
        if condition.get("scope") and scope and condition["scope"] != scope:
            continue
        return {"blocked": True, "reason": condition.get("reason") or "forbidden-reuse"}
    return {"blocked": False}
