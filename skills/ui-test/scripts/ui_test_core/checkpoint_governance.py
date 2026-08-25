"""Checkpoint identity, promotion, signature, staleness and read-only policy."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass

SCOPE_FIELDS = ("project_group", "product", "system", "module_path", "function", "checkpoint", "environment", "risk_level")


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checkpoint_identity(scope: dict, module_id: str, version: int = 1) -> dict:
    missing = [field for field in SCOPE_FIELDS if not scope.get(field)]
    if missing:
        raise ValueError(f"missing scope fields: {','.join(missing)}")
    if not isinstance(scope["module_path"], list) or not scope["module_path"]:
        raise ValueError("E_CHECKPOINT_MODULE_PATH_INVALID")
    if scope["risk_level"] not in {"r0-read-only", "r1-read-only-authenticated"}:
        raise ValueError("E_CHECKPOINT_RISK_UNSUPPORTED")
    logical = {field: scope[field] for field in SCOPE_FIELDS}
    logical["module_id"] = module_id
    digest = hashlib.sha256(_canonical(logical).encode("utf-8")).hexdigest()[:20]
    return {"module_id": module_id, "checkpoint_id": f"cp-{digest}", "checkpoint_version": version, "scope": logical}


def promotion_status(attempts: list[dict], user_activated: bool = False) -> str:
    deterministic_sessions = {item.get("session_id") for item in attempts if item.get("deterministic_pass") and not item.get("retry_of")}
    if user_activated and len(deterministic_sessions) >= 2:
        return "active"
    if len(deterministic_sessions) >= 2:
        return "eligible"
    if len(deterministic_sessions) == 1:
        return "validated"
    if attempts:
        return "candidate"
    return "blocked"


def verify_module_signature(route_verified: bool, ui_features_verified: list[str], readonly_network_evidence_ref: str | None = None, *, host_verified: bool = True, authenticated_session_verified: bool = True) -> dict:
    unique_ui = {item for item in ui_features_verified if item}
    ok = host_verified and authenticated_session_verified and route_verified and (len(unique_ui) >= 2 or (len(unique_ui) >= 1 and bool(readonly_network_evidence_ref)))
    return {"ok": ok, "host_verified": host_verified, "authenticated_session_verified": authenticated_session_verified, "route_verified": route_verified, "ui_features_verified": sorted(unique_ui), "readonly_network_evidence_ref": readonly_network_evidence_ref, "code": "OK" if ok else "E_CHECKPOINT_STALE"}


def build_module_ready_context(*, session_id: str, run_id: str, identity: dict, signature: dict, auth_reference_digest: str, policy_fingerprint: str, generated_at: str, expires_at: str, evidence_refs: list[str]) -> dict:
    if not signature.get("ok"):
        raise ValueError("E_HANDOFF_FAILED")
    forbidden = ("cookie", "token", "password", "storage", "page_handle")
    lower = auth_reference_digest.lower()
    if any(item in lower for item in forbidden):
        raise ValueError("E_SECRET_DETECTED")
    return {"schema_version":"1.0","context_id":f"mrc-{hashlib.sha256((session_id+run_id+identity['checkpoint_id']).encode()).hexdigest()[:20]}","session_id":session_id,"run_id":run_id,**identity,"host_verified":signature["host_verified"],"authenticated_session_verified":signature["authenticated_session_verified"],"route_verified":True,"ui_features_verified":signature["ui_features_verified"],"readonly_network_evidence_ref":signature.get("readonly_network_evidence_ref"),"auth_reference_digest":auth_reference_digest,"policy_fingerprint":policy_fingerprint,"generated_at":generated_at,"expires_at":expires_at,"handoff_status":"ready","evidence_refs":evidence_refs,"failure_code":None}


def validate_module_ready_context(context: dict, *, session_id: str, run_id: str, context_id: str | None = None, now: str | None = None) -> dict:
    forbidden_fields = {"page", "page_handle", "dom", "cookie", "token", "storage_state", "storagestate"}
    lowered_keys = {str(key).lower() for key in context}
    if lowered_keys & forbidden_fields:
        return {"ok": False, "code": "E_SECRET_DETECTED", "blocking": True}
    if context.get("schema_version") != "1.0" or context.get("handoff_status") != "ready":
        return {"ok": False, "code": "E_MODULE_READY_CONTEXT_INVALID", "blocking": True}
    if context.get("session_id") != session_id:
        return {"ok": False, "code": "E_MODULE_READY_CONTEXT_SESSION_MISMATCH", "blocking": True}
    if context.get("run_id") != run_id:
        return {"ok": False, "code": "E_MODULE_READY_CONTEXT_RUN_MISMATCH", "blocking": True}
    if context_id and context.get("context_id") != context_id:
        return {"ok": False, "code": "E_MODULE_READY_CONTEXT_ID_MISMATCH", "blocking": True}
    if now and context.get("expires_at") and str(context["expires_at"]) <= now:
        return {"ok": False, "code": "E_MODULE_READY_CONTEXT_EXPIRED", "blocking": True}
    if not context.get("host_verified") or not context.get("authenticated_session_verified") or not context.get("route_verified") or len(context.get("ui_features_verified", [])) < 2:
        return {"ok": False, "code": "E_MODULE_SIGNATURE_INSUFFICIENT", "blocking": True}
    return {"ok": True, "code": "OK", "blocking": False}


def stale_decision(*, signature_conflict: bool = False, version_conflict: bool = False, permission_conflict: bool = False, policy_conflict: bool = False, failed_attempts: list[dict] | None = None) -> dict:
    if signature_conflict or version_conflict or permission_conflict or policy_conflict:
        return {"status":"stale","reason":"immediate-conflict"}
    roots = Counter(item.get("root_cause") for item in (failed_attempts or []) if item.get("independent_session") and item.get("root_cause"))
    if any(count >= 2 for count in roots.values()):
        return {"status":"stale","reason":"same-root-two-independent-failures"}
    return {"status":"degraded" if roots else "active","reason":None}


def rebuild_scope(chain: list[str], failed_checkpoint_id: str) -> list[str]:
    if failed_checkpoint_id not in chain:
        raise ValueError("E_CHECKPOINT_UNKNOWN")
    return chain[chain.index(failed_checkpoint_id):]


@dataclass(frozen=True)
class SemanticReadonlySignature:
    method: str
    path_sha256: str
    content_type: str
    query_keys: tuple[str, ...]
    body_keys: tuple[str, ...]
    max_requests_per_session: int = 4

    def matches(self, request: dict, count: int) -> bool:
        normalized = normalize_semantic_readonly_request(request)
        return (
            count <= self.max_requests_per_session
            and normalized.get("method", "").upper() == self.method.upper()
            and normalized.get("path_sha256") == self.path_sha256
            and normalized.get("content_type", "").split(";", 1)[0].strip().lower() == self.content_type.lower()
            and tuple(sorted(normalized.get("query_keys", []))) == tuple(sorted(self.query_keys))
            and tuple(sorted(normalized.get("body_keys", []))) == tuple(sorted(self.body_keys))
            and not any(key in normalized for key in ("raw_url", "query_values", "payload_values", "body_values"))
        )


def normalize_semantic_readonly_request(request: dict) -> dict:
    normalized = dict(request)
    if "body_keys" not in normalized and "payload_keys" in normalized:
        normalized["body_keys"] = normalized["payload_keys"]
        normalized["legacy_payload_keys_accepted"] = True
    normalized["query_keys"] = sorted(set(normalized.get("query_keys", [])))
    normalized["body_keys"] = sorted(set(normalized.get("body_keys", [])))
    normalized.pop("payload_keys", None)
    return normalized
