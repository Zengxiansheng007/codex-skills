"""Attachment-first evidence records with safe paths and content hashes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


ALLOWED_MISSING = {"not-produced", "blocked-by-policy", "permission-failed", "timeout", "unsupported", "removed-after-retention"}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def attachment(*, attachment_id: str, step_id: str, kind: str, path: str | None = None, missing_reason: str | None = None, redaction_status: str = "clear") -> dict[str, Any]:
    if not path and missing_reason not in ALLOWED_MISSING:
        raise ValueError("E_EVIDENCE_MISSING: invalid missing reason")
    return {"attachment_id": attachment_id, "step_id": step_id, "kind": kind, "path": path, "sha256": sha256_file(path) if path else None, "missing_reason": missing_reason, "redaction_status": redaction_status}
