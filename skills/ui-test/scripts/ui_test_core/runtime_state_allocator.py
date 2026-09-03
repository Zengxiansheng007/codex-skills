"""Governed, concurrency-safe allocator for persistent runtime-state sequences."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .runtime_value_loader import (
    RuntimeValueError,
    compute_manual_hash,
    load_runtime_value_index,
    validate_runtime_state,
)
from .secret_governance import scan_value


class RuntimeStateError(RuntimeValueError):
    """Machine-readable allocation failure that never contains a credential value."""

    def __init__(self, issue: dict[str, Any]) -> None:
        self.issue = issue  # Keep the structured issue for machine-readable callers.
        super().__init__(issue["code"] + ": " + issue["message"])  # Surface only the code and redacted message.


def _issue(code: str, message: str, *, path: str = "$.runtime_state") -> dict[str, Any]:
    return {"code": code, "severity": "P0", "path": path, "message": message, "blocking_completion": True}  # Keep issue output stable and redacted.


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")  # Record a UTC ISO-8601 allocation timestamp.


class _ExclusiveLock:
    """Acquire a sibling lock file with exclusive creation; fail closed on contention."""

    def __init__(self, index_path: Path) -> None:
        self.lock_path = index_path.with_name(index_path.name + ".lock")  # Keep the lock beside the governed index.
        self._handle: Any = None  # Hold the OS-level handle so the lock survives until explicit release.

    def __enter__(self) -> "_ExclusiveLock":
        try:
            self._handle = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)  # Atomically claim the lock; no credential content is ever written.
        except FileExistsError as exc:
            raise RuntimeStateError(_issue("E_RVS_LOCK_CONTENTION", "runtime-state lock already held by another run")) from exc  # Fail closed rather than waiting or overwriting.
        except OSError as exc:
            raise RuntimeStateError(_issue("E_RVS_LOCK_UNAVAILABLE", exc.__class__.__name__)) from exc  # Surface only the failure class, never a path value.
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._handle is not None:
            try:
                os.close(self._handle)  # Release the OS handle first.
            except OSError:
                pass  # A close failure must not mask the original allocation result.
            try:
                self.lock_path.unlink()  # Remove only the writer-owned lock file.
            except OSError:
                pass  # A leftover lock on failure still forces the next run into contention fail-closed.
        self._handle = None  # Mark the lock as released even on the success path.


def _read_document(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Parse YAML without interpreting executable content.
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeStateError(_issue("E_RVS_FILE_UNREADABLE", exc.__class__.__name__)) from exc  # Surface only the parser failure class.
    if not isinstance(document, dict):
        raise RuntimeStateError(_issue("E_RVS_ROOT_INVALID", "runtime index root must be an object"))  # Reject scalar and list documents.
    return document


def _assert_manual_partition_unchanged(path: Path, observed_hash: str) -> None:
    current = load_runtime_value_index(path)  # Re-read immediately before replacement to detect a concurrent human edit.
    if current["manual_hash"] != observed_hash:
        raise RuntimeStateError(_issue("E_RVS_MANUAL_PARTITION_DRIFT", "manual hash changed before atomic replacement"))  # Never overwrite a moved human partition.


def _atomic_write(path: Path, document: dict[str, Any]) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)  # Keep the temporary file beside the target for atomic replacement.
            yaml.safe_dump(document, handle, allow_unicode=True, sort_keys=False)  # Serialize only after semantic validation.
            handle.flush()
            os.fsync(handle.fileno())  # Ensure the validated temporary file reaches the filesystem before replace.
        os.replace(temporary, path)  # Atomically publish the new runtime-state projection.
        temporary = None
    except OSError as exc:
        raise RuntimeStateError(_issue("E_RVS_ATOMIC_REPLACE_FAILED", exc.__class__.__name__)) from exc  # Never leave a partial index.
    finally:
        if temporary is not None:
            try:
                temporary.unlink()  # Remove only the writer-owned temporary file after a failed replace.
            except OSError:
                pass  # A cleanup failure must not mask the original allocation result.


def _validate_request(sequence_key: str, run_id: str, scope: str, evidence_ref: str) -> None:
    if not isinstance(sequence_key, str) or not sequence_key.strip():
        raise RuntimeStateError(_issue("E_RVS_SEQUENCE_KEY_INVALID", "sequence key must be a non-empty string"))  # Reject malformed allocation requests.
    if not isinstance(run_id, str) or not run_id.strip():
        raise RuntimeStateError(_issue("E_RVS_RUN_ID_INVALID", "run id must be a non-empty string"))  # Bind every allocation to a concrete run.
    if not isinstance(scope, str) or not scope.strip():
        raise RuntimeStateError(_issue("E_RVS_SCOPE_INVALID", "scope must be a non-empty string"))  # Bind the sequence to one declared business scope.
    if not isinstance(evidence_ref, str) or not evidence_ref.strip() or scan_value(evidence_ref, "$.runtime_state.evidence_ref"):
        raise RuntimeStateError(_issue("E_RVS_EVIDENCE_REF_INVALID", "evidence ref must be a non-empty, non-credential string"))  # Never persist credential-like evidence refs.


def initialize_runtime_sequence(
    path: str | Path,
    sequence_key: str,
    *,
    scope: str,
    description: str,
) -> dict[str, Any]:
    """Persist an empty sequence whose first future allocation will return 1."""
    target = Path(path).resolve()  # Resolve the governed index before locking it.
    if not target.is_file():
        raise RuntimeStateError(_issue("E_RVS_FILE_MISSING", "runtime value index does not exist", path="$"))  # Reject before touching the lock.
    _validate_request(sequence_key, "bootstrap", scope, "evidence:sequence-initialization")  # Reuse the redacted request contract.
    if not isinstance(description, str) or not description.strip():
        raise RuntimeStateError(_issue("E_RVS_DESCRIPTION_INVALID", "description must be a non-empty string"))  # Keep sequence ownership human-readable.
    with _ExclusiveLock(target):  # Serialize initialization with every allocation.
        observed = load_runtime_value_index(target)  # Validate schema, secrets and the human hash while holding the lock.
        observed_hash = observed["manual_hash"]  # Preserve the protected human partition digest.
        document = _read_document(target)  # Read the complete YAML for a machine-state-only update.
        state_partition = document.setdefault("runtime_state", {})  # Create only the optional machine-maintained partition.
        if not isinstance(state_partition, dict):
            raise RuntimeStateError(_issue("E_RVS_RUNTIME_STATE_INVALID", "runtime_state must be an object"))  # Reject malformed state.
        existing = state_partition.get(sequence_key)  # Detect an already initialized or used sequence.
        if existing is not None:
            validate_runtime_state(document)  # Fail closed if the existing sequence has drifted.
            if existing.get("scope") != scope or existing.get("description") != description:
                raise RuntimeStateError(_issue("E_RVS_SEQUENCE_CONFIG_CONFLICT", "existing sequence metadata differs from the requested configuration"))  # Never silently retarget a sequence.
            return {"status": "existing", "sequence_key": sequence_key, "next_value": existing["next_value"], "manual_hash": observed_hash, "source_path": str(target)}  # Idempotent initialization preserves prior allocations.
        state_partition[sequence_key] = {"next_value": 1, "allocations": [], "scope": scope, "description": description}  # Persist 1 as the first value to be allocated.
        if compute_manual_hash(document) != observed_hash:
            raise RuntimeStateError(_issue("E_RVS_MANUAL_PARTITION_DRIFT", "initialization changed the manual partition"))  # Initialization owns no human values.
        _assert_manual_partition_unchanged(target, observed_hash)  # Detect a concurrent human edit immediately before replace.
        _atomic_write(target, document)  # Publish the validated initialization atomically.
        readback = load_runtime_value_index(target)  # Prove the persisted sequence can be consumed by the standard loader.
        persisted = readback["runtime_state"].get(sequence_key)  # Resolve the exact initialized sequence.
        if not isinstance(persisted, dict) or persisted.get("next_value") != 1 or persisted.get("allocations") != []:
            raise RuntimeStateError(_issue("E_RVS_READBACK_MISMATCH", "persisted sequence initialization did not match the request"))  # Never claim a partial initialization.
        return {"status": "initialized", "sequence_key": sequence_key, "next_value": 1, "manual_hash": observed_hash, "source_path": str(target)}  # Return only non-sensitive initialization facts.


def allocate_runtime_sequence(
    path: str | Path,
    sequence_key: str,
    *,
    run_id: str,
    scope: str,
    evidence_ref: str,
    description: str = "",
) -> dict[str, Any]:
    """Allocate the next governed sequence value exactly once and persist the next counter.

    The first allocation returns ``1``; each later allocation returns the previous
    persisted ``next_value`` and then advances the stored counter by one. Allocation
    is monotonic and is never rolled back or reused after an uncertain outcome.
    """
    target = Path(path).resolve()  # Resolve the index before any lock or read.
    if not target.is_file():
        raise RuntimeStateError(_issue("E_RVS_FILE_MISSING", "runtime value index does not exist", path="$"))  # Reject before touching the lock.
    _validate_request(sequence_key, run_id, scope, evidence_ref)  # Validate redacted allocation metadata before taking the lock.
    normalized_description = description.strip() if isinstance(description, str) and description.strip() else f"Governed sequence: {sequence_key}"  # Keep legacy callers deterministic while persisting explicit ownership.
    with _ExclusiveLock(target):  # Hold the sibling lock for the whole read-validate-write cycle.
        observed = load_runtime_value_index(target)  # Re-read and validate the index (schema, hash, secrets) while holding the lock.
        observed_hash = observed["manual_hash"]  # Capture the human partition digest for the optimistic concurrency check.
        document = _read_document(target)  # Read the complete source for the final in-place mutation.
        state_partition = document.setdefault("runtime_state", {})  # Reference the machine-maintained partition without touching the human one.
        if not isinstance(state_partition, dict):
            raise RuntimeStateError(_issue("E_RVS_RUNTIME_STATE_INVALID", "runtime_state must be an object"))  # Reject a malformed partition type.
        validate_runtime_state(document)  # Re-validate every existing sequence entry before allocating.
        entry = state_partition.get(sequence_key)  # Resolve the governed sequence after validating all existing state.
        if entry is None:
            entry = {"next_value": 1, "allocations": [], "scope": scope, "description": normalized_description}  # Allow first use to initialize and allocate atomically.
            state_partition[sequence_key] = entry  # Attach only the new machine-maintained sequence.
        if not isinstance(entry, dict):
            raise RuntimeStateError(_issue("E_RVS_ENTRY_INVALID", "existing sequence entry must be an object", path=f"$.runtime_state.{sequence_key}"))  # Reject malformed state.
        if entry.get("scope") != scope or entry.get("description") != normalized_description:
            raise RuntimeStateError(_issue("E_RVS_SEQUENCE_CONFIG_CONFLICT", "existing sequence metadata differs from the requested configuration"))  # Prevent cross-scope sequence reuse.
        allocations = entry.get("allocations")  # Use the validated append-only ledger for duplicate-run checks.
        if not isinstance(allocations, list):
            raise RuntimeStateError(_issue("E_RVS_ALLOCATIONS_INVALID", "existing allocation ledger must be an array"))  # Fail closed on drift.
        if any(allocation.get("run_id") == run_id for allocation in allocations if isinstance(allocation, dict)):
            raise RuntimeStateError(_issue("E_RVS_DUPLICATE_RUN_ALLOCATION", "the same run already allocated this sequence", path=f"$.runtime_state.{sequence_key}.allocations"))  # Reject retries even after other runs allocate.
        allocated_value = entry["next_value"]  # Hand out the counter value proven consistent with the ledger.
        allocations.append({"value": allocated_value, "run_id": run_id, "allocated_at": _utc_now(), "evidence_ref": evidence_ref})  # Append immutable allocation lineage.
        entry["next_value"] = allocated_value + 1  # Advance the counter so the next creation uses previous plus one.
        if compute_manual_hash(document) != observed_hash:
            raise RuntimeStateError(_issue("E_RVS_MANUAL_PARTITION_DRIFT", "allocation changed the manual partition"))  # The allocator must never move human values.
        _assert_manual_partition_unchanged(target, observed_hash)  # Fail closed when a concurrent human edit raced the lock.
        _atomic_write(target, document)  # Publish only after every pre-write check passes.
        readback = load_runtime_value_index(target)  # Read back the final file to verify the atomic result.
        persisted = readback["runtime_state"].get(sequence_key)
        persisted_allocations = persisted.get("allocations") if isinstance(persisted, dict) else None  # Resolve the read-back ledger safely.
        if not isinstance(persisted, dict) or persisted.get("next_value") != allocated_value + 1 or not isinstance(persisted_allocations, list) or persisted_allocations[-1].get("value") != allocated_value or persisted_allocations[-1].get("run_id") != run_id:
            raise RuntimeStateError(_issue("E_RVS_READBACK_MISMATCH", "persisted sequence state did not match the allocation"))  # Never report success on an unverified file.
        return {  # Return only the allocation facts the caller needs.
            "sequence_key": sequence_key,
            "allocated_value": allocated_value,  # The value handed out for the visible UI.
            "next_value": allocated_value + 1,  # The counter the next allocation will read.
            "run_id": run_id,
            "scope": scope,
            "manual_hash": observed_hash,  # Confirm the human partition is unchanged.
            "source_path": str(target),
        }
