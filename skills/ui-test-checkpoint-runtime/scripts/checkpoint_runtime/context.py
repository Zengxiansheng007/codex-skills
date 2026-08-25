"""Current-session ModuleReadyContext construction and validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


SCOPE_FIELDS = ("project_group", "product", "system", "module", "function", "checkpoint", "environment", "risk_level")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build_context(*, target: Any, checkpoint_id: str, checkpoint_version: int, signature: dict[str, Any], auth_ref: dict[str, Any], session_id: str, run_id: str, expires_at: str, evidence_refs: list[str]) -> dict[str, Any]:
    if not signature.get("ok"):
        raise ValueError("E_HANDOFF_FAILED")
    if not auth_ref.get("auth_ref_id"):
        raise ValueError("E_AUTH_EXPIRED")
    scope = {
        "project_group": target.project_group,
        "product": target.product,
        "system": target.system_id,
        "module": target.module_id,
        "function": target.function,
        "checkpoint": target.checkpoint,
        "environment": target.environment_alias or "public",
        "risk_level": target.risk_level,
    }
    if any(not scope[field] for field in SCOPE_FIELDS):
        raise ValueError("E_HANDOFF_FAILED")
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "ui-test.module-ready-context.v1",
        "context_id": "mrc-" + hashlib.sha256(f"{session_id}:{run_id}:{checkpoint_id}:{generated_at}".encode()).hexdigest()[:20],
        "session_id": session_id,
        "run_id": run_id,
        **scope,
        "module_id": target.module_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_version": checkpoint_version,
        "route_verified": bool(signature.get("route_verified")),
        "ui_features_verified": list(signature.get("ui_features_verified", [])),
        "readonly_network_evidence_ref": signature.get("readonly_network_evidence_ref"),
        "auth_reference_digest": _digest(auth_ref.get("auth_ref_id")),
        "policy_fingerprint": _digest({"risk_level": target.risk_level, "forbidden": ["POST", "PUT", "PATCH", "DELETE"]}),
        "generated_at": generated_at,
        "expires_at": expires_at,
        "handoff_status": "ready",
        "evidence_refs": list(evidence_refs),
        "failure_code": None,
    }


def validate_context(context: dict[str, Any], *, session_id: str, run_id: str) -> dict[str, Any]:
    required = ("context_id", "session_id", "run_id", "module_id", "checkpoint_id", "route_verified", "ui_features_verified", "handoff_status", "expires_at")
    missing = [field for field in required if field not in context]
    if missing:
        return {"ok": False, "code": "E_HANDOFF_FAILED", "missing": missing}
    if context["session_id"] != session_id or context["run_id"] != run_id:
        return {"ok": False, "code": "E_HANDOFF_FAILED", "reason": "session/run mismatch"}
    if context["handoff_status"] != "ready" or not context["route_verified"] or len(context["ui_features_verified"]) < 2:
        return {"ok": False, "code": "E_HANDOFF_FAILED", "reason": "signature incomplete"}
    return {"ok": True, "code": "OK"}
