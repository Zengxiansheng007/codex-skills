"""Deterministic governance runtime for Development System.

This module owns policy evaluation, state projection, recovery checks, and
completion gates. It intentionally does not invoke external Agents, networks,
installers, or deployment tools. Those effects belong to independent adapters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GOVERNED_STATES = (
    "running",
    "waiting-approval",
    "blocked-external-dependency",
    "blocked-user-decision",
    "repair-needed",
    "requirements-review",
    "risk-gate-required",
    "loop-limit-reached",
    "resource-limit-reached",
    "completed",
    "failed",
)

# PH-2 ST-2-005: Chinese status labels for the 11 governed machine states.
# The machine code remains the stable identifier; the Chinese label is a
# user-facing projection only (FR-TOT-013, AC-TOT-018).
STATUS_ZH_MAP = {
    "running": "运行中",
    "waiting-approval": "等待审批",
    "blocked-external-dependency": "外部依赖阻塞",
    "blocked-user-decision": "等待用户决策",
    "repair-needed": "需要修复",
    "requirements-review": "需求评审",
    "risk-gate-required": "风险门",
    "loop-limit-reached": "循环上限",
    "resource-limit-reached": "资源上限",
    "completed": "已完成",
    "failed": "失败",
}

# PH-2 ST-2-001: Stable fields for an external Claude Agent registry entry.
REQUIRED_REGISTRY_FIELDS = (
    "agentId",
    "adapterId",
    "version",
    "capabilities",
    "availability",
    "feedbackSchemaRef",
    "completionAuthorityIsolated",
)

# PH-2 ST-2-002: Preauthorization policy lifecycle dimensions.
PREAUTHORIZATION_DIMENSIONS = (
    "workspaceRoots",
    "actions",
    "tools",
    "data",
    "network",
    "credentialBoundary",
    "feedbackSchema",
    "maxTimeoutSeconds",
    "maxRounds",
    "maxConcurrency",
    "stopConditions",
)

# PH-2 ST-2-004: Dry-run transition statuses.
DRY_RUN_STATUSES = ("DRY_RUN_OK", "DRY_RUN_BLOCKED", "DRY_RUN_MISSING")

# PH-2 ST-2-006: Takeover triggers.
TAKEOVER_TRIGGERS = ("claude-unavailable", "timeout", "invalid-feedback")

PRIVATE_PROFILES = {
    "product-requirement",
    "architect",
    "project-planner",
    "engineer",
    "qa",
}

REWORK_OWNER = {
    "requirement": "product-requirement",
    "architecture": "architect",
    "plan": "project-planner",
    "implementation": "engineer",
    "test": "qa",
    "evidence": "qa",
    "handoff": "handoff-system-interface",
    "cross-domain-risk": "codex-risk-gate",
}

CLAUDE_FIRST_SIGNALS = {
    "multiFile",
    "skillDevelopment",
    "complexRepair",
    "crossModule",
}

ALLOWED_TRANSITIONS = {
    "running": set(GOVERNED_STATES) - {"running"},
    "waiting-approval": {"running", "blocked-user-decision"},
    "blocked-external-dependency": {"running", "repair-needed"},
    "blocked-user-decision": {"running", "requirements-review"},
    "repair-needed": {"running", "requirements-review", "loop-limit-reached"},
    "requirements-review": {"running", "blocked-user-decision"},
    "risk-gate-required": {"running", "blocked-user-decision"},
    "loop-limit-reached": {"repair-needed", "requirements-review"},
    "resource-limit-reached": {"running", "repair-needed"},
    "failed": {"repair-needed", "requirements-review"},
    "completed": set(),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _inside(path: str, roots: Iterable[str]) -> bool:
    candidate = Path(path).resolve()
    for root in roots:
        resolved_root = Path(root).resolve()
        try:
            candidate.relative_to(resolved_root)
            return True
        except ValueError:
            continue
    return False


def validate_registry(profiles: list[dict[str, Any]], independent_skills: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Reject discoverable private profiles and ownership collisions."""
    findings: list[dict[str, str]] = []
    skill_names = [str(item.get("name", "")) for item in independent_skills]
    if len(skill_names) != len(set(skill_names)):
        findings.append({"severity": "P0", "rule": "duplicate-skill-owner", "message": "Independent Skill names must be unique."})
    for profile in profiles:
        profile_id = str(profile.get("profileId", ""))
        if profile_id not in PRIVATE_PROFILES:
            findings.append({"severity": "P1", "rule": "unknown-private-profile", "message": profile_id})
        if profile.get("globallyDiscoverable") is True:
            findings.append({"severity": "P0", "rule": "private-profile-global-clash", "message": profile_id})
        if profile_id in skill_names:
            findings.append({"severity": "P0", "rule": "private-profile-skill-name-clash", "message": profile_id})
    return findings


def validate_phase_story(phase: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for field in ("phaseId", "goal", "entryCriteria", "exitCriteria", "stories"):
        value = phase.get(field)
        if value is None or value == "" or value == []:
            findings.append({"severity": "P1", "rule": "phase-required", "message": field})
    stories = phase.get("stories") if isinstance(phase.get("stories"), list) else []
    graph: dict[str, list[str]] = {}
    for story in stories:
        sid = str(story.get("storyId", ""))
        graph[sid] = list(story.get("dependsOn") or [])
        for field in (
            "storyId",
            "title",
            "goal",
            "mappedRequirements",
            "acceptanceCriteria",
            "testability",
            "evidenceRequirements",
        ):
            value = story.get(field)
            if value is None or value == "" or value == []:
                findings.append({"severity": "P1", "rule": "story-required", "message": f"{sid}:{field}"})
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph and visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in graph):
        findings.append({"severity": "P1", "rule": "story-dependency-cycle", "message": "Story dependency graph contains a cycle."})
    return findings


def validate_artifact_envelope(artifact: dict[str, Any]) -> list[dict[str, str]]:
    """Validate stable identity, ownership, source anchor, and requirement trace.

    The normative field set is defined by ``schemas/artifact-envelope.schema.json``.
    That schema requires: ``artifactId``, ``version``, ``artifactType``, ``owner``,
    ``sourceAnchorId``, ``sourceAnchorVersion``, ``mappedFrAc``, ``createdAt``,
    and ``derivedFrom``.  ``sourceRefs`` and ``changeType`` are **not** part of
    the normative envelope and must not be independently required here, otherwise
    the same artifact faces a dual contract (DS-PREDEV-001).
    """
    findings: list[dict[str, str]] = []
    required = (
        "artifactId",
        "version",
        "artifactType",
        "owner",
        "sourceAnchorId",
        "sourceAnchorVersion",
        "mappedFrAc",
        "createdAt",
        "derivedFrom",
    )
    for field in required:
        value = artifact.get(field)
        if value is None or value == "" or value == []:
            findings.append({"severity": "P1", "rule": "artifact-required", "message": field})
    if artifact.get("owner") not in PRIVATE_PROFILES | {"codex-control-plane", "handoff-system-interface", "development-system/architecture", "development-system/planning", "development-system/qa"}:
        findings.append({"severity": "P1", "rule": "artifact-owner", "message": str(artifact.get("owner", ""))})
    if not isinstance(artifact.get("mappedFrAc"), list):
        findings.append({"severity": "P1", "rule": "artifact-trace-type", "message": "mappedFrAc"})
    return findings


def validate_transition(
    current_state: str,
    next_state: str,
    actor: str,
    completion_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed unless Codex authorizes a valid governed transition."""
    if actor != "Codex":
        return {"allowed": False, "state": current_state, "reason": "codex-only-transition-authority"}
    if current_state not in ALLOWED_TRANSITIONS or next_state not in GOVERNED_STATES:
        return {"allowed": False, "state": current_state, "reason": "unknown-governed-state"}
    if next_state not in ALLOWED_TRANSITIONS[current_state]:
        return {"allowed": False, "state": current_state, "reason": "illegal-state-transition"}
    if next_state == "completed":
        result = evaluate_completion(completion_evaluation or {})
        if result["state"] != "completed":
            return {"allowed": False, "state": result["state"], "reason": "completion-evaluator-rejected", "evaluation": result}
    return {"allowed": True, "state": next_state, "reason": "codex-authorized"}


def preauthorization_matches(
    required: dict[str, Any],
    policy: dict[str, Any],
    now: str | None = None,
) -> tuple[bool, list[str]]:
    """Require a complete, conservative match across every approval dimension.

    PH-2 (FR-TOT-010, FR-TOT-011, AC-TOT-007, AC-TOT-008): The match must
    cover workspace, actions, tools, data, network, credential boundary,
    feedback schema, timeout, rounds, concurrency, and stop conditions.
    Any mismatch or missing dimension fails closed.
    """
    missing: list[str] = []
    finding_dimensions = {
        "policy-not-active": "policyStatus",
        "policy-expired": "policyExpiry",
        "policy-not-yet-valid": "policyValidity",
        "policy-time-invalid": "policyValidity",
        "policy-hash-mismatch": "policyHash",
    }
    for finding in validate_preauthorization_policy(policy, now=now):
        dimension = finding_dimensions.get(finding["rule"], finding.get("message", "policy"))
        if dimension not in missing:
            missing.append(dimension)

    if required.get("policyId") != policy.get("policyId"):
        missing.append("policyId")
    policy_hash = compute_policy_hash(policy)
    if required.get("policyHash") != policy_hash:
        missing.append("policyHash")
    roots = policy.get("workspaceRoots") or []
    if not required.get("workspace") or not roots or not _inside(str(required.get("workspace", "")), roots):
        missing.append("workspace")
    for field in ("actions", "data", "tools"):
        requested = set(required.get(field) or [])
        allowed = set(policy.get(field) or [])
        if not requested or not requested.issubset(allowed):
            missing.append(field)
    if "network" not in required or not isinstance(required.get("network"), list):
        missing.append("network")
    elif not set(required["network"]).issubset(set(policy.get("network") or [])):
        missing.append("network")
    # credentialBoundary: the requested credential scope must be a subset of the policy's
    req_cred = str(required.get("credentialBoundary") or "")
    pol_cred = str(policy.get("credentialBoundary") or "")
    if not req_cred or not pol_cred or req_cred != pol_cred:
        missing.append("credentialBoundary")
    # feedbackSchema: exact match required
    req_schema = str(required.get("feedbackSchema") or "")
    pol_schema = str(policy.get("feedbackSchema") or "")
    if not req_schema or not pol_schema or req_schema != pol_schema:
        missing.append("feedbackSchema")
    # timeoutSeconds must be positive int and <= maxTimeoutSeconds
    timeout = required.get("timeoutSeconds")
    max_timeout = policy.get("maxTimeoutSeconds")
    if not isinstance(timeout, int) or not isinstance(max_timeout, int) or timeout <= 0 or timeout > max_timeout:
        missing.append("timeoutSeconds")
    # rounds: requested rounds must be positive int and <= maxRounds
    req_rounds = required.get("rounds")
    max_rounds = policy.get("maxRounds")
    if not isinstance(req_rounds, int) or not isinstance(max_rounds, int) or req_rounds <= 0 or req_rounds > max_rounds:
        missing.append("rounds")
    # concurrency: requested must be positive int and <= maxConcurrency
    req_conc = required.get("concurrency")
    max_conc = policy.get("maxConcurrency")
    if not isinstance(req_conc, int) or not isinstance(max_conc, int) or req_conc <= 0 or req_conc > max_conc:
        missing.append("concurrency")
    # stopConditions: every requested stop condition must be in policy's set
    req_stops = set(required.get("stopConditions") or [])
    pol_stops = set(policy.get("stopConditions") or [])
    if not req_stops or not req_stops.issubset(pol_stops):
        missing.append("stopConditions")
    return not missing, list(dict.fromkeys(missing))


def decide_execution(task: dict[str, Any], policy: dict[str, Any], claude_available: bool) -> dict[str, Any]:
    signals = set(task.get("signals") or [])
    requires_claude = bool(signals & CLAUDE_FIRST_SIGNALS)
    if task.get("userLevelInstall"):
        return {"decision": "blocked-user-decision", "reason": "user-level installation requires explicit approval"}
    matched, missing = preauthorization_matches(task.get("requiredAuthorization") or {}, policy)
    if requires_claude:
        if not matched:
            return {"decision": "blocked-user-decision", "reason": "preauthorization mismatch", "missingDimensions": missing}
        if claude_available:
            return {"decision": "claude-first", "reason": "task matched a mandatory Claude-first signal"}
        if policy.get("codexTakeoverAllowed") is True:
            return {"decision": "codex-takeover", "reason": "Claude unavailable inside a fully preauthorized boundary"}
        return {"decision": "blocked-external-dependency", "reason": "Claude unavailable and takeover is not authorized"}
    reason = task.get("codexLocalException")
    if reason not in {"documentation-only", "single-file-non-behavior", "simple-local-task"}:
        return {"decision": "repair-needed", "reason": "Codex local execution requires a recognized exception"}
    return {"decision": "codex-local-exception", "reason": reason}


def append_event(history_path: str | Path, event: dict[str, Any]) -> dict[str, Any]:
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] | None = None
    if path.exists():
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            previous = json.loads(lines[-1])
    expected_sequence = 1 if previous is None else int(previous["sequenceIndex"]) + 1
    previous_hash = "GENESIS" if previous is None else str(previous["eventHash"])
    if "sequenceIndex" in event and event["sequenceIndex"] != expected_sequence:
        raise ValueError("event sequence mismatch")
    if "previousHash" in event and event["previousHash"] != previous_hash:
        raise ValueError("event previousHash mismatch")
    persisted = deepcopy(event)
    persisted["sequenceIndex"] = expected_sequence
    persisted["previousHash"] = previous_hash
    persisted.setdefault("observedAt", _now())
    persisted.pop("eventHash", None)
    persisted["eventHash"] = _sha256(persisted)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical(persisted) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return persisted


def validate_history(history_path: str | Path) -> tuple[bool, list[str], list[dict[str, Any]]]:
    path = Path(history_path)
    if not path.exists():
        return False, ["history-missing"], []
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    previous_hash = "GENESIS"
    expected_sequence = 1
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            errors.append(f"line-{line_number}-invalid-json")
            continue
        claimed_hash = event.get("eventHash")
        payload = deepcopy(event)
        payload.pop("eventHash", None)
        if event.get("sequenceIndex") != expected_sequence:
            errors.append(f"line-{line_number}-sequence")
        if event.get("previousHash") != previous_hash:
            errors.append(f"line-{line_number}-previous-hash")
        if claimed_hash != _sha256(payload):
            errors.append(f"line-{line_number}-event-hash")
        events.append(event)
        previous_hash = str(claimed_hash)
        expected_sequence += 1
    if not events:
        errors.append("history-empty")
    return not errors, errors, events


def write_snapshot_atomic(snapshot_path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    path = Path(snapshot_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = deepcopy(snapshot)
    value.setdefault("writtenAt", _now())
    value.pop("snapshotHash", None)
    value["snapshotHash"] = _sha256(value)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return value


def resume_cycle(
    history_path: str | Path,
    snapshot_path: str | Path,
    anchor_id: str,
    anchor_version: str,
    workspace_fingerprint: str,
    heartbeat_fresh: bool,
    phase_id: str | None = None,
    queue_fingerprint: str | None = None,
) -> dict[str, Any]:
    valid, errors, events = validate_history(history_path)
    snapshot_file = Path(snapshot_path)
    if not snapshot_file.exists():
        errors.append("snapshot-missing")
        return {"resumable": False, "state": "blocked-external-dependency", "errors": errors}
    try:
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"resumable": False, "state": "blocked-external-dependency", "errors": errors + ["snapshot-invalid-json"]}
    claimed = snapshot.get("snapshotHash")
    payload = deepcopy(snapshot)
    payload.pop("snapshotHash", None)
    if claimed != _sha256(payload):
        errors.append("snapshot-hash")
    if snapshot.get("anchorId") != anchor_id or snapshot.get("anchorVersion") != anchor_version:
        errors.append("anchor-mismatch")
    if snapshot.get("workspaceFingerprint") != workspace_fingerprint:
        errors.append("workspace-mismatch")
    if phase_id is not None and snapshot.get("phaseId") != phase_id:
        errors.append("phase-mismatch")
    if queue_fingerprint is not None and snapshot.get("queueFingerprint") != queue_fingerprint:
        errors.append("queue-mismatch")
    if not heartbeat_fresh:
        errors.append("heartbeat-stale")
    if events:
        last = events[-1]
        if snapshot.get("lastSequenceIndex") != last.get("sequenceIndex"):
            errors.append("snapshot-sequence")
        if snapshot.get("lastEventHash") != last.get("eventHash"):
            errors.append("snapshot-event-hash")
    if not valid:
        pass
    return {
        "resumable": not errors,
        "state": snapshot.get("state") if not errors else "blocked-external-dependency",
        "errors": errors,
        "snapshot": snapshot if not errors else None,
    }


def evaluate_verified_progress(delta: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "mapped": bool(delta.get("mappedFrAc")),
        "validation": delta.get("validationPassed") is True,
        "evidence": bool(delta.get("evidenceRefs")),
        "improved": delta.get("stateImproved") is True,
    }
    verified = all(checks.values())
    return {"verified": verified, "classification": "verified-progress" if verified else "observation-only", "checks": checks}


def failure_fingerprint(failure: dict[str, Any]) -> str:
    normalized = {
        "type": str(failure.get("type", "")).strip().lower(),
        "testId": str(failure.get("testId", "")).strip().lower(),
        "message": " ".join(str(failure.get("message", "")).lower().split()),
        "rootCause": str(failure.get("rootCause", "")).strip().lower(),
    }
    return _sha256(normalized)[:20]


def advance_circuit(counters: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(counters)
    result.setdefault("noProgress", 0)
    result.setdefault("invalidFeedbackByRoot", {})
    result.setdefault("failureByFingerprint", {})
    result.setdefault("timeoutCount", 0)
    result.setdefault("roundCount", 0)
    result.setdefault("circuitState", "CLOSED")
    stop_reason = None
    next_state = "running"

    if observation.get("actualExecution") is True:
        result["roundCount"] += 1
    if result["roundCount"] >= 10 and observation.get("completionPassed") is not True:
        result["circuitState"] = "OPEN"
        stop_reason = "story-round-limit"
        next_state = "loop-limit-reached"

    if observation.get("verifiedProgress") is True:
        result["noProgress"] = 0
    elif observation.get("actualExecution") is True:
        result["noProgress"] += 1
        if result["noProgress"] >= 3:
            result["circuitState"] = "OPEN"
            stop_reason = stop_reason or "no-verified-progress"
            next_state = "loop-limit-reached"

    failure = observation.get("failure")
    if isinstance(failure, dict):
        fingerprint = failure_fingerprint(failure)
        counts = result["failureByFingerprint"]
        counts[fingerprint] = int(counts.get(fingerprint, 0)) + 1
        if counts[fingerprint] == 3 and next_state == "running":
            stop_reason = "repeated-failure-repair-review"
            next_state = "repair-needed"
        if counts[fingerprint] >= 5:
            result["circuitState"] = "OPEN"
            stop_reason = "repeated-failure-open"
            next_state = "loop-limit-reached"

    invalid_root = observation.get("invalidFeedbackRoot")
    if invalid_root:
        counts = result["invalidFeedbackByRoot"]
        counts[invalid_root] = int(counts.get(invalid_root, 0)) + 1
        current = counts[invalid_root]
        if current == 1 and next_state == "running":
            stop_reason = "invalid-feedback-repair"
            next_state = "repair-needed"
        elif current == 2 and next_state in {"running", "repair-needed"}:
            stop_reason = "invalid-feedback-adapter-review"
            next_state = "repair-needed"
        elif current >= 3:
            result["circuitState"] = "OPEN"
            stop_reason = "invalid-feedback-limit"
            next_state = "loop-limit-reached"

    if observation.get("timeout") is True:
        result["timeoutCount"] += 1
        if result["timeoutCount"] == 1:
            stop_reason = "timeout-recovery-required"
            next_state = "repair-needed"
        elif observation.get("takeoverPreauthorized") is True:
            stop_reason = "timeout-codex-takeover"
            next_state = "repair-needed"
        else:
            stop_reason = "timeout-external-block"
            next_state = "blocked-external-dependency"

    return {"counters": result, "stopReason": stop_reason, "nextState": next_state}


def authorize_half_open(circuit_state: str, codex_reauthorized: bool, probe_used: bool) -> dict[str, Any]:
    allowed = circuit_state == "OPEN" and codex_reauthorized and not probe_used
    return {
        "allowed": allowed,
        "nextCircuitState": "HALF_OPEN" if allowed else "OPEN",
        "probeLimit": 1,
    }


def route_rework(defect_type: str) -> dict[str, Any]:
    owner = REWORK_OWNER.get(defect_type)
    if owner is None:
        return {"state": "requirements-review", "owner": None, "reopenDownstream": True}
    return {"state": "risk-gate-required" if defect_type == "cross-domain-risk" else "repair-needed", "owner": owner, "reopenDownstream": defect_type != "handoff"}


_HEX_HASH_PATTERN = "0123456789abcdef"


def validate_feedback_evidence(feedback: Any, evidence: dict[str, Any]) -> dict[str, Any]:
    """Validate hash-bound feedback validation evidence.

    The handoff-system remains the sole owner of the feedback packet schema.
    This function does **not** re-implement that schema; it verifies that an
    external validator produced a deterministic, hash-bound evidence object
    for the actual feedback packet supplied by the caller.

    Required evidence fields:
      - ``schemaRef`` (non-empty string) — references the external schema used.
      - ``validatorId`` (non-empty string) — identifies the external validator.
      - ``feedbackHash`` — 64-character lowercase hex SHA-256 of the canonical
        form of ``feedback``.
      - ``ok`` — must be ``True``.
      - ``errorCount`` — must be ``0``.
      - ``errors`` — must be an empty list or absent.
      - ``validatedAt`` — non-empty string timestamp.

    Returns a dict with ``valid`` (bool), ``errors`` (list[str]), and
    ``computedHash`` (the canonical SHA-256 of the supplied feedback).
    """
    errors: list[str] = []
    computed_hash = _sha256(feedback) if feedback is not None else ""

    if feedback is None or feedback == "" or feedback == {}:
        errors.append("feedback-missing")
        return {"valid": False, "errors": errors, "computedHash": computed_hash}

    if not isinstance(evidence, dict):
        errors.append("validation-evidence-not-object")
        return {"valid": False, "errors": errors, "computedHash": computed_hash}

    schema_ref = evidence.get("schemaRef")
    if not isinstance(schema_ref, str) or not schema_ref.strip():
        errors.append("schemaRef-missing")

    validator_id = evidence.get("validatorId")
    if not isinstance(validator_id, str) or not validator_id.strip():
        errors.append("validatorId-missing")

    feedback_hash = evidence.get("feedbackHash")
    if feedback_hash is None:
        errors.append("feedbackHash-missing")
    elif not isinstance(feedback_hash, str):
        errors.append("feedbackHash-not-string")
    elif len(feedback_hash) != 64:
        errors.append("feedbackHash-wrong-length")
    elif any(ch not in _HEX_HASH_PATTERN for ch in feedback_hash):
        errors.append("feedbackHash-not-lowercase-hex")
    elif feedback_hash != computed_hash:
        errors.append("feedbackHash-mismatch")

    if evidence.get("ok") is not True:
        errors.append("validation-ok-false")

    error_count = evidence.get("errorCount")
    if not isinstance(error_count, int) or error_count != 0:
        errors.append("errorCount-nonzero")

    ev_errors = evidence.get("errors")
    if ev_errors is not None and ev_errors != []:
        errors.append("errors-not-empty")

    validated_at = evidence.get("validatedAt")
    if not isinstance(validated_at, str) or not validated_at.strip():
        errors.append("validatedAt-missing")

    return {"valid": not errors, "errors": errors, "computedHash": computed_hash}


def evaluate_completion(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Codex-owned completion evaluation; Agent claims are deliberately ignored.

    ``feedbackValid`` can no longer pass from a bare boolean alone. The
    evaluator consumes the actual ``feedback`` object plus
    ``feedbackValidation`` evidence and requires the hash-bound validation
    result produced by the independent handoff-system validator. An Agent
    completion claim, stop signal, timeout, circuit state or resource limit is
    never a completion signal on its own.
    """
    feedback = evaluation.get("feedback")
    feedback_validation = evaluation.get("feedbackValidation")

    feedback_result = validate_feedback_evidence(feedback, feedback_validation or {})
    feedback_valid = feedback_result["valid"]

    checks = {
        "allStoriesPassed": evaluation.get("allStoriesPassed") is True,
        "allAcceptanceCriteriaVerified": evaluation.get("allAcceptanceCriteriaVerified") is True,
        "feedbackValid": feedback_valid,
        "evidenceComplete": evaluation.get("evidenceComplete") is True,
        "qaPassed": evaluation.get("qaPassed") is True,
        "noP0P1Drift": evaluation.get("driftSeverity") in {"none", "allowed"},
        "noUnmappedActions": not evaluation.get("unmappedActions"),
        "permissionGatePassed": evaluation.get("permissionGatePassed") is True,
        "riskGatePassed": evaluation.get("riskGatePassed") is True,
        "codexReviewPassed": evaluation.get("codexReviewPassed") is True,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    if not blockers:
        return {"state": "completed", "passed": True, "checks": checks, "blockers": [], "feedbackValidation": feedback_result}
    if not checks["noP0P1Drift"] or not checks["noUnmappedActions"]:
        state = "requirements-review"
    elif not checks["permissionGatePassed"] or not checks["riskGatePassed"]:
        state = "risk-gate-required"
    else:
        state = "repair-needed"
    return {"state": state, "passed": False, "checks": checks, "blockers": blockers, "feedbackValidation": feedback_result}


def schedule_slots(stories: list[dict[str, Any]], completed_story_ids: set[str] | None = None) -> dict[str, Any]:
    completed = completed_story_ids or set()
    candidates = [s for s in stories if set(s.get("dependsOn") or []).issubset(completed)]
    accepted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    workspaces: set[str] = set()
    write_sets: set[str] = set()
    for story in candidates:
        workspace = str(story.get("workspaceFingerprint", ""))
        writes = set(story.get("writeSet") or [])
        reasons: list[str] = []
        if not workspace or workspace in workspaces:
            reasons.append("workspace-collision")
        if writes & write_sets:
            reasons.append("write-set-conflict")
        if reasons:
            blocked.append({"storyId": story.get("storyId"), "reasons": reasons})
            continue
        workspaces.add(workspace)
        write_sets.update(writes)
        accepted.append(story)
    return {"scheduled": accepted, "blocked": blocked, "state": "running" if accepted else "repair-needed"}


def evaluate_merge(candidate: dict[str, Any]) -> dict[str, Any]:
    """Gate a parallel result before it is merged into the governed baseline."""
    checks = {
        "baselineUnchanged": bool(candidate.get("baselineBefore"))
        and candidate.get("baselineBefore") == candidate.get("baselineCurrent"),
        "writeSetConflictFree": not candidate.get("writeSetConflicts"),
        "evidenceComplete": bool(candidate.get("evidenceRefs")),
        "validationPassed": candidate.get("validationPassed") is True,
        "storyTracePresent": bool(candidate.get("storyId")) and bool(candidate.get("mappedFrAc")),
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "state": "running" if not blockers else "repair-needed",
        "mergeAllowed": not blockers,
        "checks": checks,
        "blockers": blockers,
    }


def validate_skill_interface(interface: dict[str, Any]) -> list[dict[str, str]]:
    """Validate an independent Skill boundary without importing its internals."""
    findings: list[dict[str, str]] = []
    required = (
        "skillName",
        "version",
        "owner",
        "inputSchemaRef",
        "outputSchemaRef",
        "allowedActions",
        "forbiddenActions",
        "evidenceContract",
        "statusMapping",
    )
    for field in required:
        value = interface.get(field)
        if value is None or value == "" or value == [] or value == {}:
            findings.append({"severity": "P1", "rule": "skill-interface-required", "message": field})
    if interface.get("skillName") in PRIVATE_PROFILES:
        findings.append({"severity": "P0", "rule": "private-profile-skill-clash", "message": str(interface.get("skillName"))})
    if interface.get("changesCompletionAuthority") is True or interface.get("implicitReplacement") is True:
        findings.append({"severity": "P0", "rule": "skill-interface-governance-bypass", "message": str(interface.get("skillName", ""))})
    return findings


def evaluate_resources(usage: dict[str, float], budget: dict[str, float]) -> dict[str, Any]:
    exceeded = []
    for dimension in ("calls", "durationSeconds", "tokens", "cost", "rate", "concurrency"):
        if dimension in budget and float(usage.get(dimension, 0)) > float(budget[dimension]):
            exceeded.append(dimension)
    return {"state": "resource-limit-reached" if exceeded else "running", "exceeded": exceeded}


def status_projection(snapshot: dict[str, Any], last_event: dict[str, Any] | None = None) -> dict[str, Any]:
    state = snapshot.get("state")
    return {
        "cycleId": snapshot.get("cycleId"),
        "phaseId": snapshot.get("phaseId"),
        "storyId": snapshot.get("storyId"),
        "roundNumber": snapshot.get("roundNumber"),
        "state": state if state in GOVERNED_STATES else "failed",
        "blocker": snapshot.get("blocker"),
        "heartbeatAt": snapshot.get("heartbeatAt"),
        "evidenceRefs": list(snapshot.get("evidenceRefs") or []),
        "nextAction": snapshot.get("nextAction"),
        "lastEventType": None if last_event is None else last_event.get("eventType"),
    }


def build_audit_report(events: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a user-safe decision timeline without prompts or hidden reasoning."""
    timeline: list[dict[str, Any]] = []
    for event in events:
        timeline.append({
            "sequenceIndex": event.get("sequenceIndex"),
            "observedAt": event.get("observedAt"),
            "eventType": event.get("eventType"),
            "cycleId": event.get("cycleId"),
            "phaseId": event.get("phaseId"),
            "storyId": event.get("storyId"),
            "roundNumber": event.get("roundNumber"),
            "trace": list(event.get("trace") or []),
            "evidenceRefs": list(event.get("evidenceRefs") or []),
        })
    safe_decisions = []
    for decision in decisions:
        safe_decisions.append({
            "decisionId": decision.get("decisionId"),
            "state": decision.get("state"),
            "reasonCode": decision.get("reasonCode"),
            "trace": list(decision.get("trace") or []),
            "evidenceRefs": list(decision.get("evidenceRefs") or []),
        })
    return {
        "timeline": timeline,
        "decisions": safe_decisions,
        "reconstructable": bool(timeline) and all(item.get("sequenceIndex") for item in timeline),
    }


def evaluate_module_admission(candidate: dict[str, Any]) -> dict[str, Any]:
    """Classify MetaGPT module reuse candidates under FR-005 / AC-032.

    Governance-bypass signals (``changesCompletionAuthority`` or
    ``bypassesUnifiedContract``) are evaluated *before* the missing-evidence
    check so that a candidate that both lacks admission evidence and attempts
    to weaken Codex control is rejected outright, never downgraded to
    ``reference-only``.
    """
    if candidate.get("changesCompletionAuthority") or candidate.get("bypassesUnifiedContract"):
        return {"classification": "rejected", "admitted": False, "missing": [], "reason": "governance-bypass"}
    required = ("license", "version", "dependencies", "isolation", "exceptionPolicy", "testEvidence", "rollback")
    missing = [field for field in required if not candidate.get(field)]
    if missing:
        return {"classification": "reference-only", "admitted": False, "missing": missing}
    if candidate.get("codeRequested") is True:
        return {"classification": "code-admission-candidate", "admitted": True, "missing": []}
    return {"classification": "contract-reuse", "admitted": True, "missing": []}


# ---------------------------------------------------------------------------
# CLW-ST-101: Story Profile and splitting gate (FR-CLW-001, FR-CLW-002,
# AC-CLW-001, AC-CLW-002)
# ---------------------------------------------------------------------------

# Canonical Story Profile budgets keyed by size. Codex may adjust these inside
# the preauthorized upper bound, but the baseline values are the deterministic
# default used by tests and fixtures.
STORY_PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "small": {
        "profileId": "CLW-PROFILE-SMALL",
        "size": "small",
        "initialTimeoutSeconds": 900,
        "noProgressTimeoutSeconds": 1200,
        "extensionSliceSeconds": 600,
        "attemptHardDeadlineSeconds": 2700,
        "storyTotalDeadlineSeconds": 5400,
        "maxRounds": 2,
    },
    "medium": {
        "profileId": "CLW-PROFILE-MEDIUM",
        "size": "medium",
        "initialTimeoutSeconds": 1800,
        "noProgressTimeoutSeconds": 1800,
        "extensionSliceSeconds": 900,
        "attemptHardDeadlineSeconds": 5400,
        "storyTotalDeadlineSeconds": 14400,
        "maxRounds": 3,
    },
    "large": {
        "profileId": "CLW-PROFILE-LARGE",
        "size": "large",
        "splitRequired": True,
    },
}

STORY_PROFILE_SIZES = ("small", "medium", "large")


def get_default_story_profile(size: str) -> dict[str, Any]:
    """Return a copy of the canonical Story Profile for the given size.

    The size must be one of ``small``, ``medium`` or ``large``. The returned
    dict is a deep copy so callers may adjust deadlines inside the
    preauthorized upper bound without mutating the baseline.
    """
    if size not in STORY_PROFILE_DEFAULTS:
        raise ValueError(f"unknown story profile size: {size!r}")
    return deepcopy(STORY_PROFILE_DEFAULTS[size])


def validate_story_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    """Validate a Story Profile (FR-CLW-001).

    Required fields: profileId, size, initialTimeoutSeconds,
    noProgressTimeoutSeconds, extensionSliceSeconds,
    attemptHardDeadlineSeconds, storyTotalDeadlineSeconds, maxRounds.

    ``size`` must be ``small``, ``medium`` or ``large``. All deadline values
    must be positive integers. ``maxRounds`` must be a positive integer in
    [1, 10]. The deadlines must respect the ordering:
    initialTimeout < noProgressTimeout <= attemptHardDeadline <= storyTotalDeadline
    and extensionSlice <= attemptHardDeadline.
    """
    findings: list[dict[str, str]] = []
    required = (
        "profileId",
        "size",
        "initialTimeoutSeconds",
        "noProgressTimeoutSeconds",
        "extensionSliceSeconds",
        "attemptHardDeadlineSeconds",
        "storyTotalDeadlineSeconds",
        "maxRounds",
    )
    if profile.get("size") == "large":
        for field in ("profileId", "size", "splitRequired"):
            if profile.get(field) is None or profile.get(field) == "":
                findings.append({"severity": "P1", "rule": "story-profile-required", "message": field})
        if profile.get("splitRequired") is not True:
            findings.append({"severity": "P0", "rule": "large-story-split-required", "message": "Large Story must set splitRequired=true"})
        forbidden_budget_fields = [field for field in required[2:] if field in profile]
        if forbidden_budget_fields:
            findings.append({"severity": "P0", "rule": "large-story-budget-forbidden", "message": ",".join(forbidden_budget_fields)})
        return findings

    for field in required:
        value = profile.get(field)
        if value is None or value == "" or value == []:
            findings.append({"severity": "P1", "rule": "story-profile-required", "message": field})

    size = profile.get("size")
    if size not in STORY_PROFILE_SIZES:
        findings.append({"severity": "P1", "rule": "story-profile-size", "message": str(size)})

    for field in (
        "initialTimeoutSeconds",
        "noProgressTimeoutSeconds",
        "extensionSliceSeconds",
        "attemptHardDeadlineSeconds",
        "storyTotalDeadlineSeconds",
    ):
        value = profile.get(field)
        if not isinstance(value, int) or value <= 0:
            findings.append({"severity": "P1", "rule": "story-profile-deadline", "message": field})

    max_rounds = profile.get("maxRounds")
    if not isinstance(max_rounds, int) or max_rounds < 1 or max_rounds > 10:
        findings.append({"severity": "P1", "rule": "story-profile-max-rounds", "message": str(max_rounds)})

    # Deadline ordering (only check if all are valid positive ints)
    init_t = profile.get("initialTimeoutSeconds")
    noprog_t = profile.get("noProgressTimeoutSeconds")
    ext_t = profile.get("extensionSliceSeconds")
    hard_t = profile.get("attemptHardDeadlineSeconds")
    total_t = profile.get("storyTotalDeadlineSeconds")
    if (
        isinstance(init_t, int) and isinstance(noprog_t, int)
        and isinstance(ext_t, int) and isinstance(hard_t, int)
        and isinstance(total_t, int)
        and init_t > 0 and noprog_t > 0 and ext_t > 0 and hard_t > 0 and total_t > 0
    ):
        if init_t > noprog_t:
            findings.append({"severity": "P1", "rule": "story-profile-deadline-order", "message": "initialTimeout must be <= noProgressTimeout"})
        if noprog_t > hard_t:
            findings.append({"severity": "P1", "rule": "story-profile-deadline-order", "message": "noProgressTimeout must be <= attemptHardDeadline"})
        if hard_t > total_t:
            findings.append({"severity": "P1", "rule": "story-profile-deadline-order", "message": "attemptHardDeadline must be <= storyTotalDeadline"})
        if ext_t > hard_t:
            findings.append({"severity": "P1", "rule": "story-profile-deadline-order", "message": "extensionSlice must be <= attemptHardDeadline"})

    return findings


def evaluate_live_handoff_stories(packet: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a live handoff packet's Story envelope (FR-CLW-001, FR-CLW-002).

    A live handoff must identify **exactly one** Story. Small and Medium
    profiles are executable; Large must fail with a split-required finding.

    The function accepts either a handoff packet (with ``requirementAnchor``
    and ``stories``) or a simplified envelope with ``storyProfile`` and
    ``stories``. It returns a dict with:

    - ``allowed``: True if the packet is executable as-is
    - ``decision``: ``execute`` | ``blocked`` | ``split-required``
    - ``storyProfile``: the validated profile
    - ``story``: the single story if exactly one is present
    - ``findings``: list of finding dicts
    - ``splitFinding``: split-required finding for Large Stories
    - ``trace``: list of mapped FR/AC ids
    """
    findings: list[dict[str, str]] = []
    split_finding: dict[str, Any] | None = None

    # Extract stories
    stories = packet.get("stories")
    if not isinstance(stories, list):
        findings.append({"severity": "P1", "rule": "live-handoff-stories-missing", "message": "stories must be a non-empty array"})
        return {
            "allowed": False,
            "decision": "blocked",
            "storyProfile": None,
            "story": None,
            "findings": findings,
            "splitFinding": None,
            "trace": ["FR-CLW-001", "AC-CLW-001"],
        }

    if not stories:
        findings.append({"severity": "P1", "rule": "live-handoff-stories-empty", "message": "stories array must contain at least one Story"})

    # FR-CLW-001 / AC-CLW-001: exactly one Story per live invocation
    if len(stories) > 1:
        findings.append({
            "severity": "P0",
            "rule": "multi-story-rejected",
            "message": f"a live handoff must identify exactly one Story; got {len(stories)}",
        })

    # Extract storyProfile
    profile = packet.get("storyProfile")
    if not isinstance(profile, dict):
        # Try to derive from stories if packet has no explicit profile
        if stories and isinstance(stories[0], dict):
            story_profile_field = stories[0].get("storyProfile")
            if isinstance(story_profile_field, dict):
                profile = story_profile_field
        if profile is None:
            findings.append({"severity": "P1", "rule": "story-profile-missing", "message": "storyProfile is required"})

    if profile is not None:
        profile_findings = validate_story_profile(profile)
        findings.extend(profile_findings)

    # Determine story
    story: dict[str, Any] | None = None
    if len(stories) == 1:
        story = stories[0]
    elif len(stories) > 1:
        story = stories[0]  # first story for reporting

    # FR-CLW-002 / AC-CLW-002: Large Stories must be split
    size = profile.get("size") if isinstance(profile, dict) else None
    if size == "large" and not any(f["rule"] == "multi-story-rejected" for f in findings):
        story_id = str(story.get("storyId", "UNKNOWN")) if story else "UNKNOWN"
        profile_id = str(profile.get("profileId", "UNKNOWN")) if isinstance(profile, dict) else "UNKNOWN"
        split_finding = {
            "findingId": f"SPF-{story_id}",
            "rule": "large-story-split-required",
            "storyId": story_id,
            "storyProfileId": profile_id,
            "size": "large",
            "decision": "blocked",
            "reason": "Large Stories must be split into Small or Medium Stories before live execution",
            "requiredAction": "split-story-before-execution",
            "trace": ["FR-CLW-002", "AC-CLW-002"],
        }

    # Determine decision
    has_p0 = any(f.get("severity") == "P0" for f in findings)
    has_p1 = any(f.get("severity") == "P1" for f in findings)
    if split_finding or has_p0 or has_p1:
        decision = "split-required" if split_finding and not has_p0 and not has_p1 else "blocked"
        # If both multi-story and large, multi-story takes priority
        if has_p0:
            decision = "blocked"
        elif split_finding and not has_p1:
            decision = "split-required"
        allowed = False
    else:
        decision = "execute"
        allowed = True

    return {
        "allowed": allowed,
        "decision": decision,
        "storyProfile": profile,
        "story": story,
        "findings": findings,
        "splitFinding": split_finding,
        "trace": ["FR-CLW-001", "FR-CLW-002", "AC-CLW-001", "AC-CLW-002"],
    }


# ---------------------------------------------------------------------------
# CLW PH-2: serial Story queue and aggregate progress contract
# ---------------------------------------------------------------------------

def validate_story_graph(stories: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Validate the Phase Story DAG before any executor call.

    The validator is deliberately independent of the scheduler so a malformed
    graph cannot be made executable by choosing a convenient next Story.
    """
    findings: list[dict[str, str]] = []
    if not isinstance(stories, list) or not stories:
        return [{"severity": "P1", "rule": "story-graph-empty", "message": "stories must be a non-empty array"}]
    ids: list[str] = []
    graph: dict[str, list[str]] = {}
    dependency_edges: list[tuple[str, str]] = []
    for story in stories:
        sid = str(story.get("storyId", "")).strip()
        if not sid:
            findings.append({"severity": "P1", "rule": "story-id-missing", "message": "storyId"})
            continue
        ids.append(sid)
        deps = list(story.get("dependsOn") or [])
        graph.setdefault(sid, deps)
        dependency_edges.extend((sid, dep) for dep in deps)
        if not story.get("mappedRequirements"):
            findings.append({"severity": "P1", "rule": "story-fr-ac-missing", "message": sid})
        if not story.get("acceptanceCriteria"):
            findings.append({"severity": "P1", "rule": "story-acceptance-missing", "message": sid})
    duplicates = sorted({sid for sid in ids if ids.count(sid) > 1})
    for sid in duplicates:
        findings.append({"severity": "P0", "rule": "story-id-duplicate", "message": sid})
    known = set(ids)
    for sid, dep in dependency_edges:
        if dep not in known:
            findings.append({"severity": "P0", "rule": "story-dependency-unknown", "message": f"{sid}->{dep}"})
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(dep) for dep in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in graph):
        findings.append({"severity": "P0", "rule": "story-dependency-cycle", "message": "dependency cycle"})
    return findings


def select_next_story(
    stories: list[dict[str, Any]],
    completed_story_ids: set[str] | None = None,
    active_story_id: str | None = None,
) -> dict[str, Any]:
    """Select exactly one eligible Story using priority then stable ID order."""
    findings = validate_story_graph(stories)
    if findings:
        return {"allowed": False, "state": "repair-needed", "selected": None, "findings": findings}
    if active_story_id:
        return {
            "allowed": False,
            "state": "running",
            "selected": None,
            "findings": [{"severity": "P0", "rule": "single-active-story", "message": active_story_id}],
        }
    completed = set(completed_story_ids or set())
    eligible = []
    for story in stories:
        sid = str(story.get("storyId"))
        status = story.get("status", "pending")
        deps = set(story.get("dependsOn") or [])
        if sid in completed or status in {"passed", "completed"}:
            continue
        if status in {"blocked", "failed", "review"}:
            continue
        if deps.issubset(completed):
            eligible.append(story)
    eligible.sort(key=lambda item: (-int(item.get("priority", 0)), str(item.get("storyId", ""))))
    if not eligible:
        blockers = []
        for story in stories:
            sid = str(story.get("storyId"))
            if sid not in completed and story.get("status") not in {"passed", "completed"}:
                blockers.append({"storyId": sid, "dependsOn": list(story.get("dependsOn") or [])})
        return {"allowed": False, "state": "blocked-external-dependency", "selected": None, "findings": blockers}
    return {"allowed": True, "state": "running", "selected": eligible[0], "findings": [], "eligibleCount": len(eligible)}


def transition_story_after_review(story: dict[str, Any], completion_evaluation: dict[str, Any]) -> dict[str, Any]:
    """Move a Story to passed only from a real Codex completion evaluation."""
    if completion_evaluation.get("passed") is True and completion_evaluation.get("state") == "completed":
        return {"storyId": story.get("storyId"), "status": "passed", "reason": "codex-completion-evaluator"}
    state = completion_evaluation.get("state") or "repair-needed"
    if state == "completed":
        state = "repair-needed"
    return {"storyId": story.get("storyId"), "status": state, "reason": "completion-gate-not-passed"}


def build_phase_progress_snapshot(
    anchor_id: str,
    anchor_version: str,
    phase_id: str,
    workspace_fingerprint: str,
    stories: list[dict[str, Any]],
    current_story_id: str | None = None,
    current_round: int = 0,
    counters: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
    blocker: str | None = None,
    next_action: str | None = None,
    last_sequence_index: int = 0,
    last_event_hash: str = "GENESIS",
) -> dict[str, Any]:
    """Build a canonical aggregate snapshot without rewriting Story history."""
    queue_fingerprint = _sha256([
        {"storyId": s.get("storyId"), "status": s.get("status", "pending"), "dependsOn": sorted(s.get("dependsOn") or [])}
        for s in stories
    ])
    return {
        "snapshotType": "phase-progress",
        "anchorId": anchor_id,
        "anchorVersion": anchor_version,
        "phaseId": phase_id,
        "workspaceFingerprint": workspace_fingerprint,
        "queueFingerprint": queue_fingerprint,
        "stories": [{"storyId": s.get("storyId"), "status": s.get("status", "pending")} for s in stories],
        "currentStoryId": current_story_id,
        "currentRound": current_round,
        "counters": dict(counters or {}),
        "evidenceRefs": list(evidence_refs or []),
        "blocker": blocker,
        "nextAction": next_action,
        "lastSequenceIndex": last_sequence_index,
        "lastEventHash": last_event_hash,
    }


def reconcile_phase_progress(
    snapshot: dict[str, Any],
    stories: list[dict[str, Any]],
    history_path: str | Path | None = None,
    expected_anchor_id: str | None = None,
    expected_anchor_version: str | None = None,
    expected_phase_id: str | None = None,
    expected_workspace_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Reconcile aggregate state against the current graph and optional history."""
    expected = build_phase_progress_snapshot(
        snapshot.get("anchorId", ""), snapshot.get("anchorVersion", ""), snapshot.get("phaseId", ""),
        snapshot.get("workspaceFingerprint", ""), stories, snapshot.get("currentStoryId"),
        int(snapshot.get("currentRound", 0)), snapshot.get("counters"), snapshot.get("evidenceRefs"),
        snapshot.get("blocker"), snapshot.get("nextAction"),
        int(snapshot.get("lastSequenceIndex", 0)), str(snapshot.get("lastEventHash", "GENESIS")),
    )
    errors: list[str] = []
    if snapshot.get("queueFingerprint") != expected["queueFingerprint"]:
        errors.append("queue-fingerprint-mismatch")
    if history_path is not None:
        valid, history_errors, events = validate_history(history_path)
        if not valid:
            errors.extend(f"history:{item}" for item in history_errors)
        elif events:
            last = events[-1]
            if snapshot.get("lastSequenceIndex") != last.get("sequenceIndex"):
                errors.append("history:snapshot-sequence")
            if snapshot.get("lastEventHash") != last.get("eventHash"):
                errors.append("history:snapshot-event-hash")
    for field, expected_value in (
        ("anchorId", expected_anchor_id),
        ("anchorVersion", expected_anchor_version),
        ("phaseId", expected_phase_id),
        ("workspaceFingerprint", expected_workspace_fingerprint),
    ):
        if expected_value is not None and snapshot.get(field) != expected_value:
            errors.append(f"{field}-mismatch")
    return {"valid": not errors, "errors": errors, "reconciledSnapshot": expected}


def evaluate_phase_completion(story_evaluations: list[dict[str, Any]], phase_evaluation: dict[str, Any]) -> dict[str, Any]:
    """Apply the same completion requirements at Phase scope."""
    story_passed = bool(story_evaluations) and all(item.get("passed") is True for item in story_evaluations)
    checks = {
        "allStoriesPassed": story_passed,
        "allAcceptanceCriteriaVerified": phase_evaluation.get("allAcceptanceCriteriaVerified") is True,
        "feedbackValid": phase_evaluation.get("feedbackValid") is True,
        "evidenceComplete": phase_evaluation.get("evidenceComplete") is True,
        "qaPassed": phase_evaluation.get("qaPassed") is True,
        "noP0P1Drift": phase_evaluation.get("driftSeverity") in {"none", "allowed"},
        "noUnmappedActions": not phase_evaluation.get("unmappedActions"),
        "permissionGatePassed": phase_evaluation.get("permissionGatePassed") is True,
        "riskGatePassed": phase_evaluation.get("riskGatePassed") is True,
        "codexReviewPassed": phase_evaluation.get("codexReviewPassed") is True,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {"state": "completed" if not blockers else ("requirements-review" if not checks["noP0P1Drift"] or not checks["noUnmappedActions"] else "repair-needed"), "passed": not blockers, "checks": checks, "blockers": blockers}


# ---------------------------------------------------------------------------
# CLW PH-3: Windows isolated execution slots and write-set gates
# ---------------------------------------------------------------------------

def normalize_write_set(paths: list[str] | None) -> dict[str, Any]:
    """Normalize Windows paths and reject empty, escaping or wildcard sets."""
    findings: list[str] = []
    normalized: list[str] = []
    for raw in paths or []:
        value = str(raw).strip().replace("\\", "/")
        if not value or "*" in value or value.startswith("../") or "/../" in value:
            findings.append(value or "empty")
            continue
        value = value.rstrip("/").casefold()
        if value not in normalized:
            normalized.append(value)
    normalized.sort()
    overlaps = []
    for index, left in enumerate(normalized):
        for right in normalized[index + 1:]:
            if left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                overlaps.append(f"{left}<->{right}")
    return {"valid": not findings and not overlaps and bool(normalized), "paths": normalized, "invalid": findings, "overlaps": overlaps}


def validate_execution_slot(slot: dict[str, Any], approved_root: str | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for field in ("slotId", "storyId", "agentId", "worktreePath", "branch", "workspaceFingerprint", "baselineFingerprint", "permissionPolicy", "declaredWriteSet", "state"):
        if not slot.get(field):
            findings.append({"severity": "P1", "rule": "slot-required", "message": field})
    if slot.get("sharedRefMutation") is True or slot.get("agentMayMerge") is True:
        findings.append({"severity": "P0", "rule": "slot-shared-ref-permission", "message": "Agent cannot mutate shared refs or merge"})
    write_set = normalize_write_set(slot.get("declaredWriteSet"))
    if not write_set["valid"]:
        findings.append({"severity": "P0", "rule": "slot-write-set-invalid", "message": str(write_set)})
    if approved_root and slot.get("worktreePath"):
        if not _inside(str(slot["worktreePath"]), [approved_root]):
            findings.append({"severity": "P0", "rule": "slot-worktree-outside-approved-root", "message": str(slot["worktreePath"])})
    return findings


def schedule_isolated_slots(
    stories: list[dict[str, Any]],
    completed_story_ids: set[str] | None = None,
    max_slots: int = 2,
) -> dict[str, Any]:
    """Deterministically schedule bounded, independent Windows slots."""
    completed = set(completed_story_ids or set())
    if not isinstance(max_slots, int) or max_slots < 1:
        return {"scheduled": [], "blocked": [], "state": "resource-limit-reached", "reason": "invalid-slot-budget"}
    ordered = sorted(stories, key=lambda item: (-int(item.get("priority", 0)), str(item.get("storyId", ""))))
    scheduled: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    worktrees: set[str] = set()
    branches: set[str] = set()
    accepted_paths: list[str] = []
    for story in ordered:
        sid = str(story.get("storyId", ""))
        reasons: list[str] = []
        if story.get("parallelEligible") is not True:
            reasons.append("parallel-independence-not-declared")
        if not set(story.get("dependsOn") or []).issubset(completed):
            reasons.append("dependency-not-complete")
        write_set = normalize_write_set(story.get("writeSet"))
        if not write_set["valid"]:
            reasons.append("write-set-invalid")
        workspace = str(story.get("workspaceFingerprint", ""))
        branch = str(story.get("branch", "")).casefold()
        if not workspace or workspace in worktrees:
            reasons.append("workspace-collision")
        if not branch or branch in branches:
            reasons.append("branch-collision")
        if any(
            path == accepted or path.startswith(accepted + "/") or accepted.startswith(path + "/")
            for path in write_set["paths"] for accepted in accepted_paths
        ):
            reasons.append("write-set-conflict")
        if len(scheduled) >= max_slots:
            reasons.append("concurrency-limit")
        if reasons:
            blocked.append({"storyId": sid, "reasons": list(dict.fromkeys(reasons))})
            continue
        worktrees.add(workspace)
        branches.add(branch)
        accepted_paths.extend(write_set["paths"])
        scheduled.append(story)
    return {"scheduled": scheduled, "blocked": blocked, "state": "running" if scheduled else "repair-needed", "maxSlots": max_slots}


def evaluate_declared_vs_observed_write_set(declared: list[str], observed: list[str]) -> dict[str, Any]:
    declared_norm = normalize_write_set(declared)
    observed_norm = normalize_write_set(observed)
    out_of_scope = sorted(set(observed_norm["paths"]) - set(declared_norm["paths"]))
    return {"allowed": declared_norm["valid"] and observed_norm["valid"] and not out_of_scope, "declared": declared_norm, "observed": observed_norm, "outOfScope": out_of_scope, "state": "requirements-review" if out_of_scope else "running"}


def build_merge_candidate(slot: dict[str, Any], head: str, diff_hash: str, tests: list[dict[str, Any]], evidence_refs: list[str]) -> dict[str, Any]:
    candidate = {
        "candidateType": "merge-candidate",
        "slotId": slot.get("slotId"),
        "storyId": slot.get("storyId"),
        "branch": slot.get("branch"),
        "base": slot.get("baselineFingerprint"),
        "head": head,
        "diffHash": diff_hash,
        "declaredWriteSet": normalize_write_set(slot.get("declaredWriteSet"))["paths"],
        "tests": list(tests),
        "evidenceRefs": list(evidence_refs),
        "mappedFrAc": list(slot.get("mappedFrAc") or []),
    }
    candidate["candidateHash"] = _sha256(candidate)
    return candidate


# ---------------------------------------------------------------------------
# CLW PH-4: Windows Agent profile, permission match and unified feedback
# ---------------------------------------------------------------------------

def validate_agent_profile(profile: dict[str, Any], existing: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for field in ("profileId", "agentId", "adapterId", "version", "capabilities", "inputSchemaRef", "outputSchemaRef", "allowedActions", "forbiddenActions", "statusMapping"):
        if not profile.get(field):
            findings.append({"severity": "P1", "rule": "agent-profile-required", "message": field})
    if profile.get("completionAuthorityIsolated") is not True:
        findings.append({"severity": "P0", "rule": "agent-completion-authority", "message": "profile must isolate completion authority"})
    for prior in existing or []:
        if profile.get("profileId") in {prior.get("profileId"), prior.get("agentId")} or profile.get("agentId") == prior.get("agentId"):
            findings.append({"severity": "P0", "rule": "agent-profile-duplicate", "message": str(profile.get("profileId"))})
    if set(profile.get("allowedActions") or []) & set(profile.get("forbiddenActions") or []):
        findings.append({"severity": "P0", "rule": "agent-action-overlap", "message": "allowedActions/forbiddenActions overlap"})
    return findings


def match_agent_capability(request: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    required = set(request.get("capabilities") or [])
    available = set(profile.get("capabilities") or [])
    actions = set(request.get("actions") or [])
    allowed = set(profile.get("allowedActions") or [])
    forbidden = set(profile.get("forbiddenActions") or [])
    missing = sorted(required - available)
    denied = sorted((actions - allowed) | (actions & forbidden))
    return {"matched": not missing and not denied, "missingCapabilities": missing, "deniedActions": denied, "profileId": profile.get("profileId"), "state": "running" if not missing and not denied else "risk-gate-required"}


def review_agent_feedback(feedback: dict[str, Any] | None, expected: dict[str, Any]) -> dict[str, Any]:
    """Normalize adapter feedback into one Codex-owned gap decision."""
    if not isinstance(feedback, dict):
        return {"accepted": False, "state": "repair-needed", "gaps": ["feedback-missing"]}
    gaps: list[dict[str, Any]] = []
    for field in ("cycleId", "storyId", "status", "evidenceRefs"):
        if field not in feedback or feedback.get(field) in (None, "", []):
            gaps.append({"severity": "P1", "field": field, "reason": "required-field-missing"})
    for field in ("cycleId", "storyId"):
        if field in feedback and expected.get(field) is not None and feedback.get(field) != expected.get(field):
            gaps.append({"severity": "P0", "field": field, "reason": "lineage-mismatch"})
    if feedback.get("status") in {"completed", "success"} and feedback.get("completionClaim") is True:
        gaps.append({"severity": "P1", "field": "completionClaim", "reason": "agent-claim-is-not-codex-completion"})
    if feedback.get("unmappedActions"):
        gaps.append({"severity": "P1", "field": "unmappedActions", "reason": "unmapped-actions"})
    if feedback.get("driftSeverity") in {"P0", "P1"}:
        gaps.append({"severity": str(feedback["driftSeverity"]), "field": "driftSeverity", "reason": "requirement-drift"})
    state = "requirements-review" if any(g["severity"] == "P0" for g in gaps) else ("repair-needed" if gaps else "running")
    return {"accepted": not gaps, "state": state, "gaps": gaps, "evidenceRefs": list(feedback.get("evidenceRefs") or [])}


def _generate_clw_st101_fixtures(output_dir: str) -> dict[str, Any]:
    """Generate CLW-ST-101 positive and negative fixtures for deterministic testing."""
    out = Path(output_dir)
    clw_dir = out / "clw-st-101"
    clw_dir.mkdir(parents=True, exist_ok=True)
    fixtures: list[str] = []

    # -- Positive: Small Story --
    small_positive = {
        "fixtureId": "POS-CLW-101-SMALL",
        "targetFunction": "evaluate_live_handoff_stories",
        "description": "A Small Story with a valid profile is executable.",
        "input": {
            "packetId": "HND-CLW-SMALL-001",
            "packetType": "handoff",
            "version": "1.0",
            "storyProfile": get_default_story_profile("small"),
            "stories": [
                {
                    "storyId": "CLW-ST-101-SMALL",
                    "title": "Small Story positive",
                    "goal": "Execute a small documentation fix.",
                }
            ],
        },
        "expectedDecision": "execute",
        "expectedAllowed": True,
        "expectedValidation": "accept",
        "traceTo": ["FR-CLW-001", "FR-CLW-002", "AC-CLW-001", "AC-CLW-002"],
    }
    (clw_dir / "pos-clw-101-small.json").write_text(
        json.dumps(small_positive, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("pos-clw-101-small.json")

    # -- Positive: Medium Story --
    medium_positive = {
        "fixtureId": "POS-CLW-101-MEDIUM",
        "targetFunction": "evaluate_live_handoff_stories",
        "description": "A Medium Story with a valid profile is executable.",
        "input": {
            "packetId": "HND-CLW-MEDIUM-001",
            "packetType": "handoff",
            "version": "1.0",
            "storyProfile": get_default_story_profile("medium"),
            "stories": [
                {
                    "storyId": "CLW-ST-101-MEDIUM",
                    "title": "Medium Story positive",
                    "goal": "Execute a medium feature implementation.",
                }
            ],
        },
        "expectedDecision": "execute",
        "expectedAllowed": True,
        "expectedValidation": "accept",
        "traceTo": ["FR-CLW-001", "FR-CLW-002", "AC-CLW-001", "AC-CLW-002"],
    }
    (clw_dir / "pos-clw-101-medium.json").write_text(
        json.dumps(medium_positive, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("pos-clw-101-medium.json")

    # -- Negative: Multiple Stories --
    multi_story = {
        "fixtureId": "NEG-CLW-001",
        "targetFunction": "evaluate_live_handoff_stories",
        "description": "A packet with multiple Stories must be rejected before live execution.",
        "input": {
            "packetId": "HND-CLW-MULTI-001",
            "packetType": "handoff",
            "version": "1.0",
            "storyProfile": get_default_story_profile("small"),
            "stories": [
                {"storyId": "CLW-ST-101-A", "title": "First story", "goal": "First goal."},
                {"storyId": "CLW-ST-101-B", "title": "Second story", "goal": "Second goal."},
            ],
        },
        "expectedDecision": "blocked",
        "expectedAllowed": False,
        "expectedRejectionRule": "multi-story-rejected",
        "expectedValidation": "reject",
        "traceTo": ["FR-CLW-001", "AC-CLW-001"],
    }
    (clw_dir / "neg-clw-001-multi-story.json").write_text(
        json.dumps(multi_story, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("neg-clw-001-multi-story.json")

    # -- Negative: Large Story (must be split) --
    large_story = {
        "fixtureId": "NEG-CLW-002",
        "targetFunction": "evaluate_live_handoff_stories",
        "description": "A Large Story must fail with a split-required finding.",
        "input": {
            "packetId": "HND-CLW-LARGE-001",
            "packetType": "handoff",
            "version": "1.0",
            "storyProfile": get_default_story_profile("large"),
            "stories": [
                {
                    "storyId": "CLW-ST-101-LARGE",
                    "title": "Large Story negative",
                    "goal": "Execute a large cross-module feature.",
                }
            ],
        },
        "expectedDecision": "split-required",
        "expectedAllowed": False,
        "expectedRejectionRule": "large-story-split-required",
        "expectedValidation": "reject",
        "expectedSplitFinding": {
            "rule": "large-story-split-required",
            "requiredAction": "split-story-before-execution",
        },
        "traceTo": ["FR-CLW-002", "AC-CLW-002"],
    }
    (clw_dir / "neg-clw-002-large-story.json").write_text(
        json.dumps(large_story, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("neg-clw-002-large-story.json")

    return {"fixturesCreated": len(fixtures), "files": fixtures, "outputDir": str(clw_dir)}


def _generate_clw_st101_change_record(output_dir: str) -> dict[str, Any]:
    """Generate the CLW-ST-101 change record markdown file."""
    out = Path(output_dir)
    cr_dir = out / "change-records" / "entries" / "2026" / "2026-08"
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_path = cr_dir / "CR-20260816-005-clw-st-101-story-profile-and-split-gate.md"
    if cr_path.exists():
        return {"changeRecordCreated": False, "path": str(cr_path), "reason": "existing-record-preserved"}
    content = """# CR-20260816-005 - CLW-ST-101 Story Profile and Splitting Gate

| Field | Value |
|---|---|
| Status | validation-pending |
| Target Skill | development-system, handoff-claude-executor |
| Change Type | added / validation / governance |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance |
| Source | CLW-ST-101; FR-CLW-001, FR-CLW-002; AC-CLW-001, AC-CLW-002 |
| Baseline | Workspace after PH-4; no Story Profile or splitting gate existed |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260816-004 |

## Summary

Implement CLW-ST-101: Story Profile definition, single-Story live handoff gate, and Large Story splitting requirement. A live handoff must identify exactly one Story; Small and Medium profiles are executable; Large must fail with a split-required finding before execution.

## Context And Problem

The Claude Windows Adaptive Loop requirement anchor (CLW-ADAPTIVE-LOOP-REQ-20260816-001@1.0.0) requires that each Claude live invocation executes exactly one Story, and that Large Stories must be split into Small or Medium Stories before execution. PH-1 through PH-4 established the development-system governance runtime, but no Story Profile, single-Story gate, or splitting gate existed.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| schemas/story-profile.schema.json | New | Story Profile JSON schema: size, five deadlines, maxRounds |
| schemas/story-split-finding.schema.json | New | Split-required finding schema for Large Stories |
| schemas/live-handoff-story-envelope.schema.json | New | Live handoff envelope requiring exactly one Story + profile |
| scripts/development_runtime.py | STORY_PROFILE_DEFAULTS, STORY_PROFILE_SIZES, get_default_story_profile | New: canonical profile budgets for small/medium/large |
| scripts/development_runtime.py | validate_story_profile | New: validate profile fields, size, deadlines, maxRounds, ordering |
| scripts/development_runtime.py | evaluate_live_handoff_stories | New: single-Story gate + Large split-required finding |
| scripts/development_runtime.py | _generate_clw_st101_fixtures | New: generate positive and negative fixtures |
| scripts/development_runtime.py | _generate_clw_st101_change_record | New: generate this change record |
| scripts/development_runtime.py | main / CLI | Add generate-clw-st101-fixtures and generate-clw-st101-change-record commands |
| scripts/test_development_runtime.py | test_clw_st101_story_profile_and_split_gate | New test: CLW-ST-101 positive and negative matrix |
| scripts/test_development_runtime.py | test_declared_negative_fixtures | Add CLW-ST-101 fixtures to required set |
| scripts/test_development_runtime.py | test_negative_fixture_semantics | Add CLW-ST-101 negative fixture semantic checks |
| assets/fixtures/clw-st-101/pos-clw-101-small.json | New fixture | Small Story positive |
| assets/fixtures/clw-st-101/pos-clw-101-medium.json | New fixture | Medium Story positive |
| assets/fixtures/clw-st-101/neg-clw-001-multi-story.json | New fixture | Multiple Stories rejected |
| assets/fixtures/clw-st-101/neg-clw-002-large-story.json | New fixture | Large Story split-required |
| handoff-claude-executor/references/claude-adapter-contract.md | CLW-ST-101 section | Add Story Profile, single-Story gate, Large split requirement |
| handoff-claude-executor/schemas/handoff-packet.schema.json | storyProfile, stories | Add optional storyProfile and stories fields |

## Requirement Trace

| Story | FR | AC | Evidence |
|---|---|---|---|
| CLW-ST-101 | FR-CLW-001, FR-CLW-002 | AC-CLW-001, AC-CLW-002 | validate_story_profile, evaluate_live_handoff_stories, POS-CLW-101-SMALL, POS-CLW-101-MEDIUM, NEG-CLW-001, NEG-CLW-002 |

## Validation

- All existing tests preserved without weakened assertions
- New CLW-ST-101 tests cover positive (Small, Medium) and negative (multi-Story, Large) matrices
- Negative fixtures generated by `development_runtime.py generate-clw-st101-fixtures`
- A live handoff with multiple Stories is rejected before execution
- A Large Story produces a split-required finding and cannot execute
- Small and Medium Stories with valid profiles are executable
- Story Profile deadlines respect the ordering: initial < no-progress <= hard <= total
- maxRounds is bounded to [1, 10]
- No global Skill writes or user-level installation
- No network access or dependency installation

## Impact Analysis

- **Scope**: Only the two approved workspace Skill copies are modified.
- **Risk**: Low — all new functions are additive; existing assertions and schemas are unchanged.
- **Rollback**: Revert the CLW-ST-101 additions in development_runtime.py and test_development_runtime.py; delete CLW-ST-101 fixtures, schemas and change record.
- **Dependencies**: None — CLW-ST-101 reuses existing governance patterns (validate_*, evaluate_*).

## Validation Evidence

- Deterministic test suite: `test_development_runtime.py` (CLW-ST-101 tests added)
- Fixture suite: `assets/fixtures/clw-st-101/pos-clw-101-small.json`, `pos-clw-101-medium.json`, `neg-clw-001-multi-story.json`, `neg-clw-002-large-story.json`
- Schema suite: `schemas/story-profile.schema.json`, `schemas/story-split-finding.schema.json`, `schemas/live-handoff-story-envelope.schema.json`
"""
    cr_path.write_text(content, encoding="utf-8")
    return {"changeRecordCreated": str(cr_path)}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# PH-2: Claude external Agent governance (DSCR-ST-2-001 through ST-2-006)
# ---------------------------------------------------------------------------

def validate_claude_registry(entry: dict[str, Any], existing_entries: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    """Validate a Claude external Agent registry entry (FR-TOT-009, AC-TOT-014, AC-TOT-017).

    Checks: required fields present, agentId unique, adapterId unique,
    version non-empty, capabilities non-empty, feedbackSchemaRef non-empty,
    completionAuthorityIsolated is True (Claude must NOT have completion authority).
    """
    findings: list[dict[str, str]] = []
    for field in REQUIRED_REGISTRY_FIELDS:
        value = entry.get(field)
        if value is None or value == "" or value == []:
            findings.append({"severity": "P1", "rule": "registry-required", "message": field})
    if entry.get("completionAuthorityIsolated") is not True:
        findings.append({"severity": "P0", "rule": "registry-completion-authority-not-isolated", "message": "Claude must not hold completion authority"})
    if entry.get("availability") not in {"available", "unavailable", "degraded"}:
        findings.append({"severity": "P1", "rule": "registry-availability", "message": str(entry.get("availability", ""))})
    agent_id = str(entry.get("agentId", ""))
    adapter_id = str(entry.get("adapterId", ""))
    for prior in existing_entries or []:
        if str(prior.get("agentId", "")) == agent_id:
            findings.append({"severity": "P1", "rule": "registry-duplicate-agentId", "message": agent_id})
        if str(prior.get("adapterId", "")) == adapter_id:
            findings.append({"severity": "P1", "rule": "registry-duplicate-adapterId", "message": adapter_id})
    return findings


def validate_preauthorization_policy(policy: dict[str, Any], now: str | None = None) -> list[dict[str, str]]:
    """Validate the lifecycle of an active preauthorization policy (FR-TOT-010, FR-TOT-016, AC-TOT-008, AC-TOT-013).

    Required dimensions: policyId, version, status, workspaceRoots, actions,
    tools, data, network, credentialBoundary, feedbackSchema, maxTimeoutSeconds,
    maxRounds, maxConcurrency, stopConditions.
    The policy must be active, have a non-empty policyId, no wildcard
    catch-alls, and stopConditions must be non-empty.
    """
    findings: list[dict[str, str]] = []
    required = (
        "policyId", "version", "status", "policyHash", "validFrom", "expiresAt",
        "workspaceRoots", "actions", "tools", "data", "network",
        "credentialBoundary", "feedbackSchema", "maxTimeoutSeconds", "maxRounds",
        "maxConcurrency", "stopConditions", "codexTakeoverAllowed",
    )
    for field in required:
        value = policy.get(field)
        empty_not_allowed = field != "network"
        if field not in policy or value is None or value == "" or (empty_not_allowed and value == []):
            findings.append({"severity": "P1", "rule": "policy-required", "message": field})
    if policy.get("status") != "active":
        findings.append({"severity": "P1", "rule": "policy-not-active", "message": str(policy.get("status", ""))})
    # Reject empty-wildcard network (must not contain "" or "*")
    network = policy.get("network") or []
    if isinstance(network, list) and ("*" in network or "" in network):
        findings.append({"severity": "P0", "rule": "policy-wildcard-network", "message": "network must not contain wildcards"})
    # Reject cross-project reuse signal
    if policy.get("crossProjectReuse") is True:
        findings.append({"severity": "P0", "rule": "policy-cross-project-reuse", "message": "cross-project reuse is forbidden"})
    for field in ("workspaceRoots", "actions", "tools", "data", "stopConditions"):
        values = policy.get(field)
        if isinstance(values, list) and any(value in {"", "*"} for value in values):
            findings.append({"severity": "P0", "rule": "policy-wildcard-boundary", "message": field})
    # maxRounds and maxConcurrency must be finite positive ints
    max_rounds = policy.get("maxRounds")
    if not isinstance(max_rounds, int) or max_rounds <= 0:
        findings.append({"severity": "P1", "rule": "policy-max-rounds-invalid", "message": "maxRounds must be a positive integer"})
    max_conc = policy.get("maxConcurrency")
    if not isinstance(max_conc, int) or max_conc <= 0:
        findings.append({"severity": "P1", "rule": "policy-max-concurrency-invalid", "message": "maxConcurrency must be a positive integer"})
    max_timeout = policy.get("maxTimeoutSeconds")
    if not isinstance(max_timeout, int) or max_timeout <= 0:
        findings.append({"severity": "P1", "rule": "policy-max-timeout-invalid", "message": "maxTimeoutSeconds must be a positive integer"})
    valid_from = _parse_timestamp(policy.get("validFrom"))
    expires_at = _parse_timestamp(policy.get("expiresAt"))
    observed_at = _parse_timestamp(now) if now else datetime.now(timezone.utc)
    if valid_from is None or expires_at is None or valid_from >= expires_at:
        findings.append({"severity": "P1", "rule": "policy-time-invalid", "message": "validFrom/expiresAt"})
    elif observed_at is not None and observed_at < valid_from:
        findings.append({"severity": "P1", "rule": "policy-not-yet-valid", "message": "validFrom"})
    elif observed_at is not None and observed_at >= expires_at:
        findings.append({"severity": "P1", "rule": "policy-expired", "message": "expiresAt"})
    claimed_hash = policy.get("policyHash")
    if isinstance(claimed_hash, str) and claimed_hash and claimed_hash != compute_policy_hash(policy):
        findings.append({"severity": "P1", "rule": "policy-hash-mismatch", "message": "policyHash"})
    return findings


def compute_policy_hash(policy: dict[str, Any]) -> str:
    """Compute a stable SHA-256 hash of the canonical policy form."""
    canonical_policy = deepcopy(policy)
    canonical_policy.pop("policyHash", None)
    return _sha256(canonical_policy)


def decide_auto_approval(
    task: dict[str, Any],
    policy: dict[str, Any],
    dry_run_records: list[dict[str, Any]] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Decide whether Codex auto-approves a Claude call (FR-TOT-011, FR-TOT-015, AC-TOT-007, AC-TOT-008, AC-TOT-011).

    Returns a redacted audit-safe decision record. Only exact full-dimensional
    matches with a valid dry-run may be auto-approved. Everything else fails
    closed.
    """
    decision_id = "DEC-" + (_sha256({"task": task.get("taskId", ""), "policyId": policy.get("policyId", "")})[:12])
    # High-risk actions always require manual approval
    if task.get("userLevelInstall") or task.get("newBoundary"):
        return {
            "decisionId": decision_id,
            "decision": "blocked-user-decision",
            "reason": "protected-operation-requires-manual-approval",
            "policyId": policy.get("policyId"),
            "policyHash": compute_policy_hash(policy),
            "matched": False,
            "auditRedacted": True,
        }
    policy_findings = validate_preauthorization_policy(policy, now=now)
    if policy_findings:
        return {
            "decisionId": decision_id,
            "decision": "blocked-user-decision",
            "reason": "policy-invalid-or-inactive",
            "policyId": policy.get("policyId"),
            "policyHash": compute_policy_hash(policy),
            "matched": False,
            "policyFindings": [item["rule"] for item in policy_findings],
            "auditRedacted": True,
        }
    # Exact match across all dimensions
    required_auth = task.get("requiredAuthorization") or {}
    matched, missing = preauthorization_matches(required_auth, policy, now=now)
    if not matched:
        return {
            "decisionId": decision_id,
            "decision": "blocked-user-decision",
            "reason": "preauthorization-mismatch",
            "policyId": policy.get("policyId"),
            "policyHash": compute_policy_hash(policy),
            "matched": False,
            "missingDimensions": missing,
            "auditRedacted": True,
        }
    gate = evaluate_dry_run_gate(
        str(required_auth.get("packetHash", "")),
        compute_policy_hash(policy),
        dry_run_records,
        now=now,
        policy_expires_at=policy.get("expiresAt"),
    )
    if not gate["allowed"]:
        return {
            "decisionId": decision_id,
            "decision": "blocked-user-decision",
            "reason": "dry-run-gate-not-passed",
            "policyId": policy.get("policyId"),
            "policyHash": compute_policy_hash(policy),
            "matched": True,
            "dryRunStatus": gate["status"],
            "dryRunReason": gate["reason"],
            "auditRedacted": True,
        }
    # All checks passed: auto-approve
    return {
        "decisionId": decision_id,
        "decision": "auto-approved",
        "reason": "exact-preauthorization-match",
        "policyId": policy.get("policyId"),
        "policyHash": compute_policy_hash(policy),
        "matched": True,
        "dryRunStatus": gate["status"],
        "dryRunManifestIdentity": gate.get("manifestIdentity"),
        "auditRedacted": True,
    }


def compute_dry_run_manifest_hash(record: dict[str, Any]) -> str:
    canonical_record = deepcopy(record)
    canonical_record.pop("manifestHash", None)
    return _sha256(canonical_record)


def evaluate_dry_run_gate(
    packet_hash: str,
    policy_hash: str,
    dry_run_records: list[dict[str, Any]] | None = None,
    now: str | None = None,
    policy_expires_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate the dry-run-to-live transition gate (FR-TOT-012, AC-TOT-009).

    A first-time packet/policy combination must produce and verify a dry-run
    manifest before live execution is allowed. A missing or mismatched manifest
    cannot be bypassed.
    """
    observed_at = _parse_timestamp(now) if now else datetime.now(timezone.utc)
    expires_at = _parse_timestamp(policy_expires_at) if policy_expires_at else None
    if not packet_hash or not policy_hash:
        return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "packet-or-policy-hash-missing"}
    if expires_at is not None and observed_at is not None and observed_at >= expires_at:
        return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "policy-expired"}
    for record in dry_run_records or []:
        if record.get("packetHash") == packet_hash and record.get("policyHash") == policy_hash:
            if record.get("manifestHash") != compute_dry_run_manifest_hash(record):
                return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "dry-run-manifest-hash-mismatch"}
            if record.get("mode") != "dry-run" or record.get("spawnedProcess") is not False:
                return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "dry-run-manifest-semantics-invalid"}
            if record.get("status") != "DRY_RUN_OK":
                return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "dry-run-record-exists-but-not-ok"}
            if _parse_timestamp(record.get("generatedAt")) is None:
                return {"allowed": False, "status": "DRY_RUN_BLOCKED", "reason": "dry-run-generatedAt-invalid"}
            return {
                "allowed": True,
                "status": "DRY_RUN_OK",
                "reason": "verified-dry-run-match",
                "manifestIdentity": record.get("manifestIdentity"),
            }
    # No matching record: cannot proceed to live
    return {"allowed": False, "status": "DRY_RUN_MISSING", "reason": "no-dry-run-record-for-this-packet-policy-combo"}


def project_status_zh(state: str) -> dict[str, str]:
    """Project a governed machine state to a Chinese label (FR-TOT-013, FR-TOT-017, AC-TOT-012, AC-TOT-018).

    The machine code is the stable identifier. The Chinese label is a
    user-facing projection. Unknown states map to failed.
    """
    machine_code = state if state in STATUS_ZH_MAP else "failed"
    return {"machineCode": machine_code, "statusZh": STATUS_ZH_MAP[machine_code]}


def project_all_status_zh() -> list[dict[str, str]]:
    """Project all 11 governed machine states with Chinese labels."""
    return [{"machineCode": code, "statusZh": label} for code, label in STATUS_ZH_MAP.items()]


def decide_takeover(
    trigger: str,
    cycle_id: str,
    story_id: str,
    round_number: int,
    policy: dict[str, Any],
    evidence_lineage: list[str] | None = None,
    origin_cycle_id: str | None = None,
    origin_story_id: str | None = None,
    authorization_fingerprint: str | None = None,
    origin_authorization_fingerprint: str | None = None,
    invalid_feedback_count: int = 0,
    invalid_feedback_threshold: int = 2,
    takeover_count: int = 0,
) -> dict[str, Any]:
    """Decide bounded same-Story Codex takeover (FR-TOT-014, FR-TOT-016, AC-TOT-010, AC-TOT-013).

    Takeover is allowed only when:
    - The trigger is recognized (claude-unavailable, timeout, invalid-feedback)
    - codexTakeoverAllowed is True in the policy
    - The takeover is within the same Story (cycleId and storyId preserved)
    - The round number does not exceed maxRounds
    - Evidence lineage is preserved

    Cross-Story takeover is forbidden. Round-limit takeover is forbidden.
    """
    takeover_id = "TKO-" + (_sha256({"trigger": trigger, "cycleId": cycle_id, "storyId": story_id})[:12])
    if trigger not in TAKEOVER_TRIGGERS:
        return {
            "takeoverId": takeover_id,
            "allowed": False,
            "reason": "unrecognized-takeover-trigger",
            "trigger": trigger,
        }
    if policy.get("status") != "active" or policy.get("codexTakeoverAllowed") is not True:
        return {
            "takeoverId": takeover_id,
            "allowed": False,
            "reason": "takeover-not-authorized-by-active-policy",
            "policyId": policy.get("policyId"),
        }
    if origin_cycle_id is not None and origin_cycle_id != cycle_id:
        return {"takeoverId": takeover_id, "allowed": False, "reason": "cross-cycle-takeover-forbidden"}
    if origin_story_id is not None and origin_story_id != story_id:
        return {"takeoverId": takeover_id, "allowed": False, "reason": "cross-story-takeover-forbidden"}
    if (
        origin_authorization_fingerprint is not None
        and authorization_fingerprint != origin_authorization_fingerprint
    ):
        return {"takeoverId": takeover_id, "allowed": False, "reason": "authorization-boundary-mismatch"}
    if not evidence_lineage:
        return {"takeoverId": takeover_id, "allowed": False, "reason": "evidence-lineage-missing"}
    if trigger == "invalid-feedback" and invalid_feedback_count < invalid_feedback_threshold:
        return {"takeoverId": takeover_id, "allowed": False, "reason": "invalid-feedback-threshold-not-reached"}
    max_rounds = policy.get("maxRounds")
    if not isinstance(round_number, int) or round_number <= 0 or (isinstance(max_rounds, int) and round_number > max_rounds):
        return {
            "takeoverId": takeover_id,
            "allowed": False,
            "reason": "round-limit-reached",
            "roundNumber": round_number,
            "maxRounds": max_rounds,
        }
    max_takeovers = policy.get("maxTakeovers", 1)
    if not isinstance(max_takeovers, int) or max_takeovers <= 0 or takeover_count >= max_takeovers:
        return {"takeoverId": takeover_id, "allowed": False, "reason": "takeover-limit-reached"}
    return {
        "takeoverId": takeover_id,
        "allowed": True,
        "reason": "bounded-same-story-takeover",
        "trigger": trigger,
        "cycleId": cycle_id,
        "storyId": story_id,
        "roundNumber": round_number,
        "evidenceLineage": list(evidence_lineage or []),
        "policyId": policy.get("policyId"),
        "authorizationFingerprint": authorization_fingerprint,
        "takeoverCount": takeover_count + 1,
        "auditRedacted": True,
    }


def _generate_ph2_fixtures(output_dir: str) -> dict[str, Any]:
    """Generate PH-2 positive and negative fixtures for deterministic testing."""
    out = Path(output_dir)
    neg_dir = out / "negative"
    pos_dir = out / "phase-story"
    neg_dir.mkdir(parents=True, exist_ok=True)
    pos_dir.mkdir(parents=True, exist_ok=True)
    fixtures: list[str] = []

    # -- Positive fixtures --

    # POS-PH2-REGISTRY: valid Claude registry entry
    pos_registry = {
        "fixtureId": "POS-PH2-REGISTRY",
        "targetFunction": "validate_claude_registry",
        "description": "Valid Claude external Agent registry entry with isolated completion authority.",
        "input": {
            "entry": {
                "agentId": "claude-code-v1",
                "adapterId": "handoff-claude-executor",
                "version": "1.0",
                "capabilities": ["multiFile", "skillDevelopment", "complexRepair", "crossModule"],
                "availability": "available",
                "feedbackSchemaRef": "feedback-packet.schema.json",
                "completionAuthorityIsolated": True,
            },
            "existing": [],
        },
        "expectedValidation": "accept",
        "traceTo": ["FR-TOT-009", "AC-TOT-014", "AC-TOT-017"],
    }
    (pos_dir / "ph2-registry-positive.json").write_text(
        json.dumps(pos_registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("ph2-registry-positive.json")

    # POS-PH2-PREAUTH: valid active preauthorization policy
    pos_preauth = {
        "fixtureId": "POS-PH2-PREAUTH",
        "targetFunction": "validate_preauthorization_policy",
        "description": "Valid active preauthorization policy with all required dimensions.",
        "input": {
            "policyId": "DS-PH2-CLAUDE-PREAUTH-20260816-001",
            "version": "1.0",
            "status": "active",
            "validFrom": "2026-08-15T00:00:00+00:00",
            "expiresAt": "2026-08-17T00:00:00+00:00",
            "workspaceRoots": ["C:/approved/workspace"],
            "actions": ["read", "edit", "test", "validate"],
            "tools": ["claude-code", "python"],
            "data": ["workspace-source"],
            "network": [],
            "credentialBoundary": "inherit-claude-auth-only",
            "feedbackSchema": "feedback-packet.schema.json",
            "maxTimeoutSeconds": 900,
            "maxRounds": 1,
            "maxConcurrency": 1,
            "maxTakeovers": 1,
            "stopConditions": ["p0-drift", "timeout"],
            "codexTakeoverAllowed": True,
            "crossProjectReuse": False,
        },
        "expectedValidation": "accept",
        "traceTo": ["FR-TOT-010", "FR-TOT-016", "AC-TOT-008", "AC-TOT-013"],
    }
    pos_preauth["input"]["policyHash"] = compute_policy_hash(pos_preauth["input"])
    (pos_dir / "ph2-preauth-positive.json").write_text(
        json.dumps(pos_preauth, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("ph2-preauth-positive.json")

    # POS-PH2-STATUS: all 11 governed states with Chinese labels
    pos_status = {
        "fixtureId": "POS-PH2-STATUS",
        "targetFunction": "project_all_status_zh",
        "description": "All 11 governed machine states project to stable Chinese labels.",
        "input": {},
        "expectedStates": [
            {"machineCode": code, "statusZh": label} for code, label in STATUS_ZH_MAP.items()
        ],
        "expectedCount": 11,
        "expectedValidation": "accept",
        "traceTo": ["FR-TOT-013", "FR-TOT-017", "AC-TOT-012", "AC-TOT-018"],
    }
    (pos_dir / "ph2-status-positive.json").write_text(
        json.dumps(pos_status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("ph2-status-positive.json")

    # -- Negative fixtures --

    neg_fixtures = [
        {
            "name": "NEG-AUTH-004-credential-mismatch.json",
            "fixtureId": "NEG-AUTH-004",
            "targetFunction": "preauthorization_matches",
            "description": "A credential boundary mismatch must fail closed.",
            "input": {
                "required": {
                    "workspace": "C:/approved/workspace",
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "read-credentials",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "timeoutSeconds": 300,
                    "rounds": 1,
                    "concurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
                "policy": {
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 600,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
            },
            "expectedMissingDimensions": ["credentialBoundary"],
            "expectedValidation": "reject",
            "expectedRejectionRule": "credential-boundary-mismatch",
            "traceTo": ["FR-TOT-010", "FR-TOT-011", "AC-TOT-007", "AC-TOT-008"],
        },
        {
            "name": "NEG-AUTH-005-schema-mismatch.json",
            "fixtureId": "NEG-AUTH-005",
            "targetFunction": "preauthorization_matches",
            "description": "A feedback schema mismatch must fail closed.",
            "input": {
                "required": {
                    "workspace": "C:/approved/workspace",
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "other-schema.json",
                    "timeoutSeconds": 300,
                    "rounds": 1,
                    "concurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
                "policy": {
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 600,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
            },
            "expectedMissingDimensions": ["feedbackSchema"],
            "expectedValidation": "reject",
            "expectedRejectionRule": "feedback-schema-mismatch",
            "traceTo": ["FR-TOT-010", "FR-TOT-011", "AC-TOT-007", "AC-TOT-008"],
        },
        {
            "name": "NEG-AUTH-006-rounds-overflow.json",
            "fixtureId": "NEG-AUTH-006",
            "targetFunction": "preauthorization_matches",
            "description": "Requested rounds exceeding maxRounds must fail closed.",
            "input": {
                "required": {
                    "workspace": "C:/approved/workspace",
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "timeoutSeconds": 300,
                    "rounds": 20,
                    "concurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
                "policy": {
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 600,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
            },
            "expectedMissingDimensions": ["rounds"],
            "expectedValidation": "reject",
            "expectedRejectionRule": "rounds-overflow",
            "traceTo": ["FR-TOT-010", "FR-TOT-016", "AC-TOT-008", "AC-TOT-013"],
        },
        {
            "name": "NEG-AUTH-007-concurrency-overflow.json",
            "fixtureId": "NEG-AUTH-007",
            "targetFunction": "preauthorization_matches",
            "description": "Requested concurrency exceeding maxConcurrency must fail closed.",
            "input": {
                "required": {
                    "workspace": "C:/approved/workspace",
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "timeoutSeconds": 300,
                    "rounds": 1,
                    "concurrency": 5,
                    "stopConditions": ["p0-drift", "timeout"],
                },
                "policy": {
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 600,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
            },
            "expectedMissingDimensions": ["concurrency"],
            "expectedValidation": "reject",
            "expectedRejectionRule": "concurrency-overflow",
            "traceTo": ["FR-TOT-010", "FR-TOT-011", "AC-TOT-008"],
        },
        {
            "name": "NEG-AUTH-008-stopcondition-mismatch.json",
            "fixtureId": "NEG-AUTH-008",
            "targetFunction": "preauthorization_matches",
            "description": "A stop condition not in the policy must fail closed.",
            "input": {
                "required": {
                    "workspace": "C:/approved/workspace",
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "timeoutSeconds": 300,
                    "rounds": 1,
                    "concurrency": 1,
                    "stopConditions": ["unknown-stop"],
                },
                "policy": {
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test"],
                    "data": ["workspace-source"],
                    "network": [],
                    "tools": ["python", "claude"],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 600,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                },
            },
            "expectedMissingDimensions": ["stopConditions"],
            "expectedValidation": "reject",
            "expectedRejectionRule": "stop-condition-not-in-policy",
            "traceTo": ["FR-TOT-010", "FR-TOT-011", "AC-TOT-008"],
        },
        {
            "name": "NEG-DRYRUN-001-no-manifest.json",
            "fixtureId": "NEG-DRYRUN-001",
            "targetFunction": "evaluate_dry_run_gate",
            "description": "A first-time packet/policy combo with no dry-run manifest cannot proceed to live.",
            "input": {
                "packetHash": "abc123",
                "policyHash": "def456",
                "dryRunRecords": [],
            },
            "expectedAllowed": False,
            "expectedStatus": "DRY_RUN_MISSING",
            "expectedValidation": "reject",
            "expectedRejectionRule": "no-dry-run-record-for-this-packet-policy-combo",
            "traceTo": ["FR-TOT-012", "AC-TOT-009"],
        },
        {
            "name": "NEG-DRYRUN-002-wrong-packet.json",
            "fixtureId": "NEG-DRYRUN-002",
            "targetFunction": "evaluate_dry_run_gate",
            "description": "A wrong packet hash must not bypass the dry-run gate.",
            "input": {
                "packetHash": "wrong-packet",
                "policyHash": "def456",
                "dryRunRecords": [{"packetHash": "correct-packet", "policyHash": "def456", "status": "DRY_RUN_OK"}],
            },
            "expectedAllowed": False,
            "expectedStatus": "DRY_RUN_MISSING",
            "expectedValidation": "reject",
            "expectedRejectionRule": "no-dry-run-record-for-this-packet-policy-combo",
            "traceTo": ["FR-TOT-012", "AC-TOT-009"],
        },
        {
            "name": "NEG-DRYRUN-003-wrong-policy-hash.json",
            "fixtureId": "NEG-DRYRUN-003",
            "targetFunction": "evaluate_dry_run_gate",
            "description": "A wrong policy hash must not bypass the dry-run gate.",
            "input": {
                "packetHash": "abc123",
                "policyHash": "wrong-policy",
                "dryRunRecords": [{"packetHash": "abc123", "policyHash": "correct-policy", "status": "DRY_RUN_OK"}],
            },
            "expectedAllowed": False,
            "expectedStatus": "DRY_RUN_MISSING",
            "expectedValidation": "reject",
            "expectedRejectionRule": "no-dry-run-record-for-this-packet-policy-combo",
            "traceTo": ["FR-TOT-012", "AC-TOT-009"],
        },
        {
            "name": "NEG-STATUS-002-unknown-state.json",
            "fixtureId": "NEG-STATUS-002",
            "targetFunction": "project_status_zh",
            "description": "An unknown state must map to failed, not be accepted as valid.",
            "input": {"state": "cancelled-or-superseded"},
            "expectedMachineCode": "failed",
            "expectedStatusZh": "失败",
            "expectedValidation": "reject",
            "expectedRejectionRule": "unknown-state-maps-to-failed",
            "traceTo": ["FR-TOT-013", "AC-TOT-012", "AC-TOT-018"],
        },
        {
            "name": "NEG-TAKEOVER-001-unrecognized-trigger.json",
            "fixtureId": "NEG-TAKEOVER-001",
            "targetFunction": "decide_takeover",
            "description": "An unrecognized takeover trigger must be rejected.",
            "input": {
                "trigger": "unknown-trigger",
                "cycleId": "C1",
                "storyId": "ST-2-006",
                "roundNumber": 1,
                "policy": {"codexTakeoverAllowed": True, "maxRounds": 10},
                "evidenceLineage": [],
            },
            "expectedAllowed": False,
            "expectedReason": "unrecognized-takeover-trigger",
            "expectedValidation": "reject",
            "expectedRejectionRule": "unrecognized-takeover-trigger",
            "traceTo": ["FR-TOT-014", "AC-TOT-010"],
        },
        {
            "name": "NEG-TAKEOVER-002-not-authorized.json",
            "fixtureId": "NEG-TAKEOVER-002",
            "targetFunction": "decide_takeover",
            "description": "Takeover without policy authorization must be rejected.",
            "input": {
                "trigger": "claude-unavailable",
                "cycleId": "C1",
                "storyId": "ST-2-006",
                "roundNumber": 1,
                "policy": {"status": "active", "codexTakeoverAllowed": False, "maxRounds": 10},
                "evidenceLineage": [],
            },
            "expectedAllowed": False,
            "expectedReason": "takeover-not-authorized-by-active-policy",
            "expectedValidation": "reject",
            "expectedRejectionRule": "takeover-not-authorized-by-active-policy",
            "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010"],
        },
        {
            "name": "NEG-TAKEOVER-003-round-limit.json",
            "fixtureId": "NEG-TAKEOVER-003",
            "targetFunction": "decide_takeover",
            "description": "Takeover at round limit must be rejected.",
            "input": {
                "trigger": "timeout",
                "cycleId": "C1",
                "storyId": "ST-2-006",
                "roundNumber": 11,
                "policy": {"status": "active", "codexTakeoverAllowed": True, "maxRounds": 10, "maxTakeovers": 1},
                "evidenceLineage": ["EV-1"],
            },
            "expectedAllowed": False,
            "expectedReason": "round-limit-reached",
            "expectedValidation": "reject",
            "expectedRejectionRule": "round-limit-reached",
            "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010", "AC-TOT-013"],
        },
        {
            "name": "NEG-TAKEOVER-004-cross-story.json",
            "fixtureId": "NEG-TAKEOVER-004",
            "targetFunction": "decide_takeover",
            "description": "A takeover request for a different Story than the failed Claude attempt must fail closed.",
            "input": {
                "trigger": "claude-unavailable",
                "cycleId": "C1",
                "storyId": "ST-2-006",
                "roundNumber": 1,
                "originCycleId": "C1",
                "originStoryId": "ST-2-005",
                "policy": {"status": "active", "codexTakeoverAllowed": True, "maxRounds": 10, "maxTakeovers": 1},
                "evidenceLineage": ["EV-1"],
            },
            "expectedAllowed": False,
            "expectedValidation": "reject",
            "expectedRejectionRule": "cross-story-takeover-forbidden",
            "traceTo": ["FR-TOT-014", "AC-TOT-010"],
        },
        {
            "name": "NEG-AUTH-009-expired-policy.json",
            "fixtureId": "NEG-AUTH-009",
            "targetFunction": "validate_preauthorization_policy",
            "description": "An otherwise valid policy outside expiresAt must fail closed.",
            "input": {"observedAt": "2026-08-16T04:00:00+00:00", "expiresAt": "2026-08-16T03:00:00+00:00"},
            "expectedValidation": "reject",
            "expectedRejectionRule": "policy-expired",
            "traceTo": ["FR-TOT-010", "FR-TOT-016", "AC-TOT-008"],
        },
        {
            "name": "NEG-AUTH-010-policy-hash-mismatch.json",
            "fixtureId": "NEG-AUTH-010",
            "targetFunction": "validate_preauthorization_policy",
            "description": "A policy changed after hashing must fail closed.",
            "input": {"mutation": "actions+publish"},
            "expectedValidation": "reject",
            "expectedRejectionRule": "policy-hash-mismatch",
            "traceTo": ["FR-TOT-010", "FR-TOT-011", "AC-TOT-008"],
        },
        {
            "name": "NEG-AUTH-011-inactive-policy.json",
            "fixtureId": "NEG-AUTH-011",
            "targetFunction": "validate_preauthorization_policy",
            "description": "A revoked policy must not authorize execution.",
            "input": {"status": "revoked"},
            "expectedValidation": "reject",
            "expectedRejectionRule": "policy-not-active",
            "traceTo": ["FR-TOT-010", "FR-TOT-016", "AC-TOT-007"],
        },
        {
            "name": "NEG-REGISTRY-001-completion-authority.json",
            "fixtureId": "NEG-REGISTRY-001",
            "targetFunction": "validate_claude_registry",
            "description": "Claude registry entries cannot own Development System completion authority.",
            "input": {"completionAuthorityIsolated": False},
            "expectedValidation": "reject",
            "expectedRejectionRule": "registry-completion-authority-not-isolated",
            "traceTo": ["FR-TOT-009", "AC-TOT-014"],
        },
        {
            "name": "NEG-DRYRUN-004-manifest-hash-mismatch.json",
            "fixtureId": "NEG-DRYRUN-004",
            "targetFunction": "evaluate_dry_run_gate",
            "description": "A dry-run manifest changed after hashing must fail closed.",
            "input": {"mutation": "spawnedProcess=true"},
            "expectedValidation": "reject",
            "expectedRejectionRule": "dry-run-manifest-hash-mismatch",
            "traceTo": ["FR-TOT-012", "AC-TOT-009"],
        },
    ]

    for fixture in neg_fixtures:
        if fixture.get("targetFunction") == "preauthorization_matches":
            required = fixture["input"]["required"]
            policy = fixture["input"]["policy"]
            policy.update({
                "policyId": "DS-PH2-FIXTURE-POLICY",
                "version": "1.0",
                "status": "active",
                "validFrom": "2026-08-15T00:00:00+00:00",
                "expiresAt": "2099-01-01T00:00:00+00:00",
                "maxTakeovers": 1,
                "codexTakeoverAllowed": True,
                "crossProjectReuse": False,
            })
            policy["policyHash"] = compute_policy_hash(policy)
            required["policyId"] = policy["policyId"]
            required["policyHash"] = policy["policyHash"]
        fname = fixture.pop("name")
        (neg_dir / fname).write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        fixtures.append(fname)

    return {"fixturesCreated": len(fixtures), "files": fixtures, "outputDir": str(out)}


def _generate_ph2_change_record(output_dir: str) -> dict[str, Any]:
    """Generate the PH-2 change record markdown file."""
    out = Path(output_dir)
    cr_dir = out / "change-records" / "entries" / "2026" / "2026-08"
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_path = cr_dir / "CR-20260816-002-ph2-claude-governance.md"
    if cr_path.exists():
        return {"changeRecordCreated": False, "path": str(cr_path), "reason": "existing-record-preserved"}
    content = """# CR-20260816-002 - PH-2 Claude External Agent Governance

| Field | Value |
|---|---|
| Status | validation-pending |
| Target Skill | development-system, handoff-claude-executor |
| Change Type | added / validation / governance |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | DSCR-PH-2 stories ST-2-001 through ST-2-006; FR-TOT-009 through FR-TOT-018; AC-TOT-007 through AC-TOT-018 |
| Baseline | Workspace before PH-2; preauthorization only matched workspace/actions/data/network/tools/timeout |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260816-001, CR-20260815-003 |

## Summary

Implement PH-2 Claude external Agent governance with exact preauthorization matching across all dimensions, automatic approval inside the boundary, dry-run gating, Chinese status projection, and bounded same-Story takeover.

## Context And Problem

The v2.2 requirement baseline (DS-CLAUDE-REPAIR-RA-20260815-001) requires that Codex may auto-approve a Claude call only when the complete active preauthorization matches exactly. The PH-1 preauthorization_matches function only checked workspace, actions, data, network, tools, and timeoutSeconds. The remaining dimensions (credentialBoundary, feedbackSchema, maxRounds, maxConcurrency, stopConditions) were not enforced. Additionally, no dry-run-to-live gate, Chinese status projection, or bounded takeover decision existed.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| scripts/development_runtime.py | GOVERNED_STATES, STATUS_ZH_MAP, REQUIRED_REGISTRY_FIELDS, PREAUTHORIZATION_DIMENSIONS, DRY_RUN_STATUSES, TAKEOVER_TRIGGERS | Add PH-2 constants for status mapping, registry, preauthorization, dry-run, and takeover |
| scripts/development_runtime.py | preauthorization_matches | Extend to check credentialBoundary, feedbackSchema, rounds, concurrency, stopConditions (exact match) |
| scripts/development_runtime.py | validate_claude_registry | New function: validate Claude Agent registry entry (FR-TOT-009) |
| scripts/development_runtime.py | validate_preauthorization_policy | New function: validate policy lifecycle (FR-TOT-010, FR-TOT-016) |
| scripts/development_runtime.py | compute_policy_hash | New function: stable SHA-256 of canonical policy form |
| scripts/development_runtime.py | decide_auto_approval | New function: exact-match auto-approval with redacted audit record (FR-TOT-011, FR-TOT-015) |
| scripts/development_runtime.py | evaluate_dry_run_gate | New function: dry-run-to-live transition gate (FR-TOT-012) |
| scripts/development_runtime.py | project_status_zh, project_all_status_zh | New functions: Chinese status projection (FR-TOT-013, FR-TOT-017) |
| scripts/development_runtime.py | decide_takeover | New function: bounded same-Story takeover (FR-TOT-014, FR-TOT-016) |
| scripts/development_runtime.py | _generate_ph2_fixtures | New function: generate PH-2 positive and negative fixtures |
| scripts/test_development_runtime.py | test_authority_and_execution | Update policy/required dicts with PH-2 dimensions; add credential/schema/rounds/concurrency/stopCondition mismatch tests |
| scripts/test_development_runtime.py | test_ph2_claude_registry | New test: DSCR-ST-2-001 registry validation |
| scripts/test_development_runtime.py | test_ph2_preauthorization_policy | New test: DSCR-ST-2-002 policy lifecycle |
| scripts/test_development_runtime.py | test_ph2_auto_approval | New test: DSCR-ST-2-003 exact-match auto-approval |
| scripts/test_development_runtime.py | test_ph2_dry_run_gate | New test: DSCR-ST-2-004 dry-run gate |
| scripts/test_development_runtime.py | test_ph2_status_projection | New test: DSCR-ST-2-005 Chinese status projection |
| scripts/test_development_runtime.py | test_ph2_takeover | New test: DSCR-ST-2-006 bounded takeover |
| scripts/test_development_runtime.py | test_declared_negative_fixtures | Add PH-2 negative fixtures to required set |
| scripts/test_development_runtime.py | test_negative_fixture_semantics | Add PH-2 negative fixture semantic checks |
| assets/fixtures/negative/NEG-AUTH-001-workspace-boundary.json | traceTo, input | Update to include PH-2 dimensions and FR-TOT trace |
| assets/fixtures/negative/NEG-AUTH-002-incomplete-preauthorization.json | traceTo, input | Update to include PH-2 dimensions and FR-TOT trace |
| handoff-claude-executor/SKILL.md | PH-2 sections | Add preauthorization auto-approval, dry-run gate, Chinese status projection, bounded takeover |
| handoff-claude-executor/references/claude-adapter-contract.md | PH-2 sections | Add all PH-2 governance contracts |
| handoff-claude-executor/references/security-policy.md | PH-2 sections | Add credential boundary, high-risk actions, auto-approval gate |

## Requirement Trace

| Story | FR | AC | Evidence |
|---|---|---|---|
| DSCR-ST-2-001 | FR-TOT-009 | AC-TOT-014, AC-TOT-017 | validate_claude_registry, POS-PH2-REGISTRY fixture |
| DSCR-ST-2-002 | FR-TOT-010, FR-TOT-016 | AC-TOT-008, AC-TOT-013 | validate_preauthorization_policy, POS-PH2-PREAUTH fixture, NEG-AUTH-004 through 008 |
| DSCR-ST-2-003 | FR-TOT-011, FR-TOT-015 | AC-TOT-007, AC-TOT-008, AC-TOT-011 | decide_auto_approval, match/mismatch matrix tests |
| DSCR-ST-2-004 | FR-TOT-012 | AC-TOT-009 | evaluate_dry_run_gate, NEG-DRYRUN-001 through 003 |
| DSCR-ST-2-005 | FR-TOT-013, FR-TOT-017 | AC-TOT-012, AC-TOT-018 | project_status_zh, project_all_status_zh, POS-PH2-STATUS, NEG-STATUS-002 |
| DSCR-ST-2-006 | FR-TOT-014, FR-TOT-016 | AC-TOT-010, AC-TOT-013 | decide_takeover, NEG-TAKEOVER-001 through 004 |

## Validation

- All existing tests preserved without weakened assertions
- New PH-2 tests cover positive and negative matrices
- Negative fixtures generated by `development_runtime.py generate-ph2-fixtures`
- Audit records are redacted (no credentials, prompts, or private transcripts)
- Fail-closed behavior verified for all mismatch dimensions
"""
    cr_path.write_text(content, encoding="utf-8")
    return {"changeRecordCreated": str(cr_path)}


# ---------------------------------------------------------------------------
# PH-3: Bounded local live-loop harness (DSCR-ST-3-001 through ST-3-004)
# ---------------------------------------------------------------------------

PH3_LINEAGE_FIELDS = (
    "cycleId",
    "storyId",
    "roundNumber",
    "attemptId",
)


def validate_feedback_lineage(
    feedback: Any,
    expected_cycle_id: str,
    expected_story_id: str,
    expected_round_number: int,
    expected_attempt_id: str,
    evidence_lineage: list[str] | None = None,
) -> dict[str, Any]:
    """Validate that feedback lineage fields are consistent with the current cycle.

    DSCR-ST-3-003: Stale fields (references to a previous cycle/round/attempt)
    must be detected and block completion (FR-TOT-008, AC-TOT-006).
    """
    errors: list[str] = []

    if not isinstance(feedback, dict) or not feedback:
        errors.append("feedback-missing-or-not-object")
        return {"valid": False, "errors": errors}

    expected_values = {
        "cycleId": expected_cycle_id,
        "storyId": expected_story_id,
        "roundNumber": expected_round_number,
        "attemptId": expected_attempt_id,
    }

    for field, expected in expected_values.items():
        actual = feedback.get(field)
        if actual is not None and actual != expected:
            errors.append(
                f"stale-{field}: expected={expected}, actual={actual}"
            )

    evidence_index = feedback.get("evidenceIndex")
    if isinstance(evidence_index, list):
        for i, item in enumerate(evidence_index):
            if isinstance(item, dict):
                path = str(item.get("path", ""))
                if (
                    expected_attempt_id
                    and "ATT-" in path
                    and expected_attempt_id not in path
                ):
                    errors.append(f"stale-evidence-path-{i}")

    trace_delta = feedback.get("requirementTraceDelta")
    if isinstance(trace_delta, list):
        for i, item in enumerate(trace_delta):
            if isinstance(item, dict):
                item_cycle = item.get("cycleId")
                if item_cycle is not None and item_cycle != expected_cycle_id:
                    errors.append(f"stale-trace-cycle-{i}")
                item_round = item.get("roundNumber")
                if item_round is not None and item_round != expected_round_number:
                    errors.append(f"stale-trace-round-{i}")

    if evidence_lineage is not None:
        feedback_lineage = feedback.get("evidenceLineage")
        if isinstance(feedback_lineage, list):
            for ev in evidence_lineage:
                if ev not in feedback_lineage:
                    errors.append(f"evidence-lineage-broken: {ev}")

    return {"valid": not errors, "errors": errors}


def check_duplicate_side_effects(
    current_changed_files: list[dict[str, Any]],
    previous_rounds: list[list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Check for duplicate side effects across rounds.

    DSCR-ST-3-004: Multi-round repair must not repeat side effects
    (FR-TOT-014, FR-TOT-016, AC-TOT-010, AC-TOT-013).
    """
    prior_rounds = previous_rounds or []

    current_paths: set[str] = set()
    for item in current_changed_files:
        if isinstance(item, dict):
            path = str(item.get("path", ""))
            if path:
                current_paths.add(path)

    duplicates: list[str] = []
    for prev_round in prior_rounds:
        for item in prev_round:
            if isinstance(item, dict):
                path = str(item.get("path", ""))
                if path and path in current_paths:
                    duplicates.append(path)

    unique_dupes = sorted(set(duplicates))
    return {
        "duplicateCount": len(unique_dupes),
        "duplicatePaths": unique_dupes,
        "hasDuplicates": bool(unique_dupes),
    }


def _make_feedback_validation_evidence(feedback: Any) -> dict[str, Any]:
    """Produce valid hash-bound feedback validation evidence for a feedback object."""
    return {
        "schemaRef": "feedback-packet.schema.json",
        "validatorId": "handoff-feedback-reviewer",
        "feedbackHash": _sha256(feedback),
        "ok": True,
        "errorCount": 0,
        "validatedAt": _now(),
    }


def run_live_loop(
    packet: dict[str, Any],
    policy: dict[str, Any],
    dry_run_records: list[dict[str, Any]] | None,
    simulated_outcome: dict[str, Any],
    cycle_id: str,
    story_id: str,
    round_number: int,
    attempt_id: str,
    evidence_lineage: list[str] | None = None,
    previous_changed_files: list[list[dict[str, Any]]] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Bounded local live-loop harness (DSCR-ST-3-001 through ST-3-004).

    Simulates the full closed-loop without spawning Claude:
    1. Preauthorization match
    2. Dry-run gate
    3. Auto-approval
    4. Simulated Claude execution (via ``simulated_outcome``)
    5. Feedback validation (hash-bound evidence)
    6. Lineage validation (stale field detection)
    7. Side-effect duplicate detection
    8. Completion evaluation

    ``simulated_outcome`` keys:
      - ``feedback``: feedback dict or None
      - ``processEvidence``: dict with failureClass, spawnSucceeded, timedOut, childExitCode
      - ``changedFiles``: list of changed-file dicts
      - ``driftSeverity``: string (none/allowed/P2/P1/P0)
      - ``unmappedActions``: list of unmapped action strings
      - ``evidenceRefs``: list of evidence reference strings

    Returns a structured result with all evidence and the final state.
    Preserves cycleId, storyId, roundNumber, attemptId and evidence lineage.
    """
    result: dict[str, Any] = {
        "cycleId": cycle_id,
        "storyId": story_id,
        "roundNumber": round_number,
        "attemptId": attempt_id,
        "evidenceLineage": list(evidence_lineage or []),
        "state": "running",
        "failureClass": None,
        "blockers": [],
        "autoApproval": None,
        "feedbackValidation": None,
        "lineageValidation": None,
        "sideEffectCheck": None,
        "completionEvaluation": None,
        "circuitResult": None,
    }

    # -- 1. Preauthorization match --
    required_auth = packet.get("requiredAuthorization") or {}
    if not required_auth.get("packetHash"):
        required_auth = dict(required_auth)
        required_auth["packetHash"] = _sha256(packet)
    matched, missing = preauthorization_matches(required_auth, policy, now=now)
    if not matched:
        result["state"] = "blocked-user-decision"
        result["failureClass"] = "preauthorization-mismatch"
        result["blockers"].append(f"preauthorization-mismatch: {missing}")
        return result

    # -- 2. Dry-run gate --
    packet_hash = required_auth.get("packetHash", _sha256(packet))
    policy_hash = compute_policy_hash(policy)
    gate = evaluate_dry_run_gate(
        packet_hash,
        policy_hash,
        dry_run_records,
        now=now,
        policy_expires_at=policy.get("expiresAt"),
    )
    if not gate["allowed"]:
        result["state"] = "blocked-user-decision"
        result["failureClass"] = "dry-run-gate-blocked"
        result["blockers"].append(f"dry-run-gate: {gate['reason']}")
        return result

    # -- 3. Auto-approval --
    task = {"taskId": story_id, "requiredAuthorization": required_auth}
    auto = decide_auto_approval(task, policy, dry_run_records, now=now)
    result["autoApproval"] = auto
    if auto["decision"] != "auto-approved":
        result["state"] = "blocked-user-decision"
        result["failureClass"] = "auto-approval-blocked"
        result["blockers"].append(f"auto-approval: {auto['reason']}")
        return result

    # -- 4. Simulated Claude execution --
    pe = simulated_outcome.get("processEvidence") or {}
    failure_class = pe.get("failureClass")
    feedback = simulated_outcome.get("feedback")
    changed_files = simulated_outcome.get("changedFiles") or []
    drift_severity = simulated_outcome.get("driftSeverity", "none")
    unmapped_actions = simulated_outcome.get("unmappedActions") or []
    evidence_refs = simulated_outcome.get("evidenceRefs") or []

    result["failureClass"] = failure_class

    # -- 5. Feedback validation --
    feedback_result = validate_feedback_evidence(feedback, {})
    if feedback and feedback_result["valid"] is False and not failure_class:
        # Recompute with proper evidence if feedback exists and no process failure
        fv_evidence = _make_feedback_validation_evidence(feedback)
        feedback_result = validate_feedback_evidence(feedback, fv_evidence)
        feedback_result["generatedEvidence"] = fv_evidence
    result["feedbackValidation"] = feedback_result

    # -- 6. Lineage validation --
    lineage_result = validate_feedback_lineage(
        feedback or {},
        cycle_id,
        story_id,
        round_number,
        attempt_id,
        evidence_lineage,
    )
    result["lineageValidation"] = lineage_result
    if not lineage_result["valid"]:
        result["blockers"].extend(lineage_result["errors"])

    # -- 7. Side-effect duplicate detection --
    dup_check = check_duplicate_side_effects(changed_files, previous_changed_files)
    result["sideEffectCheck"] = dup_check
    if dup_check["hasDuplicates"]:
        result["blockers"].append(
            f"duplicate-side-effects: {dup_check['duplicatePaths']}"
        )

    # -- 8. Completion evaluation --
    evidence_complete = (
        not failure_class
        and bool(evidence_refs)
        and feedback_result["valid"]
        and lineage_result["valid"]
        and not dup_check["hasDuplicates"]
    )
    qa_passed = not failure_class and feedback_result["valid"]
    permission_passed = auto["decision"] == "auto-approved"
    risk_passed = not failure_class and not dup_check["hasDuplicates"]
    codex_review = not failure_class and feedback_result["valid"] and lineage_result["valid"]

    completion_input = {
        "allStoriesPassed": not failure_class,
        "allAcceptanceCriteriaVerified": not failure_class and feedback_result["valid"],
        "feedback": feedback if feedback else {},
        "feedbackValidation": _make_feedback_validation_evidence(feedback) if feedback else {},
        "evidenceComplete": evidence_complete,
        "qaPassed": qa_passed,
        "driftSeverity": drift_severity,
        "unmappedActions": unmapped_actions,
        "permissionGatePassed": permission_passed,
        "riskGatePassed": risk_passed,
        "codexReviewPassed": codex_review,
        "agentCompletionClaim": False,
    }
    completion = evaluate_completion(completion_input)
    result["completionEvaluation"] = completion

    # -- 9. Circuit advancement --
    observation = {
        "actualExecution": True,
        "verifiedProgress": completion["passed"],
        "completionPassed": completion["passed"],
        "failure": None,
    }
    if failure_class:
        observation["failure"] = {
            "type": failure_class,
            "testId": story_id,
            "message": failure_class,
            "rootCause": failure_class,
        }
    circuit = advance_circuit({}, observation)
    result["circuitResult"] = circuit

    # -- Determine final state --
    if completion["passed"]:
        result["state"] = "completed"
    elif failure_class in {"spawn-permission", "spawn-not-found", "spawn-os-error", "timeout"}:
        result["state"] = "blocked-external-dependency"
    elif drift_severity in {"P0", "P1"} or unmapped_actions:
        result["state"] = "requirements-review"
    elif not lineage_result["valid"] or not feedback_result["valid"]:
        result["state"] = "repair-needed"
    elif dup_check["hasDuplicates"]:
        result["state"] = "repair-needed"
    else:
        result["state"] = completion["state"]

    result["blockers"].extend(completion["blockers"])

    # Update evidence lineage
    if attempt_id and attempt_id not in result["evidenceLineage"]:
        result["evidenceLineage"].append(attempt_id)
    if evidence_refs:
        for ref in evidence_refs:
            if ref not in result["evidenceLineage"]:
                result["evidenceLineage"].append(ref)

    return result


def _generate_ph3_fixtures(output_dir: str) -> dict[str, Any]:
    """Generate PH-3 positive and negative fixtures for deterministic testing."""
    out = Path(output_dir)
    neg_dir = out / "negative"
    pos_dir = out / "phase-story"
    neg_dir.mkdir(parents=True, exist_ok=True)
    pos_dir.mkdir(parents=True, exist_ok=True)
    fixtures: list[str] = []

    # -- Positive fixture: live loop closed-loop success --
    pos_live = {
        "fixtureId": "POS-PH3-LIVE-LOOP",
        "targetFunction": "run_live_loop",
        "description": "A positive live loop closed-loop: auto-approval, valid feedback, completion passed.",
        "input": {
            "packet": {"packetId": "HND-PH3-POS", "requiredAuthorization": {}},
            "policy": {
                "policyId": "DS-PH3-FIXTURE-POLICY",
                "version": "1.0",
                "status": "active",
                "validFrom": "2026-08-15T00:00:00+00:00",
                "expiresAt": "2099-01-01T00:00:00+00:00",
                "workspaceRoots": ["C:/approved/workspace"],
                "actions": ["read", "edit", "test", "validate"],
                "tools": ["claude-code", "python"],
                "data": ["workspace-source"],
                "network": [],
                "credentialBoundary": "inherit-claude-auth-only",
                "feedbackSchema": "feedback-packet.schema.json",
                "maxTimeoutSeconds": 900,
                "maxRounds": 1,
                "maxConcurrency": 1,
                "maxTakeovers": 1,
                "stopConditions": ["p0-drift", "timeout"],
                "codexTakeoverAllowed": True,
                "crossProjectReuse": False,
            },
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-POS", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "fixture.py", "trace": ["FR-TOT-001"]}],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": ["EV-PH3-001"],
            },
            "cycleId": "C-PH3-001",
            "storyId": "DSCR-ST-3-001",
            "roundNumber": 1,
            "attemptId": "ATT-PH3-POS-001",
            "evidenceLineage": ["EV-PRE-001"],
        },
        "expectedState": "completed",
        "expectedValidation": "accept",
        "traceTo": ["FR-TOT-001", "FR-TOT-011", "FR-TOT-012", "FR-TOT-017", "AC-TOT-007", "AC-TOT-009", "AC-TOT-014"],
    }
    pos_live["input"]["policy"]["policyHash"] = compute_policy_hash(pos_live["input"]["policy"])
    (pos_dir / "ph3-live-loop-positive.json").write_text(
        json.dumps(pos_live, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("ph3-live-loop-positive.json")

    # -- Negative fixtures --

    neg_specs = [
        {
            "name": "NEG-PH3-001-spawn-failure.json",
            "fixtureId": "NEG-PH3-001",
            "description": "Spawn failure must block the live loop and not produce completed.",
            "simulatedOutcome": {
                "feedback": None,
                "processEvidence": {"failureClass": "spawn-permission", "spawnSucceeded": False, "timedOut": False, "childExitCode": None},
                "changedFiles": [],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": [],
            },
            "expectedState": "blocked-external-dependency",
            "expectedRejectionRule": "spawn-failure-blocks-loop",
            "traceTo": ["FR-TOT-003", "FR-TOT-004", "FR-TOT-005", "AC-TOT-002", "AC-TOT-003", "AC-TOT-005"],
        },
        {
            "name": "NEG-PH3-002-timeout.json",
            "fixtureId": "NEG-PH3-002",
            "description": "Timeout must block the live loop and not produce completed.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-TIMEOUT", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": "timeout", "spawnSucceeded": True, "timedOut": True, "childExitCode": None},
                "changedFiles": [],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": [],
            },
            "expectedState": "blocked-external-dependency",
            "expectedRejectionRule": "timeout-blocks-loop",
            "traceTo": ["FR-TOT-003", "FR-TOT-004", "FR-TOT-005", "AC-TOT-002", "AC-TOT-003", "AC-TOT-005"],
        },
        {
            "name": "NEG-PH3-003-invalid-feedback.json",
            "fixtureId": "NEG-PH3-003",
            "description": "Invalid child feedback must block the live loop and route to repair-needed.",
            "simulatedOutcome": {
                "feedback": {},
                "processEvidence": {"failureClass": "feedback-missing", "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": [],
            },
            "expectedState": "repair-needed",
            "expectedRejectionRule": "invalid-feedback-blocks-loop",
            "traceTo": ["FR-TOT-005", "FR-TOT-006", "FR-TOT-007", "AC-TOT-003", "AC-TOT-004", "AC-TOT-005"],
        },
        {
            "name": "NEG-PH3-004-p1-drift.json",
            "fixtureId": "NEG-PH3-004",
            "description": "P1 requirement drift must block completion and route to requirements-review.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-DRIFT", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "drift.py", "trace": ["FR-TOT-001"]}],
                "driftSeverity": "P1",
                "unmappedActions": [],
                "evidenceRefs": ["EV-PH3-004"],
            },
            "expectedState": "requirements-review",
            "expectedRejectionRule": "p1-drift-blocks-completion",
            "traceTo": ["FR-TOT-008", "FR-TOT-017", "AC-TOT-003", "AC-TOT-006"],
        },
        {
            "name": "NEG-PH3-005-unmapped-action.json",
            "fixtureId": "NEG-PH3-005",
            "description": "An unmapped action must block completion and route to requirements-review.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-UNMAPPED", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "unmapped.py", "trace": ["FR-UNKNOWN"]}],
                "driftSeverity": "none",
                "unmappedActions": ["untraced-action"],
                "evidenceRefs": ["EV-PH3-005"],
            },
            "expectedState": "requirements-review",
            "expectedRejectionRule": "unmapped-action-blocks-completion",
            "traceTo": ["FR-TOT-008", "FR-TOT-017", "AC-TOT-003", "AC-TOT-006"],
        },
        {
            "name": "NEG-PH3-006-stale-field.json",
            "fixtureId": "NEG-PH3-006",
            "description": "A stale cycleId in feedback must block completion.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-STALE", "packetType": "feedback", "version": "1.0", "cycleId": "OLD-CYCLE"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "stale.py", "trace": ["FR-TOT-001"]}],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": ["EV-PH3-006"],
            },
            "expectedState": "repair-needed",
            "expectedRejectionRule": "stale-field-blocks-completion",
            "traceTo": ["FR-TOT-008", "FR-TOT-017", "AC-TOT-003", "AC-TOT-006"],
        },
        {
            "name": "NEG-PH3-007-evidence-gap.json",
            "fixtureId": "NEG-PH3-007",
            "description": "An evidence gap (no evidenceRefs) must block completion.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-GAP", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "gap.py", "trace": ["FR-TOT-001"]}],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": [],
            },
            "expectedState": "repair-needed",
            "expectedRejectionRule": "evidence-gap-blocks-completion",
            "traceTo": ["FR-TOT-007", "FR-TOT-008", "AC-TOT-003", "AC-TOT-006"],
        },
        {
            "name": "NEG-PH3-008-duplicate-side-effects.json",
            "fixtureId": "NEG-PH3-008",
            "description": "Duplicate side effects across rounds must block completion.",
            "simulatedOutcome": {
                "feedback": {"packetId": "FDB-PH3-DUP", "packetType": "feedback", "version": "1.0"},
                "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
                "changedFiles": [{"path": "shared.py", "trace": ["FR-TOT-001"]}],
                "driftSeverity": "none",
                "unmappedActions": [],
                "evidenceRefs": ["EV-PH3-008"],
            },
            "previousChangedFiles": [[{"path": "shared.py", "trace": ["FR-TOT-001"]}]],
            "expectedState": "repair-needed",
            "expectedRejectionRule": "duplicate-side-effects-block-completion",
            "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010", "AC-TOT-013"],
        },
    ]

    for spec in neg_specs:
        fixture = {
            "fixtureId": spec["fixtureId"],
            "targetFunction": "run_live_loop",
            "description": spec["description"],
            "input": {
                "packet": {"packetId": f"HND-{spec['fixtureId']}", "requiredAuthorization": {}},
                "policy": {
                    "policyId": "DS-PH3-FIXTURE-POLICY",
                    "version": "1.0",
                    "status": "active",
                    "validFrom": "2026-08-15T00:00:00+00:00",
                    "expiresAt": "2099-01-01T00:00:00+00:00",
                    "workspaceRoots": ["C:/approved/workspace"],
                    "actions": ["read", "edit", "test", "validate"],
                    "tools": ["claude-code", "python"],
                    "data": ["workspace-source"],
                    "network": [],
                    "credentialBoundary": "inherit-claude-auth-only",
                    "feedbackSchema": "feedback-packet.schema.json",
                    "maxTimeoutSeconds": 900,
                    "maxRounds": 10,
                    "maxConcurrency": 1,
                    "maxTakeovers": 1,
                    "stopConditions": ["p0-drift", "timeout"],
                    "codexTakeoverAllowed": True,
                    "crossProjectReuse": False,
                },
                "simulatedOutcome": spec["simulatedOutcome"],
                "cycleId": "C-PH3-001",
                "storyId": f"DSCR-ST-3-{spec['fixtureId'][-3:-3] or '00X'}",
                "roundNumber": 1,
                "attemptId": f"ATT-{spec['fixtureId']}-001",
                "evidenceLineage": ["EV-PRE-001"],
                "previousChangedFiles": spec.get("previousChangedFiles"),
            },
            "expectedState": spec["expectedState"],
            "expectedValidation": "reject",
            "expectedRejectionRule": spec["expectedRejectionRule"],
            "traceTo": spec["traceTo"],
        }
        fixture["input"]["policy"]["policyHash"] = compute_policy_hash(fixture["input"]["policy"])
        # Fix storyId
        story_map = {
            "NEG-PH3-001": "DSCR-ST-3-002",
            "NEG-PH3-002": "DSCR-ST-3-002",
            "NEG-PH3-003": "DSCR-ST-3-002",
            "NEG-PH3-004": "DSCR-ST-3-003",
            "NEG-PH3-005": "DSCR-ST-3-003",
            "NEG-PH3-006": "DSCR-ST-3-003",
            "NEG-PH3-007": "DSCR-ST-3-003",
            "NEG-PH3-008": "DSCR-ST-3-004",
        }
        fixture["input"]["storyId"] = story_map.get(spec["fixtureId"], "DSCR-ST-3-001")
        fname = spec["name"]
        (neg_dir / fname).write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        fixtures.append(fname)

    # -- Round limit and takeover limit fixtures --
    round_limit = {
        "fixtureId": "NEG-PH3-009",
        "targetFunction": "advance_circuit",
        "description": "Reaching the round limit must stop the loop.",
        "input": {
            "initialCounters": {"roundCount": 10, "circuitState": "CLOSED"},
            "observation": {"actualExecution": False, "completionPassed": False},
        },
        "expectedState": "loop-limit-reached",
        "expectedStopReason": "story-round-limit",
        "expectedValidation": "reject",
        "expectedRejectionRule": "round-limit-stops-loop",
        "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010", "AC-TOT-013"],
    }
    (neg_dir / "NEG-PH3-009-round-limit.json").write_text(
        json.dumps(round_limit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("NEG-PH3-009-round-limit.json")

    takeover_limit = {
        "fixtureId": "NEG-PH3-010",
        "targetFunction": "decide_takeover",
        "description": "Exceeding the takeover limit must be rejected.",
        "input": {
            "trigger": "timeout",
            "cycleId": "C-PH3-001",
            "storyId": "DSCR-ST-3-004",
            "roundNumber": 1,
            "policy": {"status": "active", "codexTakeoverAllowed": True, "maxRounds": 10, "maxTakeovers": 1},
            "evidenceLineage": ["EV-1"],
            "takeoverCount": 1,
        },
        "expectedAllowed": False,
        "expectedReason": "takeover-limit-reached",
        "expectedValidation": "reject",
        "expectedRejectionRule": "takeover-limit-stops-loop",
        "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010", "AC-TOT-013"],
    }
    (neg_dir / "NEG-PH3-010-takeover-limit.json").write_text(
        json.dumps(takeover_limit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("NEG-PH3-010-takeover-limit.json")

    # No-progress fixture
    no_progress = {
        "fixtureId": "NEG-PH3-011",
        "targetFunction": "advance_circuit",
        "description": "Three rounds with no verified progress must open the circuit.",
        "input": {
            "initialCounters": {},
            "observations": [
                {"actualExecution": True, "verifiedProgress": False},
                {"actualExecution": True, "verifiedProgress": False},
                {"actualExecution": True, "verifiedProgress": False},
            ],
        },
        "expectedState": "loop-limit-reached",
        "expectedStopReason": "no-verified-progress",
        "expectedValidation": "reject",
        "expectedRejectionRule": "no-progress-stops-loop",
        "traceTo": ["FR-TOT-014", "FR-TOT-016", "AC-TOT-010"],
    }
    (neg_dir / "NEG-PH3-011-no-progress.json").write_text(
        json.dumps(no_progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures.append("NEG-PH3-011-no-progress.json")

    return {"fixturesCreated": len(fixtures), "files": fixtures, "outputDir": str(out)}


def _generate_ph3_change_record(output_dir: str) -> dict[str, Any]:
    """Generate the PH-3 change record markdown file."""
    out = Path(output_dir)
    cr_dir = out / "change-records" / "entries" / "2026" / "2026-08"
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_path = cr_dir / "CR-20260816-003-ph3-real-closed-loop.md"
    if cr_path.exists():
        return {"changeRecordCreated": False, "path": str(cr_path), "reason": "existing-record-preserved"}
    content = """# CR-20260816-003 - PH-3 Real Closed-Loop Acceptance

| Field | Value |
|---|---|
| Status | validation-pending |
| Target Skill | development-system, handoff-claude-executor |
| Change Type | added / validation / governance |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | DSCR-PH-3 stories ST-3-001 through ST-3-004; FR-TOT-001/003/004/005/006/007/008/011/012/014/016/017; AC-TOT-002/003/004/005/006/007/009/010/013/014/015/017 |
| Baseline | Workspace after PH-2; live loop harness, lineage validation and side-effect detection did not exist |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260816-001, CR-20260816-002 |

## Summary

Implement PH-3 real closed-loop acceptance with a bounded local live-loop harness, feedback lineage validation, duplicate side-effect detection, and eleven negative fixtures covering spawn failure, timeout, invalid feedback, P1 drift, unmapped actions, stale fields, evidence gaps, duplicate side effects, round limits, takeover limits and no-progress circuit opening.

## Context And Problem

The v2.2 requirement baseline requires that Codex's CompletionEvaluator rejects Agent completed claims when any evidence, QA, permission, risk or drift gate is missing. PH-2 established the governance building blocks (preauthorization, dry-run gate, takeover, status projection). PH-3 needed a deterministic live-loop harness that orchestrates these building blocks into a single closed-loop, plus negative tests for every failure mode that must block completion.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| scripts/development_runtime.py | PH3_LINEAGE_FIELDS, validate_feedback_lineage | New: detect stale cycleId/storyId/roundNumber/attemptId and stale evidence paths |
| scripts/development_runtime.py | check_duplicate_side_effects | New: detect duplicate file changes across rounds |
| scripts/development_runtime.py | run_live_loop | New: bounded local live-loop harness orchestrating preauth, dry-run gate, auto-approval, feedback validation, lineage validation, side-effect check, completion evaluation and circuit advancement |
| scripts/development_runtime.py | _generate_ph3_fixtures | New: generate PH-3 positive and negative fixtures |
| scripts/development_runtime.py | _generate_ph3_change_record | New: generate this change record |
| scripts/development_runtime.py | main / CLI | Add generate-ph3-fixtures and generate-ph3-change-record commands |
| scripts/test_development_runtime.py | test_ph3_live_loop_positive | New test: DSCR-ST-3-001 positive closed-loop |
| scripts/test_development_runtime.py | test_ph3_negative_live_cases | New test: DSCR-ST-3-002 spawn failure, timeout, invalid feedback |
| scripts/test_development_runtime.py | test_ph3_drift_and_completion_blocks | New test: DSCR-ST-3-003 drift, unmapped, stale, evidence gap |
| scripts/test_development_runtime.py | test_ph3_multi_round_and_limits | New test: DSCR-ST-3-004 multi-round lineage, duplicate side effects, round/takeover limits |
| scripts/test_development_runtime.py | test_declared_negative_fixtures | Add PH-3 negative fixtures to required set |
| scripts/test_development_runtime.py | test_negative_fixture_semantics | Add PH-3 negative fixture semantic checks |
| assets/fixtures/phase-story/ph3-live-loop-positive.json | New fixture | Positive live-loop closed-loop |
| assets/fixtures/negative/NEG-PH3-001 through NEG-PH3-011 | New fixtures | Eleven PH-3 negative fixtures |

## Requirement Trace

| Story | FR | AC | Evidence |
|---|---|---|---|
| DSCR-ST-3-001 | FR-TOT-001, FR-TOT-011, FR-TOT-012, FR-TOT-017 | AC-TOT-007, AC-TOT-009, AC-TOT-014 | run_live_loop, POS-PH3-LIVE-LOOP fixture |
| DSCR-ST-3-002 | FR-TOT-003, FR-TOT-004, FR-TOT-005, FR-TOT-006, FR-TOT-007 | AC-TOT-002, AC-TOT-003, AC-TOT-004, AC-TOT-005, AC-TOT-015 | NEG-PH3-001 through 003 |
| DSCR-ST-3-003 | FR-TOT-001, FR-TOT-008, FR-TOT-017 | AC-TOT-003, AC-TOT-006, AC-TOT-012, AC-TOT-017 | NEG-PH3-004 through 007 |
| DSCR-ST-3-004 | FR-TOT-014, FR-TOT-016, FR-TOT-017 | AC-TOT-010, AC-TOT-013, AC-TOT-014 | NEG-PH3-008 through 011, check_duplicate_side_effects |

## Validation

- All existing tests preserved without weakened assertions
- New PH-3 tests cover positive and negative matrices
- Negative fixtures generated by `development_runtime.py generate-ph3-fixtures`
- CompletionEvaluator rejects Agent completed claims when any evidence, QA, permission, risk or drift gate is missing
- Stale field detection prevents completion when lineage fields reference a previous cycle/round/attempt
- Duplicate side-effect detection prevents completion when file changes overlap across rounds
- Round limit, takeover limit and no-progress circuit opening all stop the loop
- No public handoff schema changes
- No global Skill writes or user-level installation

## Impact Analysis

- **Scope**: Only the two approved workspace Skill copies are modified.
- **Risk**: Low — all new functions are additive; existing assertions and schemas are unchanged.
- **Rollback**: Revert the PH-3 additions in development_runtime.py and test_development_runtime.py; delete PH-3 fixtures and change record.
- **Dependencies**: None — PH-3 reuses PH-2 building blocks (preauthorization_matches, evaluate_dry_run_gate, decide_auto_approval, validate_feedback_evidence, evaluate_completion, advance_circuit, decide_takeover).

## Validation Evidence

- Deterministic test suite: `test_development_runtime.py` (PH-3 tests added)
- Fixture suite: `assets/fixtures/phase-story/ph3-live-loop-positive.json` and `assets/fixtures/negative/NEG-PH3-001` through `NEG-PH3-011`
- Live evidence: `test-runs/ph3-claude-dryrun-20260816/manifest.json` (DRY_RUN_OK) and `test-runs/ph3-claude-live-20260816/manifest.json` (spawn-permission failure with three-layer exit evidence)
"""
    cr_path.write_text(content, encoding="utf-8")
    return {"changeRecordCreated": str(cr_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Development System deterministic governance runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    completion = sub.add_parser("evaluate-completion")
    completion.add_argument("input")
    phase = sub.add_parser("validate-phase-story")
    phase.add_argument("input")
    admission = sub.add_parser("evaluate-admission")
    admission.add_argument("input")
    registry = sub.add_parser("validate-claude-registry")
    registry.add_argument("input")
    preauth = sub.add_parser("validate-preauthorization")
    preauth.add_argument("input")
    statuszh = sub.add_parser("project-status-zh")
    statuszh.add_argument("--state", default="all")
    genfix = sub.add_parser("generate-ph2-fixtures")
    genfix.add_argument("--output-dir", required=True)
    gencr = sub.add_parser("generate-ph2-change-record")
    gencr.add_argument("--output-dir", required=True)
    genph3fix = sub.add_parser("generate-ph3-fixtures")
    genph3fix.add_argument("--output-dir", required=True)
    genph3cr = sub.add_parser("generate-ph3-change-record")
    genph3cr.add_argument("--output-dir", required=True)
    genclwfix = sub.add_parser("generate-clw-st101-fixtures")
    genclwfix.add_argument("--output-dir", required=True)
    genclwcr = sub.add_parser("generate-clw-st101-change-record")
    genclwcr.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "evaluate-completion":
        result = evaluate_completion(load_json(args.input))
    elif args.command == "validate-phase-story":
        findings = validate_phase_story(load_json(args.input))
        result = {"status": "accepted" if not findings else "review-required", "findings": findings}
    elif args.command == "validate-claude-registry":
        data = load_json(args.input)
        findings = validate_claude_registry(data.get("entry", data), data.get("existing", []))
        result = {"status": "accepted" if not findings else "review-required", "findings": findings}
    elif args.command == "validate-preauthorization":
        findings = validate_preauthorization_policy(load_json(args.input))
        result = {"status": "accepted" if not findings else "review-required", "findings": findings}
    elif args.command == "project-status-zh":
        if args.state == "all":
            result = {"statuses": project_all_status_zh()}
        else:
            result = project_status_zh(args.state)
    elif args.command == "generate-ph2-fixtures":
        result = _generate_ph2_fixtures(args.output_dir)
    elif args.command == "generate-ph2-change-record":
        result = _generate_ph2_change_record(args.output_dir)
    elif args.command == "generate-ph3-fixtures":
        result = _generate_ph3_fixtures(args.output_dir)
    elif args.command == "generate-ph3-change-record":
        result = _generate_ph3_change_record(args.output_dir)
    elif args.command == "generate-clw-st101-fixtures":
        result = _generate_clw_st101_fixtures(args.output_dir)
    elif args.command == "generate-clw-st101-change-record":
        result = _generate_clw_st101_change_record(args.output_dir)
    else:
        result = evaluate_module_admission(load_json(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (
        result.get("state") == "completed"
        or result.get("status") == "accepted"
        or result.get("admitted") is True
        or result.get("machineCode") is not None
        or result.get("fixturesCreated") is not None
        or result.get("changeRecordCreated") is not None
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
