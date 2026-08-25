"""Validate and optionally append a redacted UI-Test experience candidate.

The script is deliberately standard-library only. It is a gate and adapter for
the project experience store; it is not a promotion service and never promotes
an experience to active/shared/RC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


ALLOWED_WRITE_STATES = frozenset({"observed", "candidate"})
REQUIRED_SCOPE = (
    "project_group", "product", "system", "module", "function",
    "checkpoint", "environment", "risk_level",
)
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SENSITIVE_KEY = re.compile(
    r"(?i)(password|passwd|secret|token|cookie|storage.?state|api.?key|authorization|username|credential|raw.?url)"
)
RAW_URL = re.compile(r"(?i)https?://|wss?://")
SENSITIVE_VALUE = re.compile(
    r"(?i)(?:password|passwd|secret|token|cookie|authorization|api[_-]?key)\s*[:=]\s*[^\s,;]{3,}|bearer\s+[A-Za-z0-9._~+/-]{8,}|sk-[A-Za-z0-9_-]{16,}"
)


class PacketError(ValueError):
    """A fail-closed packet or policy violation."""


def _walk(value: Any, path: str = "$"):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield path + "." + str(key), str(key), child
            yield from _walk(child, path + "." + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def sensitive_findings(packet: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for path, key, child in _walk(packet):
        if SENSITIVE_KEY.search(key):
            findings.append(f"{path}:sensitive-key")
        if isinstance(child, str) and RAW_URL.search(child):
            findings.append(f"{path}:raw-url")
        if isinstance(child, str) and SENSITIVE_VALUE.search(child):
            findings.append(f"{path}:sensitive-value")
        if key.lower() == "contains_production_data" and child is True:
            findings.append(f"{path}:production-data")
        if key.lower() == "data_classification" and str(child).lower() in {"prod", "production", "production-data"}:
            findings.append(f"{path}:production-data")
    return findings


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise PacketError(f"{field} must be a logical ID")
    return value


def validate_semantic_post(value: Mapping[str, Any]) -> None:
    required = ("method", "path_sha256", "query_keys", "body_keys", "content_type", "classification", "max_per_session")
    missing = [key for key in required if key not in value]
    if missing:
        raise PacketError("semantic POST signature missing: " + ",".join(missing))
    if value["method"] != "POST" or not SHA256.fullmatch(str(value["path_sha256"])):
        raise PacketError("semantic POST requires POST and a path-only SHA-256")
    if not isinstance(value["query_keys"], list) or value["query_keys"] != sorted(set(value["query_keys"])):
        raise PacketError("query_keys must be a sorted unique key set")
    if not isinstance(value["body_keys"], list) or value["body_keys"] != sorted(set(value["body_keys"])):
        raise PacketError("body_keys must be a sorted unique key set")
    if not value["content_type"] or value["classification"] not in {"authentication", "query", "pagination"}:
        raise PacketError("semantic POST classification is not read-only")
    if not isinstance(value["max_per_session"], int) or not 1 <= value["max_per_session"] <= 4:
        raise PacketError("semantic POST count must be bounded to 1..4")
    forbidden = {"url", "raw_url", "query_values", "body_values", "request_body", "response_body"}
    if forbidden.intersection(value):
        raise PacketError("semantic POST signature must not contain request values or raw URLs")


def authorize_semantic_post(observed: Mapping[str, Any], signature: Mapping[str, Any], *, used_count: int) -> dict[str, Any]:
    """Match one value-free request observation against a reviewed signature."""

    validate_semantic_post(signature)
    allowed_observation = {"method", "path_sha256", "query_keys", "body_keys", "content_type"}
    if set(observed) != allowed_observation:
        return {"allowed": False, "decision_code": "observation-shape-mismatch"}
    comparable = ("method", "path_sha256", "query_keys", "body_keys", "content_type")
    if any(observed.get(field) != signature.get(field) for field in comparable):
        return {"allowed": False, "decision_code": "semantic-signature-mismatch"}
    if used_count < 0 or used_count >= signature["max_per_session"]:
        return {"allowed": False, "decision_code": "session-count-exceeded"}
    return {"allowed": True, "decision_code": "semantic-readonly-post-authorized", "next_count": used_count + 1}


def validate_packet(packet: Mapping[str, Any], *, for_writeback: bool = False, expected_scope: Mapping[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise PacketError("packet must be an object")
    findings = sensitive_findings(packet)
    if findings:
        raise PacketError("sensitive scan failed: " + ",".join(findings))
    for field in ("experience_id", "experience_version", "experience_status", "scope", "category", "trigger", "strategy", "source_run_ids", "source_step_ids", "source_checkpoint_ids", "evidence_refs"):
        if field not in packet:
            raise PacketError(f"missing field: {field}")
    _require_id(packet["experience_id"], "experience_id")
    if not isinstance(packet["experience_version"], int) or packet["experience_version"] < 1:
        raise PacketError("experience_version must be a positive integer")
    status = packet["experience_status"]
    if status not in {"observed", "candidate", "validated", "promotable", "active", "stale", "retired", "rejected"}:
        raise PacketError("unknown experience_status")
    if for_writeback and status not in ALLOWED_WRITE_STATES:
        raise PacketError("automatic writeback only permits observed/candidate")
    scope = packet["scope"]
    if not isinstance(scope, Mapping) or any(not isinstance(scope.get(field), str) or not scope[field].strip() for field in REQUIRED_SCOPE):
        raise PacketError("scope must contain all independent dimensions")
    if scope["environment"] == "production":
        raise PacketError("production experience is outside automatic governance")
    if expected_scope and any(scope.get(field) != expected_scope.get(field) for field in ("project_group", "product", "environment")):
        raise PacketError("packet scope does not match the active project policy")
    if scope["risk_level"] not in {"r0-reference", "r1-read-only", "r2-write-isolated", "r3-sensitive"}:
        raise PacketError("unknown risk level")
    if for_writeback and scope["risk_level"] not in {"r0-reference", "r1-read-only"}:
        raise PacketError("R2/R3 experience requires separate manual review and cannot auto-write")
    for field in ("source_run_ids", "source_step_ids", "source_checkpoint_ids", "evidence_refs"):
        if not isinstance(packet[field], list) or any(not isinstance(item, str) or not item for item in packet[field]):
            raise PacketError(f"{field} must contain logical references")
    if "semantic_post" in packet:
        validate_semantic_post(packet["semantic_post"])
    result = dict(packet)
    result["content_hash"] = canonical_hash({key: value for key, value in result.items() if key != "content_hash"})
    return result


def _timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PacketError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PacketError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: Mapping[str, Any], *, now: str) -> None:
    required = ("policy_id", "status", "knowledge_space_id", "target_root", "project_group", "product", "environment", "allowed_actions", "valid_from", "expires_at", "auto_renew", "approval_ref", "boundary_hash")
    if any(field not in policy for field in required):
        raise PacketError("writeback policy is incomplete")
    _require_id(policy["policy_id"], "policy_id")
    _require_id(policy["approval_ref"], "approval_ref")
    if policy["status"] != "active":
        raise PacketError("writeback policy is not active")
    _require_id(policy["knowledge_space_id"], "knowledge_space_id")
    target_root = Path(str(policy["target_root"]))
    if not target_root.is_absolute():
        raise PacketError("writeback target_root must be absolute")
    if any(not isinstance(policy.get(field), str) or not policy[field] for field in ("project_group", "product", "environment")):
        raise PacketError("writeback policy scope mismatch")
    if policy["environment"] == "production":
        raise PacketError("production writeback is not permitted")
    actions = policy["allowed_actions"]
    if not isinstance(actions, list) or not actions or policy["auto_renew"] or not set(actions).issubset({"append-observed", "append-candidate"}):
        raise PacketError("writeback policy action or renewal boundary is invalid")
    expected_hash = canonical_hash({key: value for key, value in policy.items() if key != "boundary_hash"})
    if policy["boundary_hash"] != expected_hash:
        raise PacketError("writeback policy boundary hash mismatch")
    start = _timestamp(policy["valid_from"], "valid_from")
    end = _timestamp(policy["expires_at"], "expires_at")
    current = _timestamp(now, "now")
    if end <= start or end - start > timedelta(days=90) or not start <= current < end:
        raise PacketError("writeback policy is expired or exceeds 90 days")


def _atomic_create(path: Path, payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == serialized:
            return "idempotent"
        raise PacketError("append-only conflict: target exists with different content")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".candidate-", suffix=".tmp", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return "created"


def writeback(packet: Mapping[str, Any], policy: Mapping[str, Any], *, request_id: str, now: str) -> dict[str, Any]:
    validate_policy(policy, now=now)
    checked = validate_packet(packet, for_writeback=True, expected_scope=policy)
    action = "append-" + str(checked["experience_status"])
    if action not in policy["allowed_actions"]:
        raise PacketError("action is not authorized")
    _require_id(request_id, "request_id")
    root = Path(str(policy["target_root"]))
    candidate = root / "project" / "candidates" / f"{checked['experience_id']}-v{checked['experience_version']}.json"
    outcome = _atomic_create(candidate, checked)
    audit = {
        "audit_type": "experience.writeback",
        "request_id": request_id,
        "policy_id": policy["policy_id"],
        "knowledge_space_id": policy["knowledge_space_id"],
        "experience_id": checked["experience_id"],
        "action": action,
        "outcome": outcome,
        "evaluated_at": now,
        "raw_values_persisted": False,
    }
    audit["audit_hash"] = canonical_hash(audit)
    _atomic_create(root / "governance" / "audit" / "experience-writeback" / f"{request_id}.json", audit)
    return {"status": outcome, "experience_id": checked["experience_id"], "audit_hash": audit["audit_hash"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--writeback", action="store_true")
    parser.add_argument("--request-id", default="REQ-UI-TEST-EXPERIENCE")
    parser.add_argument("--now", default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    args = parser.parse_args()
    packet = json.loads(args.input.read_text(encoding="utf-8"))
    if not args.writeback:
        print(json.dumps({"status": "passed", "packet": validate_packet(packet)}, ensure_ascii=False, sort_keys=True))
        return 0
    if args.policy is None:
        raise SystemExit("--policy is required with --writeback")
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    print(json.dumps(writeback(packet, policy, request_id=args.request_id, now=args.now), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
