"""Atomic writer for exploration values in a governed runtime index."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .runtime_value_loader import (
    RuntimeValueError,
    compute_manual_hash,
    load_runtime_value_index,
)
from .secret_governance import scan_value


class RuntimeValueWriteError(RuntimeValueError):
    """Machine-readable write failure that never contains a raw value."""

    def __init__(self, issue: dict[str, Any]) -> None:
        self.issue = issue
        super().__init__(issue["code"] + ": " + issue["message"])


def _issue(code: str, message: str, *, path: str = "$") -> dict[str, Any]:
    return {"code": code, "severity": "P0", "path": path, "message": message, "blocking_completion": True}  # Keep issue output stable and redacted.


def _read_document(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Parse YAML without interpreting executable content.
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeValueWriteError(_issue("E_RVI_FILE_UNREADABLE", exc.__class__.__name__)) from exc
    if not isinstance(document, dict):
        raise RuntimeValueWriteError(_issue("E_RVI_ROOT_INVALID", "runtime index root must be an object"))
    return document


def _validate_non_credential_value(value: Any) -> None:
    if scan_value(value, "$.exploration_values.value"):
        raise RuntimeValueWriteError(_issue("E_RVI_SECRET_DETECTED", "secret-like value is forbidden in exploration partition"))


def _validate_url_host(value: Any, allowed_hosts: set[str]) -> None:
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return
    host = urlsplit(value).netloc
    if not allowed_hosts or host not in allowed_hosts:
        raise RuntimeValueWriteError(_issue("E_RVI_HOST_NOT_ALLOWED", "exploration URL host is outside the approved host set"))


def _atomic_write(path: Path, document: dict[str, Any]) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)  # Keep the temporary file beside the target for atomic replacement.
            yaml.safe_dump(document, handle, allow_unicode=True, sort_keys=False)  # Serialize only after semantic validation.
            handle.flush()
            os.fsync(handle.fileno())  # Ensure the validated temporary file reaches the filesystem before replace.
        os.replace(temporary, path)  # Atomically publish the new exploration projection.
        temporary = None
    except OSError as exc:
        raise RuntimeValueWriteError(_issue("E_RVI_ATOMIC_REPLACE_FAILED", exc.__class__.__name__)) from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink()  # Remove only the writer-owned temporary file after failure.
            except OSError:
                pass


def _assert_manual_partition_unchanged(path: Path, observed_hash: str) -> None:
    current = load_runtime_value_index(path)  # Re-read immediately before replacement to detect a concurrent human edit.
    if current["manual_hash"] != observed_hash:
        raise RuntimeValueWriteError(_issue("E_RVI_CONCURRENT_MODIFICATION", "manual hash changed before atomic replacement"))


def append_exploration_value(
    path: str | Path,
    key: str,
    value: Any,
    *,
    run_id: str,
    scope: str,
    evidence_ref: str,
    description: str = "",
    allowed_hosts: set[str] | None = None,
    expected_manual_hash: str | None = None,
) -> dict[str, Any]:
    """Append one candidate exploration value without changing the manual partition."""
    target = Path(path).resolve()  # Resolve the target before reading or writing it.
    if not target.is_file():
        raise RuntimeValueWriteError(_issue("E_RVI_FILE_MISSING", "runtime value index does not exist"))
    original = _read_document(target)  # Read the complete source once for the optimistic concurrency check.
    loaded = load_runtime_value_index(target)  # Reuse the loader for schema, hash, path and sensitive gates.
    observed_hash = loaded["manual_hash"]
    if expected_manual_hash is not None and expected_manual_hash != observed_hash:
        raise RuntimeValueWriteError(_issue("E_RVI_CONCURRENT_MODIFICATION", "manual hash changed before write"))
    if key in original.get("runtime_values", {}):
        raise RuntimeValueWriteError(_issue("E_RVI_MANUAL_KEY_COLLISION", "exploration key collides with a manual key", path=f"$.exploration_values.{key}"))
    if key in original.get("exploration_values", {}):
        raise RuntimeValueWriteError(_issue("E_RVI_EXPLORATION_KEY_EXISTS", "exploration key already exists", path=f"$.exploration_values.{key}"))
    _validate_non_credential_value(value)  # Do not persist token-like or credential-like values in the exploration partition.
    _validate_url_host(value, allowed_hosts or set())  # URL discoveries require an explicit approved host set.
    original.setdefault("exploration_values", {})[key] = {
        "value": value,
        "source_type": "literal",
        "status": "candidate",
        "run_id": run_id,
        "discovered_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),  # Record a UTC discovery timestamp.
        "scope": scope,
        "evidence_ref": evidence_ref,
        "description": description,
    }  # Append a fully traceable candidate entry.
    if compute_manual_hash(original) != observed_hash:
        raise RuntimeValueWriteError(_issue("E_RVI_MANUAL_PARTITION_CHANGED", "writer changed the manual partition"))
    _assert_manual_partition_unchanged(target, observed_hash)  # Fail closed even when the caller did not provide an optimistic token.
    _atomic_write(target, original)  # Publish only after every pre-write check passes.
    load_runtime_value_index(target)  # Read back the final file to verify the atomic result.
    return {"status": "candidate", "key": key, "manual_hash": observed_hash, "source_path": str(target)}


def promote_exploration_value(path: str | Path, key: str, *, allowed_hosts: set[str]) -> dict[str, Any]:
    """Promote a validated non-credential candidate to active without changing manual values."""
    target = Path(path).resolve()  # Resolve before applying the same governed write path.
    original = _read_document(target)  # Preserve the source for the final manual hash comparison.
    loaded = load_runtime_value_index(target)  # Fail closed before any promotion.
    entry = original.get("exploration_values", {}).get(key)
    if not isinstance(entry, dict) or entry.get("status") != "candidate":
        raise RuntimeValueWriteError(_issue("E_RVI_CANDIDATE_NOT_FOUND", "only candidate exploration values can be promoted", path=f"$.exploration_values.{key}"))
    _validate_non_credential_value(entry.get("value"))  # Recheck the value at promotion time.
    _validate_url_host(entry.get("value"), allowed_hosts)  # Require the approved host set for URL promotion.
    entry["status"] = "active"  # Codex self-approval changes only the machine-owned exploration state.
    if compute_manual_hash(original) != loaded["manual_hash"]:
        raise RuntimeValueWriteError(_issue("E_RVI_MANUAL_PARTITION_CHANGED", "promotion changed the manual partition"))
    _assert_manual_partition_unchanged(target, loaded["manual_hash"])  # Protect promotion from a concurrent manual edit.
    _atomic_write(target, original)  # Use the same atomic writer for candidate promotion.
    load_runtime_value_index(target)  # Verify the post-promotion document before returning.
    return {"status": "active", "key": key, "manual_hash": loaded["manual_hash"], "source_path": str(target)}
