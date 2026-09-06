"""Deterministic V2 Grill ledger operations and bounded batch-writeback evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grill_artifact_checks import (  # Local helper deliberately has no document-merging capability.
    BoundaryError,
    diff_snapshots,
    relative_workspace_path,
    scope_contains,
    snapshot_protected_assets,
    verify_expected_postconditions,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
V2_SCHEMA = SKILL_ROOT / "schemas" / "grill-session-v2.schema.json"
PHASES = {"grilling", "awaiting-closure", "review-ended", "writeback", "writeback-complete", "paused", "repair-needed", "blocked"}
RESULTS = {"in-progress", "ready-for-writeback", "conclusions-only", "completed", "partial-failure", "blocked", "repair-needed", "legacy-read-only"}
QUESTION_OPEN = {"proposed", "needs-evidence"}


class LedgerError(ValueError):
    """A caller requested a transition that the ledger cannot safely make."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LedgerError("ledger must be a JSON object")
    return value


def _write_json(path: str | Path, value: dict[str, Any], create: bool = False) -> None:
    """Persist through a sibling file; an interrupted write leaves recoverable evidence."""
    destination = Path(path)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if create:
            os.link(temporary_name, destination)  # Atomic no-clobber publication for a new canonical ledger.
            os.unlink(temporary_name)
        else:
            os.replace(temporary_name, destination)  # Existing ledger replacement is atomic on this volume.
    except Exception:
        raise  # Keep the sibling temporary file for recovery rather than hiding a partial-write failure.


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _decision_fingerprint(ledger: dict[str, Any]) -> str:
    """Bind text and consequences, not only stable decision IDs, to a writeback batch."""
    return _fingerprint([item for item in ledger.get("decisions", []) if item.get("status") == "effective"])


def _legacy_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    if ledger.get("schemaVersion") == "2.0":
        return []
    return [{"severity": "P1", "rule": "legacy-read-only", "message": "legacy session has no V2 closure/writeback evidence and is read-only"}]


def new_ledger(session_id: str, scenario: str, record_mode: str = "ledger", session_path: str | Path | None = None, workspace_root: str | Path | None = None) -> dict[str, Any]:
    if record_mode not in {"ledger", "conversation-only"}:
        raise LedgerError("recordMode must be ledger or conversation-only")
    if session_path is None:
        raise LedgerError("new ledger needs its canonical session path")
    canonical = Path(session_path).resolve(strict=False)
    root = Path(workspace_root).resolve(strict=True) if workspace_root else canonical.parent.resolve()
    if record_mode == "ledger" and canonical.exists():
        raise LedgerError("refusing to overwrite an existing ledger or user file")
    if record_mode == "ledger" and not canonical.parent.is_dir():
        raise LedgerError("ledger parent directory must already exist")
    return {
        "schemaVersion": "2.0",
        "sessionId": session_id,
        "scenario": scenario,
        "ledgerPath": str(canonical) if record_mode == "ledger" else "conversation-only",
        "workspaceRoot": str(root),
        "phase": "grilling",
        "result": "in-progress",
        "recordMode": record_mode,
        "questions": [],
        "decisions": [],
        "effectiveDecisions": [],
        "evidenceIndex": [],
        "openItems": [],
        "nextActions": [],
        "sourceBaseline": [],
        "protectedAssets": [],
        "processArtifacts": [{"kind": "ledger", "path": str(canonical)}] if record_mode == "ledger" else [],
        "closureEvidence": {},
        "writebackPolicy": {"mode": "default-batch", "approvedScopes": [], "authorization": "default-on-session-closure"},
        "exceptions": [],
        "recovery": {"lastSafePhase": "grilling", "nextQuestionId": None},
        "checkpoints": [],
        "writebackReceipts": [],
        "history": [{"event": "created", "at": utc_now()}],
    }


def _schema_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    try:
        import jsonschema  # Machine-provided dependency, intentionally not installed by this package.
    except ImportError:
        return [{"severity": "P0", "rule": "jsonschema-unavailable", "message": "V2 validation requires the preinstalled jsonschema package"}]
    schema = json.loads(V2_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [{"severity": "P0", "rule": "schema-violation", "message": error.message} for error in validator.iter_errors(ledger)]


def _p0_crosscheck_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    questions = {q.get("id"): q for q in ledger.get("questions", []) if isinstance(q, dict) and q.get("id")}
    p0_open_items = [item for item in ledger.get("openItems", []) if isinstance(item, dict) and item.get("severity") == "P0"]
    p0_open_by_question = {item.get("sourceQuestion") for item in p0_open_items}
    unresolved_questions = [q for q in questions.values() if q.get("severity") == "P0" and q.get("status") in QUESTION_OPEN]
    for question in unresolved_questions:
        if question["id"] not in p0_open_by_question:
            issues.append({"severity": "P0", "rule": "unresolved-p0-missing-open-item", "message": f"{question['id']} is unresolved P0 but has no matching openItems sourceQuestion"})
    for item in p0_open_items:
        source = item.get("sourceQuestion")
        if not source or source not in questions:
            issues.append({"severity": "P0", "rule": "p0-open-item-missing-question", "message": f"{item.get('id', 'open item')} needs a valid sourceQuestion"})
    return issues


def _answered_question_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    for question in ledger.get("questions", []):
        if not isinstance(question, dict):
            continue
        if question.get("status") in {"confirmed", "changed", "rejected"} and not str(question.get("userResponse", "")).strip():
            issues.append({"severity": "P0", "rule": "answered-question-missing-response", "message": f"{question.get('id', 'question')} has a terminal status without a user response"})
    return issues


def _risk_acceptance_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    acceptances = {item.get("openItemId"): item for item in ledger.get("riskAcceptances", []) if isinstance(item, dict)}
    for item in ledger.get("openItems", []):
        if not isinstance(item, dict) or item.get("severity") != "P0":
            continue
        acceptance = acceptances.get(item.get("id"))
        required = ("risk", "acceptanceBasis", "scope", "acceptedBy")
        if not acceptance or any(not acceptance.get(name) for name in required):
            issues.append({"severity": "P0", "rule": "concrete-risk-acceptance-required", "message": f"P0 open item {item.get('id')} lacks a concrete risk acceptance"})
    return issues


def _exception_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for exception in ledger.get("exceptions", []):
        if not isinstance(exception, dict):
            issues.append({"severity": "P0", "rule": "invalid-exception", "message": "exception must be an object"})
            continue
        if exception.get("status") not in {"active", "consumed", "verified", "expired"}:
            issues.append({"severity": "P0", "rule": "invalid-exception-status", "message": "exception has invalid status"})
        if exception.get("status") == "active":
            missing = [field for field in ("id", "authorization", "scope", "preCheckpointId") if not exception.get(field)]
            if missing:
                issues.append({"severity": "P0", "rule": "incomplete-active-exception", "message": f"active exception missing {', '.join(missing)}"})
    return issues


def _closure_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    """Reject a forged review-ended/writeback state even when a caller sets fields directly."""
    phase = ledger.get("phase")
    if phase not in {"review-ended", "writeback", "writeback-complete"}:
        return []
    closure = ledger.get("closureEvidence", {})
    issues = []
    if any(not closure.get(field) for field in ("statement", "source", "recordedAt")):
        issues.append({"severity": "P0", "rule": "closure-evidence-required", "message": "review-ended/writeback requires explicit closure evidence"})
    policy = ledger.get("writebackPolicy", {})
    if policy.get("mode") not in {"default-batch", "conclusions-only", "deferred"}:
        issues.append({"severity": "P0", "rule": "invalid-writeback-policy", "message": "writeback policy mode is invalid"})
    if phase in {"writeback", "writeback-complete"} and policy.get("mode") != "default-batch":
        issues.append({"severity": "P0", "rule": "writeback-policy-denied", "message": "only default-batch can enter formal writeback"})
    return issues


def _pending_exception_issues(ledger: dict[str, Any]) -> list[dict[str, str]]:
    pending = ledger.get("recovery", {}).get("exceptionPendingId")
    return [{"severity": "P0", "rule": "exception-postcondition-pending", "message": "consumed mid-review exception needs post-change verification"}] if pending else []


def _storage_issues(ledger: dict[str, Any], session_path: str | Path) -> list[dict[str, str]]:
    """Bind mutations to one ledger and reject aliases into protected formal scopes."""
    issues: list[dict[str, str]] = []
    supplied = Path(session_path).resolve(strict=False)
    if str(supplied) != ledger.get("ledgerPath"):
        return [{"severity": "P0", "rule": "noncanonical-ledger-path", "message": "mutations must use the ledger's canonical path"}]
    try:
        root = Path(ledger["workspaceRoot"]).resolve(strict=True)
        for artifact in ledger.get("processArtifacts", []):
            if not isinstance(artifact, dict) or not artifact.get("path"):
                issues.append({"severity": "P0", "rule": "invalid-process-artifact", "message": "process artifact needs a path"})
                continue
            if scope_contains(root, ledger.get("protectedAssets", []), artifact["path"]):
                issues.append({"severity": "P0", "rule": "process-artifact-protected-overlap", "message": f"process artifact overlaps protected asset: {artifact['path']}"})
    except (OSError, BoundaryError, KeyError) as exc:
        issues.append({"severity": "P0", "rule": "process-artifact-path-invalid", "message": str(exc)})
    return issues


def validate_ledger(ledger: dict[str, Any], intent: str = "read") -> list[dict[str, str]]:
    """Validate semantic gates; write intent always refuses a legacy ledger."""
    issues = _legacy_issues(ledger)
    if issues:
        if intent != "read":
            issues.append({"severity": "P0", "rule": "legacy-write-denied", "message": "legacy reports preserve read-only validation but cannot authorize writeback"})
        return issues
    issues.extend(_schema_issues(ledger))
    if ledger.get("phase") not in PHASES:
        issues.append({"severity": "P0", "rule": "invalid-phase", "message": "phase is not a V2 phase"})
    if ledger.get("result") not in RESULTS:
        issues.append({"severity": "P0", "rule": "invalid-result", "message": "result is not a V2 result"})
    issues.extend(_p0_crosscheck_issues(ledger))
    issues.extend(_answered_question_issues(ledger))
    if intent in {"close", "write"}:
        issues.extend(_risk_acceptance_issues(ledger))  # Ordinary question work may still have unaccepted P0 items.
    issues.extend(_exception_issues(ledger))
    issues.extend(_pending_exception_issues(ledger))
    issues.extend(_closure_issues(ledger))
    return issues


def ensure_mutable_ledger(ledger: dict[str, Any], session_path: str | Path, allow_pending_exception: bool = False) -> None:
    """Guard ledger persistence only; formal-write and close gates stay command-specific."""
    if ledger.get("schemaVersion") != "2.0":
        raise LedgerError("mutation refused: legacy-write-denied")
    issues = validate_ledger(ledger, intent="read")
    if allow_pending_exception:
        issues = [item for item in issues if item["rule"] != "exception-postcondition-pending"]
    issues.extend(_storage_issues(ledger, session_path))
    fatal = [issue for issue in issues if issue["severity"] == "P0"]
    if fatal:
        raise LedgerError("mutation refused: " + "; ".join(item["rule"] for item in fatal))


def _has_unaccepted_p0(ledger: dict[str, Any]) -> bool:
    return bool(_risk_acceptance_issues(ledger)) or any(
        item.get("severity") == "P0" for item in ledger.get("openItems", []) if isinstance(item, dict)
    ) and not bool(ledger.get("riskAcceptances"))


def _append_event(ledger: dict[str, Any], event: str, **details: Any) -> None:
    ledger.setdefault("history", []).append({"event": event, "at": utc_now(), **details})


def record_answer(ledger: dict[str, Any], question_id: str, answer: str, status: str, decision: str | None = None) -> dict[str, Any]:
    if ledger.get("recovery", {}).get("exceptionPendingId"):
        raise LedgerError("record-answer is frozen until the consumed exception is verified")
    if ledger.get("phase") not in {"grilling", "awaiting-closure"}:
        raise LedgerError("answers can only be recorded during grilling")
    question = next((item for item in ledger["questions"] if item.get("id") == question_id), None)
    if question is None:
        raise LedgerError(f"unknown question: {question_id}")
    if status not in {"confirmed", "changed", "rejected", "needs-evidence"}:
        raise LedgerError("answer status is invalid")
    question["userResponse"] = answer
    question["status"] = status
    if status in {"confirmed", "changed", "rejected"}:
        ledger["openItems"] = [item for item in ledger.get("openItems", []) if item.get("sourceQuestion") != question_id]  # Resolved answers cannot leave stale P0 blockers.
    if decision:
        ledger.setdefault("decisions", []).append({"id": f"D-{len(ledger['decisions']) + 1:03d}", "sourceQuestion": question_id, "decision": decision, "status": "effective", "recordedAt": utc_now()})
        ledger["effectiveDecisions"] = [item["id"] for item in ledger["decisions"] if item.get("status") == "effective"]
    ledger["phase"] = "awaiting-closure"
    ledger["recovery"]["lastSafePhase"] = "awaiting-closure"
    _append_event(ledger, "answer-recorded", questionId=question_id)
    return ledger


def propose_question(ledger: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Append one next question to the sole ledger and create its P0 open item when needed."""
    if ledger.get("phase") not in {"grilling", "awaiting-closure"} or ledger.get("recovery", {}).get("exceptionPendingId"):
        raise LedgerError("question proposal is unavailable outside an unfrozen review")
    required = ("id", "question", "purpose", "recommendedAnswer", "blockingDecision", "severity")
    if any(not str(proposal.get(field, "")).strip() for field in required):
        raise LedgerError("question proposal needs id, question, purpose, recommendedAnswer, blockingDecision, and severity")
    if proposal["severity"] not in {"P0", "P1", "P2"} or any(item.get("id") == proposal["id"] for item in ledger.get("questions", [])):
        raise LedgerError("question proposal has invalid severity or duplicate id")
    if any(item.get("status") == "proposed" for item in ledger.get("questions", [])):
        raise LedgerError("one-question-at-a-time gate has an existing open question")
    if str(proposal["question"]).count("?") + str(proposal["question"]).count("？") > 1:
        raise LedgerError("question proposal appears to contain more than one question")
    question = {field: proposal[field] for field in required}
    question.update({"status": "proposed", "evidence": list(proposal.get("evidence", [])), "reopenHistory": []})
    ledger.setdefault("questions", []).append(question)
    if question["severity"] == "P0":
        open_id = f"O-{question['id']}"
        ledger.setdefault("openItems", []).append({"id": open_id, "severity": "P0", "sourceQuestion": question["id"], "question": question["question"]})
    ledger["phase"] = "grilling"; ledger["result"] = "in-progress"
    ledger["recovery"]["nextQuestionId"] = question["id"]
    _append_event(ledger, "question-proposed", questionId=question["id"])
    return ledger


def close_session(ledger: dict[str, Any], closure: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
    issues = validate_ledger(ledger, intent="close")
    fatal = [issue for issue in issues if issue["severity"] == "P0"]
    if fatal:
        raise LedgerError("closure refused: " + "; ".join(item["rule"] for item in fatal))
    required = ("statement", "source", "recordedAt")
    if any(not closure.get(item) for item in required):
        raise LedgerError("closure evidence needs statement, source, and recordedAt")
    effective_mode = mode or ledger["writebackPolicy"].get("mode", "default-batch")
    if effective_mode not in {"default-batch", "conclusions-only", "deferred"}:
        raise LedgerError("unknown writeback mode")
    ledger["closureEvidence"] = copy.deepcopy(closure)
    ledger["writebackPolicy"]["mode"] = effective_mode
    ledger["phase"] = "review-ended"
    ledger["result"] = "conclusions-only" if effective_mode in {"conclusions-only", "deferred"} else "ready-for-writeback"
    ledger["recovery"]["lastSafePhase"] = "review-ended"
    _append_event(ledger, "session-closed", mode=effective_mode)
    return ledger


def pause_session(ledger: dict[str, Any], next_question_id: str | None) -> dict[str, Any]:
    if ledger.get("phase") in {"writeback-complete", "repair-needed", "blocked"}:
        raise LedgerError("terminal session phase cannot be paused")
    ledger["recovery"] = {"lastSafePhase": ledger.get("phase"), "nextQuestionId": next_question_id, "pausedAt": utc_now()}
    ledger["phase"] = "paused"
    _append_event(ledger, "paused")
    return ledger


def resume_session(ledger: dict[str, Any]) -> dict[str, Any]:
    if ledger.get("phase") != "paused":
        raise LedgerError("only a paused session can resume")
    phase = ledger.get("recovery", {}).get("lastSafePhase")
    if phase not in PHASES - {"paused"}:
        raise LedgerError("paused session lacks a valid recovery phase")
    ledger["phase"] = phase
    _append_event(ledger, "resumed", phase=phase)
    return ledger


def reopen_question(ledger: dict[str, Any], question_id: str, reason: str, evidence_ref: str) -> dict[str, Any]:
    if not reason or not evidence_ref:
        raise LedgerError("reopen requires new evidence and a reason")
    question = next((item for item in ledger.get("questions", []) if item.get("id") == question_id), None)
    if question is None:
        raise LedgerError(f"unknown question: {question_id}")
    question.setdefault("reopenHistory", []).append({"at": utc_now(), "priorStatus": question.get("status"), "reason": reason, "evidenceRef": evidence_ref})
    question["status"] = "proposed"
    for decision in ledger.get("decisions", []):
        if decision.get("sourceQuestion") == question_id and decision.get("status") == "effective":
            decision["status"] = "superseded"
            decision["supersededBy"] = question_id
    ledger["effectiveDecisions"] = [item["id"] for item in ledger.get("decisions", []) if item.get("status") == "effective"]
    ledger["phase"] = "grilling"
    ledger["result"] = "in-progress"
    _append_event(ledger, "question-reopened", questionId=question_id, evidenceRef=evidence_ref)
    return ledger


def create_checkpoint(ledger: dict[str, Any], workspace_root: str | Path, checkpoint_id: str) -> dict[str, Any]:
    if not checkpoint_id:
        raise LedgerError("checkpoint id is required")
    if any(item.get("id") == checkpoint_id for item in ledger.get("checkpoints", [])):
        raise LedgerError("checkpoint id already exists")
    root = Path(workspace_root).resolve(strict=True)
    if root != Path(ledger["workspaceRoot"]).resolve(strict=True):
        raise LedgerError("checkpoint workspace root does not match the ledger-bound root")
    snapshot = snapshot_protected_assets(root, ledger.get("protectedAssets", []))
    checkpoint = {"id": checkpoint_id, "createdAt": utc_now(), "workspaceRoot": str(root), "snapshot": snapshot, "snapshotHash": _fingerprint(snapshot), "approvedForWriteback": not ledger.get("checkpoints")}  # Later observations cannot silently replace the approved review baseline.
    ledger.setdefault("checkpoints", []).append(checkpoint)
    _append_event(ledger, "checkpoint-created", checkpointId=checkpoint_id)
    return ledger


def consume_exception(ledger: dict[str, Any], workspace_root: str | Path, exception_id: str, target_path: str) -> dict[str, Any]:
    """Consume one narrowly authorized mid-review exception before an external edit."""
    if ledger.get("phase") not in {"grilling", "awaiting-closure"}:
        raise LedgerError("mid-review exceptions are unavailable after review closure")
    exception = next((item for item in ledger.get("exceptions", []) if item.get("id") == exception_id), None)
    if exception is None or exception.get("status") != "active":
        raise LedgerError("exception is missing, expired, or already consumed")
    if not scope_contains(workspace_root, exception.get("scope", []), target_path):
        raise LedgerError("exception target is outside its bounded scope")
    checkpoint = _verified_checkpoint(ledger, workspace_root, exception["preCheckpointId"])
    current = snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))
    if diff_snapshots(checkpoint["snapshot"], current):
        raise LedgerError("exception baseline drift requires review before a mid-review edit")
    exception["status"] = "consumed"  # A one-use authorization cannot silently persist to the next answer.
    exception["consumedAt"] = utc_now()
    exception["consumedTarget"] = target_path
    ledger.setdefault("recovery", {})["exceptionPendingId"] = exception_id
    _append_event(ledger, "exception-consumed", exceptionId=exception_id, targetPath=target_path)
    return ledger


def finish_exception(ledger: dict[str, Any], workspace_root: str | Path, exception_id: str, postconditions: list[dict[str, Any]], checkpoint_id: str) -> dict[str, Any]:
    """Verify the authorized edit, record its actual delta, and restore the review freeze."""
    exception = next((item for item in ledger.get("exceptions", []) if item.get("id") == exception_id), None)
    if exception is None or exception.get("status") != "consumed" or ledger.get("recovery", {}).get("exceptionPendingId") != exception_id:
        raise LedgerError("only the pending consumed exception can be finished")
    if any(item.get("id") == checkpoint_id for item in ledger.get("checkpoints", [])):
        raise LedgerError("post-exception checkpoint id already exists")
    expected_target = exception.get("consumedTarget")
    if len(postconditions) != 1 or postconditions[0].get("path") != expected_target:
        raise LedgerError("exception postconditions must cover exactly its consumed target")
    verified = verify_expected_postconditions(workspace_root, postconditions)
    if any(item.get("status") != "verified" for item in verified):
        raise LedgerError("exception postconditions did not match actual content")
    before = _verified_checkpoint(ledger, workspace_root, exception["preCheckpointId"])
    current = snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))
    changes = diff_snapshots(before["snapshot"], current)
    normalized_target = str(expected_target).replace("\\", "/")
    if not changes or any(change["path"] != normalized_target for change in changes):
        raise LedgerError("exception changed an unapproved protected target or made no observable change")
    checkpoint = {"id": checkpoint_id, "createdAt": utc_now(), "workspaceRoot": str(Path(workspace_root).resolve()), "snapshot": current, "snapshotHash": _fingerprint(current), "approvedForWriteback": True, "exceptionId": exception_id, "postconditions": verified, "observedChanges": changes}
    ledger.setdefault("checkpoints", []).append(checkpoint)
    exception["status"] = "verified"; exception["postCheckpointId"] = checkpoint_id; exception["postconditions"] = verified
    ledger["recovery"].pop("exceptionPendingId", None)
    _append_event(ledger, "exception-verified-and-frozen", exceptionId=exception_id, checkpointId=checkpoint_id)
    return ledger


def _checkpoint(ledger: dict[str, Any], checkpoint_id: str) -> dict[str, Any]:
    item = next((entry for entry in ledger.get("checkpoints", []) if entry.get("id") == checkpoint_id), None)
    if item is None:
        raise LedgerError(f"checkpoint not found: {checkpoint_id}")
    return item


def _verified_checkpoint(ledger: dict[str, Any], workspace_root: str | Path, checkpoint_id: str) -> dict[str, Any]:
    checkpoint = _checkpoint(ledger, checkpoint_id)
    root = Path(workspace_root).resolve(strict=True)
    if str(root) != checkpoint.get("workspaceRoot") or root != Path(ledger["workspaceRoot"]).resolve(strict=True):
        raise LedgerError("checkpoint/workspace root does not match the ledger-bound root")
    if _fingerprint(checkpoint.get("snapshot")) != checkpoint.get("snapshotHash"):
        raise LedgerError("checkpoint hash evidence is forged or stale")
    return checkpoint


def reconcile_format_only_drift(ledger: dict[str, Any], workspace_root: str | Path, baseline_id: str, reconciliation_id: str, reviewer_evidence: str, affected_questions: list[str]) -> dict[str, Any]:
    """Create an explicitly reviewed format-only baseline without guessing semantic impact."""
    if not reviewer_evidence or not reconciliation_id:
        raise LedgerError("format-only reconciliation needs reviewer evidence and a new checkpoint id")
    baseline = _verified_checkpoint(ledger, workspace_root, baseline_id)
    if any(item.get("id") == reconciliation_id for item in ledger.get("checkpoints", [])):
        raise LedgerError("reconciliation checkpoint id already exists")
    known_questions = {item.get("id") for item in ledger.get("questions", []) if isinstance(item, dict)}
    if not set(affected_questions).issubset(known_questions):
        raise LedgerError("reconciliation names an unknown affected question")
    current = snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))
    changes = diff_snapshots(baseline["snapshot"], current)
    if not changes:
        raise LedgerError("format-only reconciliation needs observed drift")
    checkpoint = {"id": reconciliation_id, "createdAt": utc_now(), "workspaceRoot": str(Path(workspace_root).resolve()), "snapshot": current, "snapshotHash": _fingerprint(current), "approvedForWriteback": True, "reconciledFrom": baseline_id, "classification": "format-only", "reviewerEvidence": reviewer_evidence, "affectedQuestions": affected_questions, "observedChanges": changes}
    ledger.setdefault("checkpoints", []).append(checkpoint)
    _append_event(ledger, "format-only-drift-reconciled", baselineId=baseline_id, checkpointId=reconciliation_id)
    return ledger


def create_exception(ledger: dict[str, Any], workspace_root: str | Path, exception_id: str, authorization: str, scope: list[dict[str, Any]], checkpoint_id: str) -> dict[str, Any]:
    """Create the single auditable lease for a user-approved mid-review exception."""
    if ledger.get("phase") not in {"grilling", "awaiting-closure"}:
        raise LedgerError("mid-review exceptions are unavailable after review closure")
    if not exception_id or not authorization or not scope or any(item.get("id") == exception_id for item in ledger.get("exceptions", [])):
        raise LedgerError("exception needs unique id, authorization, and a non-empty scope")
    checkpoint = _verified_checkpoint(ledger, workspace_root, checkpoint_id)
    if diff_snapshots(checkpoint["snapshot"], snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))):
        raise LedgerError("mid-review exception needs a fresh protected-asset baseline")
    for item in scope:
        if not isinstance(item, dict) or not item.get("path"):
            raise LedgerError("exception scope must contain normalized path entries")
        scope_contains(workspace_root, scope, item["path"])
    ledger.setdefault("exceptions", []).append({"id": exception_id, "status": "active", "authorization": authorization, "scope": copy.deepcopy(scope), "preCheckpointId": checkpoint_id, "createdAt": utc_now()})
    _append_event(ledger, "exception-created", exceptionId=exception_id)
    return ledger


def _validate_writeback_plan(ledger: dict[str, Any], workspace_root: str | Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        raise LedgerError("writeback plan needs frozen postcondition items")
    if plan.get("decisionFingerprint") != _decision_fingerprint(ledger):
        raise LedgerError("writeback plan decision fingerprint is stale")
    seen_ids = set()
    seen_targets = set()
    normalized_items = []
    for item in items:
        valid_hash = isinstance(item.get("expectedSha256"), str) and len(item["expectedSha256"]) == 64 if isinstance(item, dict) else False
        if not isinstance(item, dict) or not item.get("id") or not item.get("path") or not valid_hash:
            raise LedgerError("each frozen plan item needs id, path, and expectedSha256")
        canonical_target = relative_workspace_path(workspace_root, item["path"])
        if item["id"] in seen_ids or canonical_target in seen_targets or not scope_contains(workspace_root, ledger["writebackPolicy"].get("approvedScopes", []), item["path"]):
            raise LedgerError("writeback plan has duplicate or out-of-scope target")
        normalized = copy.deepcopy(item)
        normalized["path"] = canonical_target  # Receipt coverage and protected snapshots share this relative key.
        normalized_items.append(normalized)
        seen_ids.add(item["id"]); seen_targets.add(canonical_target)
    return normalized_items


def prepare_writeback_plan(ledger: dict[str, Any], items: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Publish the canonical decision fingerprint for a downstream batch without formal writes."""
    issues = validate_ledger(ledger, intent="write")
    if any(issue["severity"] == "P0" for issue in issues) or ledger.get("phase") != "review-ended" or ledger.get("result") != "ready-for-writeback":
        raise LedgerError("writeback plan preparation requires a closed session eligible for default batch writeback")
    allowed = {str(item.get("path")) for item in ledger.get("processArtifacts", []) if isinstance(item, dict) and item.get("kind") == "writeback-plan"}
    target = str(Path(output_path).resolve(strict=False))
    if target not in allowed:
        raise LedgerError("plan output must be an explicit writeback-plan process artifact")
    plan = {"decisionFingerprint": _decision_fingerprint(ledger), "scopeFingerprint": _fingerprint(ledger["writebackPolicy"].get("approvedScopes", [])), "items": items.get("items", [])}
    plan["items"] = _validate_writeback_plan(ledger, ledger["workspaceRoot"], plan)  # Producer and consumer freeze identical canonical targets.
    _write_json(target, plan)
    _append_event(ledger, "writeback-plan-prepared", output=target, itemCount=len(plan["items"]))
    return plan


def start_writeback(ledger: dict[str, Any], workspace_root: str | Path, batch_id: str, checkpoint_id: str, plan: dict[str, Any]) -> dict[str, Any]:
    issues = validate_ledger(ledger, intent="write")
    fatal = [issue for issue in issues if issue["severity"] == "P0"]
    if fatal:
        raise LedgerError("writeback refused: " + "; ".join(item["rule"] for item in fatal))
    if ledger.get("phase") != "review-ended" or ledger.get("result") != "ready-for-writeback":
        raise LedgerError("writeback requires review-ended and ready-for-writeback")
    checkpoint = _verified_checkpoint(ledger, workspace_root, checkpoint_id)
    if not checkpoint.get("approvedForWriteback"):
        raise LedgerError("writeback must use the reviewed baseline or an explicitly reconciled format-only checkpoint")
    current = snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))
    drift = diff_snapshots(checkpoint["snapshot"], current)
    if drift:
        raise LedgerError("external drift requires explicit human classification; no semantic guess was made")
    if any(entry.get("batchId") == batch_id for entry in ledger.get("writebackReceipts", [])):
        raise LedgerError("batch id already exists")
    planned = _validate_writeback_plan(ledger, workspace_root, plan)
    ledger.setdefault("writebackReceipts", []).append({"batchId": batch_id, "decisionFingerprint": _decision_fingerprint(ledger), "scopeFingerprint": _fingerprint(ledger["writebackPolicy"].get("approvedScopes", [])), "checkpointId": checkpoint_id, "startedAt": utc_now(), "status": "in-progress", "plannedItems": planned, "items": []})
    ledger["phase"] = "writeback"
    _append_event(ledger, "writeback-started", batchId=batch_id, checkpointId=checkpoint_id)
    return ledger


def verify_writeback(ledger: dict[str, Any], workspace_root: str | Path, receipt: dict[str, Any]) -> dict[str, Any]:
    """Verify downstream postconditions; no formal content is merged by this runtime."""
    issues = validate_ledger(ledger, intent="write")
    fatal = [issue for issue in issues if issue["severity"] == "P0" and issue["rule"] != "concrete-risk-acceptance-required"]
    if fatal:
        raise LedgerError("receipt refused: " + "; ".join(item["rule"] for item in fatal))
    batch_id = receipt.get("batchId")
    entry = next((item for item in ledger.get("writebackReceipts", []) if item.get("batchId") == batch_id), None)
    if entry is None:
        raise LedgerError("receipt does not match a started batch")
    if receipt.get("decisionFingerprint") != entry.get("decisionFingerprint") or entry.get("decisionFingerprint") != _decision_fingerprint(ledger) or entry.get("scopeFingerprint") != _fingerprint(ledger["writebackPolicy"].get("approvedScopes", [])):
        raise LedgerError("receipt decision fingerprint does not match this batch")
    items = receipt.get("items")
    if not isinstance(items, list) or not items:
        raise LedgerError("receipt needs at least one declared postcondition item")
    planned = entry.get("plannedItems", [])
    if [(item.get("id"), item.get("path"), item.get("expectedSha256")) for item in items] != [(item.get("id"), item.get("path"), item.get("expectedSha256")) for item in planned]:
        raise LedgerError("receipt cannot alter the frozen writeback plan")
    for item in items:
        if not isinstance(item, dict) or not item.get("path") or not scope_contains(workspace_root, ledger["writebackPolicy"].get("approvedScopes", []), item["path"]):
            raise LedgerError("receipt has a target outside its approved writeback scope")
    checkpoint = _verified_checkpoint(ledger, workspace_root, entry["checkpointId"])
    after = snapshot_protected_assets(workspace_root, ledger.get("protectedAssets", []))
    observed_changes = diff_snapshots(checkpoint["snapshot"], after)
    declared_paths = {str(item["path"]).replace("\\", "/") for item in items}
    uncovered = [change for change in observed_changes if change["path"] not in declared_paths]
    postconditions = verify_expected_postconditions(workspace_root, items)
    entry["items"] = postconditions
    entry["verifiedAt"] = utc_now()
    entry["observedChanges"] = observed_changes
    if uncovered or any(item["status"] != "verified" for item in postconditions):
        entry["status"] = "partial-failure"
        entry["uncoveredChanges"] = uncovered
        ledger["phase"] = "repair-needed"
        ledger["result"] = "partial-failure"
        _append_event(ledger, "writeback-partial-failure", batchId=batch_id)
        return ledger
    previously_verified = entry.get("status") in {"verified", "verified-noop"}
    entry["status"] = "verified-noop" if not observed_changes else "verified"  # A no-op is successful evidence, never a claimed merge.
    entry["outcome"] = "no-op" if not observed_changes else "updated"
    entry["contentChanged"] = bool(observed_changes)
    entry["mergePerformed"] = bool(observed_changes)  # The runtime observes bytes; it never asserts an authoring mechanism.
    ledger["phase"] = "writeback-complete"
    ledger["result"] = "completed"
    if not previously_verified:
        _append_event(ledger, "writeback-verified", batchId=batch_id)
    return ledger


def _load_or_error(path: str) -> dict[str, Any]:
    try:
        return _load_json(path)
    except (OSError, json.JSONDecodeError, LedgerError) as exc:
        raise LedgerError(str(exc)) from exc


def _save_and_print(path: str, ledger: dict[str, Any], create: bool = False) -> int:
    if str(Path(path).resolve(strict=False)) != ledger.get("ledgerPath"):
        raise LedgerError("save target is not the canonical ledger path")
    _write_json(path, ledger, create=create)
    passed = ledger.get("result") not in {"partial-failure", "repair-needed", "blocked"}
    latest = ledger.get("writebackReceipts", [])[-1] if ledger.get("writebackReceipts") else {}
    print(json.dumps({"resultCode": "PASS" if passed else "FAIL", "phase": ledger.get("phase"), "result": ledger.get("result"), "writebackOutcome": latest.get("outcome"), "contentChanged": latest.get("contentChanged"), "mergePerformed": latest.get("mergePerformed")}, ensure_ascii=False))
    return 0 if passed else 1


def render_report(ledger: dict[str, Any], output_path: str | Path) -> None:
    """Project visible report fields from the canonical ledger; never accept report-owned decisions."""
    if ledger.get("recordMode") != "ledger" or ledger.get("phase") in {"grilling", "awaiting-closure", "paused"}:
        raise LedgerError("report projection requires a persisted post-closure ledger")
    allowed = {str(item.get("path")) for item in ledger.get("processArtifacts", []) if isinstance(item, dict) and item.get("kind") == "report"}
    target = str(Path(output_path).resolve(strict=False))
    if target not in allowed:
        raise LedgerError("report output must be an explicit canonical process artifact")
    decision_rows = "".join(f"<li>{html.escape(str(item.get('id')))}: {html.escape(str(item.get('decision', item.get('title', ''))))}</li>" for item in ledger.get("decisions", []))
    embedded = json.dumps(ledger, ensure_ascii=False).replace("</", "<\\/")  # Preserve JSON value while preventing script-tag termination.
    latest = ledger.get("writebackReceipts", [])[-1] if ledger.get("writebackReceipts") else {}
    writeback_visible = html.escape(str(latest.get("outcome", "not-started")))
    document = f"<!doctype html><html><head><meta charset=\"utf-8\"><title>Grill Session Report</title></head><body><h1>Grill Session Report</h1><dl><dt>Session</dt><dd>{html.escape(ledger['sessionId'])}</dd><dt>Phase</dt><dd>{html.escape(ledger['phase'])}</dd><dt>Result</dt><dd>{html.escape(ledger['result'])}</dd><dt>Writeback outcome</dt><dd>{writeback_visible}</dd></dl><h2>Decisions</h2><ul>{decision_rows}</ul><script type=\"application/json\" id=\"grill-session\">{embedded}</script></body></html>"
    destination = Path(output_path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(document); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--session", required=True)
    init.add_argument("--session-id", required=True)
    init.add_argument("--scenario", required=True)
    init.add_argument("--record-mode", default="ledger")
    init.add_argument("--workspace-root")
    validate = sub.add_parser("validate")
    validate.add_argument("--session", required=True)
    validate.add_argument("--intent", choices=("read", "close", "write"), default="read")
    answer = sub.add_parser("record-answer")
    answer.add_argument("--session", required=True); answer.add_argument("--question", required=True); answer.add_argument("--answer", required=True); answer.add_argument("--status", required=True); answer.add_argument("--decision")
    propose = sub.add_parser("propose-question")
    propose.add_argument("--session", required=True); propose.add_argument("--question-json", required=True)
    close = sub.add_parser("close")
    close.add_argument("--session", required=True); close.add_argument("--closure", required=True); close.add_argument("--mode")
    pause = sub.add_parser("pause")
    pause.add_argument("--session", required=True); pause.add_argument("--next-question")
    resume = sub.add_parser("resume"); resume.add_argument("--session", required=True)
    reopen = sub.add_parser("reopen")
    reopen.add_argument("--session", required=True); reopen.add_argument("--question", required=True); reopen.add_argument("--reason", required=True); reopen.add_argument("--evidence", required=True)
    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--session", required=True); checkpoint.add_argument("--workspace-root", required=True); checkpoint.add_argument("--checkpoint-id", required=True)
    reconcile = sub.add_parser("reconcile-format-only")
    reconcile.add_argument("--session", required=True); reconcile.add_argument("--workspace-root", required=True); reconcile.add_argument("--baseline-id", required=True); reconcile.add_argument("--checkpoint-id", required=True); reconcile.add_argument("--reviewer-evidence", required=True); reconcile.add_argument("--affected-questions", default="[]")
    create_exception_parser = sub.add_parser("create-exception")
    create_exception_parser.add_argument("--session", required=True); create_exception_parser.add_argument("--workspace-root", required=True); create_exception_parser.add_argument("--exception-id", required=True); create_exception_parser.add_argument("--authorization", required=True); create_exception_parser.add_argument("--scope", required=True); create_exception_parser.add_argument("--checkpoint-id", required=True)
    finish_exception_parser = sub.add_parser("finish-exception")
    finish_exception_parser.add_argument("--session", required=True); finish_exception_parser.add_argument("--workspace-root", required=True); finish_exception_parser.add_argument("--exception-id", required=True); finish_exception_parser.add_argument("--postconditions", required=True); finish_exception_parser.add_argument("--checkpoint-id", required=True)
    exception = sub.add_parser("consume-exception")
    exception.add_argument("--session", required=True); exception.add_argument("--workspace-root", required=True); exception.add_argument("--exception-id", required=True); exception.add_argument("--target", required=True)
    begin = sub.add_parser("begin-writeback")
    begin.add_argument("--session", required=True); begin.add_argument("--workspace-root", required=True); begin.add_argument("--batch-id", required=True); begin.add_argument("--checkpoint-id", required=True); begin.add_argument("--plan", required=True)
    prepare = sub.add_parser("prepare-writeback-plan")
    prepare.add_argument("--session", required=True); prepare.add_argument("--items", required=True); prepare.add_argument("--output", required=True)
    verify = sub.add_parser("verify-writeback")
    verify.add_argument("--session", required=True); verify.add_argument("--workspace-root", required=True); verify.add_argument("--receipt", required=True)
    report = sub.add_parser("render-report")
    report.add_argument("--session", required=True); report.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            ledger = new_ledger(args.session_id, args.scenario, args.record_mode, args.session, args.workspace_root)
            if args.record_mode == "conversation-only":
                print(json.dumps({"resultCode": "PASS", "recordMode": "conversation-only", "persisted": False, "ledger": ledger}, ensure_ascii=False))
                return 0
            return _save_and_print(args.session, ledger, create=True)
        ledger = _load_or_error(args.session)
        if args.command == "validate":
            issues = validate_ledger(ledger, args.intent)
            print(json.dumps({"resultCode": "PASS" if not any(item["severity"] == "P0" for item in issues) else "FAIL", "issues": issues}, ensure_ascii=False, indent=2))
            return 1 if any(item["severity"] == "P0" for item in issues) else 0
        ensure_mutable_ledger(ledger, args.session, allow_pending_exception=args.command == "finish-exception")  # Ledger persistence is separate from formal-write eligibility.
        if args.command == "record-answer":
            return _save_and_print(args.session, record_answer(ledger, args.question, args.answer, args.status, args.decision))
        if args.command == "propose-question":
            return _save_and_print(args.session, propose_question(ledger, _load_json(args.question_json)))
        if args.command == "close":
            return _save_and_print(args.session, close_session(ledger, _load_json(args.closure), args.mode))
        if args.command == "pause":
            return _save_and_print(args.session, pause_session(ledger, args.next_question))
        if args.command == "resume":
            return _save_and_print(args.session, resume_session(ledger))
        if args.command == "reopen":
            return _save_and_print(args.session, reopen_question(ledger, args.question, args.reason, args.evidence))
        if args.command == "checkpoint":
            return _save_and_print(args.session, create_checkpoint(ledger, args.workspace_root, args.checkpoint_id))
        if args.command == "reconcile-format-only":
            return _save_and_print(args.session, reconcile_format_only_drift(ledger, args.workspace_root, args.baseline_id, args.checkpoint_id, args.reviewer_evidence, json.loads(args.affected_questions)))
        if args.command == "create-exception":
            return _save_and_print(args.session, create_exception(ledger, args.workspace_root, args.exception_id, args.authorization, _load_json(args.scope).get("scope", []), args.checkpoint_id))
        if args.command == "finish-exception":
            return _save_and_print(args.session, finish_exception(ledger, args.workspace_root, args.exception_id, _load_json(args.postconditions).get("items", []), args.checkpoint_id))
        if args.command == "consume-exception":
            return _save_and_print(args.session, consume_exception(ledger, args.workspace_root, args.exception_id, args.target))
        if args.command == "begin-writeback":
            return _save_and_print(args.session, start_writeback(ledger, args.workspace_root, args.batch_id, args.checkpoint_id, _load_json(args.plan)))
        if args.command == "prepare-writeback-plan":
            prepare_writeback_plan(ledger, _load_json(args.items), args.output)
            _write_json(args.session, ledger)
            print(json.dumps({"resultCode": "PASS", "plan": args.output}, ensure_ascii=False))
            return 0
        if args.command == "verify-writeback":
            return _save_and_print(args.session, verify_writeback(ledger, args.workspace_root, _load_json(args.receipt)))
        if args.command == "render-report":
            render_report(ledger, args.output)
            print(json.dumps({"resultCode": "PASS", "report": args.output}, ensure_ascii=False))
            return 0
    except (LedgerError, BoundaryError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"resultCode": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
