"""Offline validation and append-only state logic for document publishing."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


STATES = {
    "draft",
    "preflight-passed",
    "github-published",
    "gitbook-sync-pending",
    "gitbook-verified",
    "failed",
    "rolled-back",
}
TRANSITIONS = {
    ("draft", "preflight-passed"),
    ("preflight-passed", "github-published"),
    ("github-published", "gitbook-sync-pending"),
    ("gitbook-sync-pending", "gitbook-verified"),
    ("github-published", "failed"),
    ("gitbook-sync-pending", "failed"),
    ("gitbook-verified", "rolled-back"),
    ("github-published", "rolled-back"),
}
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def idempotency_key(manifest: dict[str, Any]) -> str:
    return ":".join(str(manifest[field]) for field in ("docId", "version", "sourceCommit"))


def validate_manifest(manifest: dict[str, Any], content: str | None = None) -> list[str]:
    errors: list[str] = []
    required = ("docId", "category", "phase", "version", "sourceCommit", "integrity", "classification", "paths", "provenance", "status")
    for field in required:
        if field not in manifest:
            errors.append(f"missing:{field}")
    if errors:
        return errors
    if not isinstance(manifest["docId"], str) or not manifest["docId"]:
        errors.append("invalid:docId")
    if not SEMVER.fullmatch(str(manifest["version"])):
        errors.append("invalid:version")
    if not SHA1.fullmatch(str(manifest["sourceCommit"])):
        errors.append("invalid:sourceCommit")
    integrity = manifest["integrity"]
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "SHA-256" or not SHA256.fullmatch(str(integrity.get("digest", ""))):
        errors.append("invalid:integrity")
    if manifest["status"] not in STATES:
        errors.append("invalid:status")
    if not isinstance(manifest.get("classification"), dict):
        errors.append("invalid:classification")
    if content is not None and digest_text(content) != integrity.get("digest"):
        errors.append("digest-mismatch")
    return errors


def transition(record: dict[str, Any], target: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    source = str(record.get("status", ""))
    if target not in STATES or (source, target) not in TRANSITIONS:
        raise ValueError(f"invalid-transition:{source}->{target}")
    evidence = evidence or {}
    if target == "github-published" and not evidence.get("commitSha"):
        raise ValueError("missing-evidence:commitSha")
    if target == "gitbook-verified" and not evidence.get("contentCheck"):
        raise ValueError("missing-evidence:contentCheck")
    if target in {"failed", "rolled-back"} and not evidence.get("reason"):
        raise ValueError(f"missing-evidence:reason:{target}")
    updated = dict(record)
    updated["status"] = target
    updated["history"] = list(record.get("history", [])) + [{"from": source, "to": target, "evidence": evidence}]
    return updated


def register_or_reuse(manifest: dict[str, Any], registry: list[dict[str, Any]]) -> dict[str, Any]:
    key = idempotency_key(manifest)
    for record in registry:
        if record.get("idempotencyKey") == key:
            return {"reused": True, "idempotencyKey": key, "record": record}
    record = {"idempotencyKey": key, "status": manifest["status"], "history": [], "manifest": manifest}
    registry.append(record)
    return {"reused": False, "idempotencyKey": key, "record": record}


def rollback(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return transition(record, "rolled-back", {"reason": reason, "rollbackOf": idempotency_key(record["manifest"])})
