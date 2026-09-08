"""Cross-phase deterministic tests for Development System runtime."""

import json
import sys
import tempfile
from pathlib import Path

from development_runtime import (
    _sha256,
    GOVERNED_STATES,
    STATUS_ZH_MAP,
    STORY_PROFILE_DEFAULTS,
    STORY_PROFILE_SIZES,
    advance_circuit,
    append_event,
    authorize_half_open,
    build_audit_report,
    check_duplicate_side_effects,
    compute_dry_run_manifest_hash,
    compute_policy_hash,
    decide_auto_approval,
    decide_execution,
    decide_takeover,
    evaluate_dry_run_gate,
    evaluate_live_handoff_stories,
    evaluate_merge,
    evaluate_completion,
    evaluate_module_admission,
    evaluate_resources,
    evaluate_verified_progress,
    get_default_story_profile,
    preauthorization_matches,
    project_all_status_zh,
    project_status_zh,
    resume_cycle,
    route_rework,
    run_live_loop,
    schedule_slots,
    status_projection,
    validate_artifact_envelope,
    validate_claude_registry,
    validate_feedback_evidence,
    validate_feedback_lineage,
    validate_history,
    validate_preauthorization_policy,
    validate_registry,
    validate_skill_interface,
    validate_story_profile,
    validate_transition,
    write_snapshot_atomic,
)


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_GOVERNED_STATES = (
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


def check(condition, message, errors):
    if not condition:
        errors.append(message)


TEST_NOW = "2026-08-16T04:00:00+00:00"


def active_policy(workspace=None):
    policy = {
        "policyId": "DS-PH2-CLAUDE-PREAUTH-20260816-001",
        "version": "1.0",
        "status": "active",
        # Keep the fixture valid independently of the wall clock.  Runtime
        # behavior is tested against TEST_NOW below; an expired fixture would
        # make unrelated Claude-first and takeover assertions fail over time.
        "validFrom": "2026-08-15T00:00:00+00:00",
        "expiresAt": "2099-01-01T00:00:00+00:00",
        "workspaceRoots": [str(workspace or ROOT)],
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
    }
    policy["policyHash"] = compute_policy_hash(policy)
    return policy


def required_authorization(policy, packet_hash=None):
    return {
        "policyId": policy["policyId"],
        "policyHash": compute_policy_hash(policy),
        "packetHash": packet_hash or _sha256({"packetId": "HND-PH2-001"}),
        "workspace": policy["workspaceRoots"][0],
        "actions": ["read", "edit", "test", "validate"],
        "data": ["workspace-source"],
        "network": [],
        "tools": ["claude-code", "python"],
        "credentialBoundary": "inherit-claude-auth-only",
        "feedbackSchema": "feedback-packet.schema.json",
        "timeoutSeconds": 600,
        "rounds": 1,
        "concurrency": 1,
        "stopConditions": ["p0-drift", "timeout"],
    }


def dry_run_record(packet_hash, policy_hash, **overrides):
    record = {
        "manifestIdentity": "DRY-HND-PH2-001",
        "packetHash": packet_hash,
        "policyHash": policy_hash,
        "mode": "dry-run",
        "status": "DRY_RUN_OK",
        "spawnedProcess": False,
        "generatedAt": "2026-08-16T03:30:00+00:00",
    }
    record.update(overrides)
    record["manifestHash"] = compute_dry_run_manifest_hash(record)
    return record


def test_authority_and_execution(errors):
    findings = validate_registry(
        [{"profileId": "engineer", "globallyDiscoverable": False}],
        [{"name": "handoff-system"}],
    )
    check(not findings, "valid private profile registry rejected", errors)
    findings = validate_registry(
        [{"profileId": "engineer", "globallyDiscoverable": True}],
        [{"name": "engineer"}],
    )
    check(any(f["severity"] == "P0" for f in findings), "global profile clash not rejected", errors)

    policy = active_policy()
    required = required_authorization(policy)
    matched, missing = preauthorization_matches(required, policy, now=TEST_NOW)
    check(matched and not missing, f"complete preauthorization did not match: {missing}", errors)
    incomplete = dict(required)
    incomplete.pop("network")
    matched, missing = preauthorization_matches(incomplete, policy, now=TEST_NOW)
    check(not matched and "network" in missing, "missing network dimension was accepted", errors)
    # PH-2: test credentialBoundary mismatch
    cred_mismatch = dict(required)
    cred_mismatch["credentialBoundary"] = "read-credentials"
    matched, missing = preauthorization_matches(cred_mismatch, policy, now=TEST_NOW)
    check(not matched and "credentialBoundary" in missing, "credential boundary mismatch accepted", errors)
    # PH-2: test feedbackSchema mismatch
    schema_mismatch = dict(required)
    schema_mismatch["feedbackSchema"] = "other-schema.json"
    matched, missing = preauthorization_matches(schema_mismatch, policy, now=TEST_NOW)
    check(not matched and "feedbackSchema" in missing, "feedback schema mismatch accepted", errors)
    # PH-2: test rounds overflow
    rounds_overflow = dict(required)
    rounds_overflow["rounds"] = 20
    matched, missing = preauthorization_matches(rounds_overflow, policy, now=TEST_NOW)
    check(not matched and "rounds" in missing, "rounds overflow accepted", errors)
    # PH-2: test concurrency overflow
    conc_overflow = dict(required)
    conc_overflow["concurrency"] = 5
    matched, missing = preauthorization_matches(conc_overflow, policy, now=TEST_NOW)
    check(not matched and "concurrency" in missing, "concurrency overflow accepted", errors)
    # PH-2: test stopConditions not subset
    stop_mismatch = dict(required)
    stop_mismatch["stopConditions"] = ["unknown-stop"]
    matched, missing = preauthorization_matches(stop_mismatch, policy, now=TEST_NOW)
    check(not matched and "stopConditions" in missing, "unknown stop condition accepted", errors)

    task = {"signals": ["multiFile"], "requiredAuthorization": required}
    # decide_execution is intentionally passed a policy whose validity is
    # independent of wall-clock time; preauthorization_matches is checked
    # above with TEST_NOW for deterministic assertions.
    check(decide_execution(task, policy, True)["decision"] == "claude-first", "Claude-first task not routed to Claude", errors)
    check(decide_execution(task, policy, False)["decision"] == "codex-takeover", "authorized takeover not selected", errors)
    install_task = {"signals": ["skillDevelopment"], "requiredAuthorization": required, "userLevelInstall": True}
    check(decide_execution(install_task, policy, True)["decision"] == "blocked-user-decision", "user-level install was auto-approved", errors)


def test_governed_state_contract(errors):
    check(GOVERNED_STATES == EXPECTED_GOVERNED_STATES, "runtime governed states differ from DS-PSR-001", errors)
    rejected = validate_transition("running", "cancelled-or-superseded", "Codex")
    check(
        not rejected["allowed"] and rejected["reason"] == "unknown-governed-state",
        "undeclared cancelled-or-superseded state was accepted",
        errors,
    )


def test_event_snapshot_recovery(errors):
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "history.jsonl"
        snapshot_path = Path(tmp) / "snapshot.json"
        first = append_event(history, {"eventType": "cycle-started", "cycleId": "C1", "trace": ["FR-006"]})
        second = append_event(history, {"eventType": "story-started", "cycleId": "C1", "trace": ["FR-008"]})
        valid, history_errors, events = validate_history(history)
        check(valid and not history_errors and len(events) == 2, "valid event history rejected", errors)
        snapshot = write_snapshot_atomic(snapshot_path, {
            "cycleId": "C1",
            "anchorId": "A1",
            "anchorVersion": "1.0",
            "workspaceFingerprint": "W1",
            "lastSequenceIndex": second["sequenceIndex"],
            "lastEventHash": second["eventHash"],
            "state": "running",
            "phaseId": "PH-01",
            "storyId": "PH1-ST-007",
            "roundNumber": 1,
            "heartbeatAt": "fresh",
            "evidenceRefs": ["EV-1"],
            "nextAction": "continue",
        })
        check(snapshot_path.exists() and snapshot["snapshotHash"], "atomic snapshot missing", errors)
        resumed = resume_cycle(history, snapshot_path, "A1", "1.0", "W1", True)
        check(resumed["resumable"], f"valid recovery rejected: {resumed['errors']}", errors)
        bad_anchor = resume_cycle(history, snapshot_path, "A1", "2.0", "W1", True)
        check(not bad_anchor["resumable"] and "anchor-mismatch" in bad_anchor["errors"], "anchor drift recovery accepted", errors)
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        raw["lastEventHash"] = first["eventHash"]
        snapshot_path.write_text(json.dumps(raw), encoding="utf-8")
        bad_hash = resume_cycle(history, snapshot_path, "A1", "1.0", "W1", True)
        check(not bad_hash["resumable"], "tampered snapshot accepted", errors)


def test_progress_circuit_and_timeout(errors):
    good = evaluate_verified_progress({"mappedFrAc": ["FR-015"], "validationPassed": True, "evidenceRefs": ["EV"], "stateImproved": True})
    check(good["verified"], "verified progress rejected", errors)
    claim_only = evaluate_verified_progress({"agentClaim": "COMPLETE", "mappedFrAc": ["FR-015"], "validationPassed": False, "evidenceRefs": [], "stateImproved": False})
    check(not claim_only["verified"], "Agent claim counted as progress", errors)

    counters = {}
    for _ in range(3):
        result = advance_circuit(counters, {"actualExecution": True, "verifiedProgress": False})
        counters = result["counters"]
    check(result["nextState"] == "loop-limit-reached" and counters["circuitState"] == "OPEN", "three no-progress rounds did not open circuit", errors)

    counters = {}
    failure = {"type": "test", "testId": "T1", "message": "same error", "rootCause": "schema"}
    for index in range(5):
        result = advance_circuit(counters, {"actualExecution": False, "failure": failure})
        counters = result["counters"]
        if index == 2:
            check(result["nextState"] == "repair-needed", "third repeated failure did not request repair review", errors)
    check(result["nextState"] == "loop-limit-reached", "fifth repeated failure did not open circuit", errors)

    counters = {}
    for _ in range(3):
        result = advance_circuit(counters, {"invalidFeedbackRoot": "schema-output"})
        counters = result["counters"]
    check(result["nextState"] == "loop-limit-reached", "third invalid feedback did not stop loop", errors)

    counters = {}
    first_timeout = advance_circuit(counters, {"timeout": True})
    second_timeout = advance_circuit(first_timeout["counters"], {"timeout": True, "takeoverPreauthorized": True})
    check(first_timeout["stopReason"] == "timeout-recovery-required", "first timeout recovery rule failed", errors)
    check(second_timeout["stopReason"] == "timeout-codex-takeover", "second timeout takeover rule failed", errors)

    counters = {"roundCount": 9}
    round_ten = advance_circuit(counters, {"actualExecution": True, "completionPassed": False})
    check(round_ten["nextState"] == "loop-limit-reached", "round ten did not stop", errors)
    check(authorize_half_open("OPEN", True, False)["allowed"], "Codex-authorized half-open probe rejected", errors)
    check(not authorize_half_open("OPEN", False, False)["allowed"], "Agent cleared circuit without Codex", errors)


def _make_feedback_validation(feedback):
    """Produce valid hash-bound feedback validation evidence for a feedback object."""
    return {
        "schemaRef": "feedback-packet.schema.json",
        "validatorId": "handoff-feedback-reviewer",
        "feedbackHash": _sha256(feedback),
        "ok": True,
        "errorCount": 0,
        "validatedAt": "2026-08-15T00:00:00+00:00",
    }


def test_feedback_validation_evidence(errors):
    feedback = {"packetId": "FB-UNIT-001", "result": "completed", "evidenceRefs": ["EV-1"]}

    valid_evidence = _make_feedback_validation(feedback)
    result = validate_feedback_evidence(feedback, valid_evidence)
    check(result["valid"], f"valid feedback validation evidence rejected: {result['errors']}", errors)

    missing_evidence = {}
    result = validate_feedback_evidence(feedback, missing_evidence)
    check(not result["valid"] and "schemaRef-missing" in result["errors"], "missing schemaRef accepted", errors)
    check(not result["valid"] and "validatorId-missing" in result["errors"], "missing validatorId accepted", errors)
    check(not result["valid"] and "feedbackHash-missing" in result["errors"], "missing feedbackHash not detected", errors)
    check(not result["valid"] and "validation-ok-false" in result["errors"], "missing ok=true accepted", errors)

    tampered_evidence = dict(valid_evidence)
    tampered_evidence["feedbackHash"] = "0" * 64
    result = validate_feedback_evidence(feedback, tampered_evidence)
    check(not result["valid"] and "feedbackHash-mismatch" in result["errors"], "hash mismatch not detected", errors)

    wrong_length_evidence = dict(valid_evidence)
    wrong_length_evidence["feedbackHash"] = "abc123"
    result = validate_feedback_evidence(feedback, wrong_length_evidence)
    check(not result["valid"] and "feedbackHash-wrong-length" in result["errors"], "wrong hash length not detected", errors)

    uppercase_evidence = dict(valid_evidence)
    uppercase_evidence["feedbackHash"] = _sha256(feedback).upper()
    result = validate_feedback_evidence(feedback, uppercase_evidence)
    check(not result["valid"] and "feedbackHash-not-lowercase-hex" in result["errors"], "uppercase hash accepted", errors)

    non_string_evidence = dict(valid_evidence)
    non_string_evidence["feedbackHash"] = 123
    result = validate_feedback_evidence(feedback, non_string_evidence)
    check(not result["valid"] and "feedbackHash-not-string" in result["errors"], "non-string hash accepted", errors)

    schema_errors_evidence = {
        "schemaRef": "feedback-packet.schema.json",
        "validatorId": "handoff-feedback-reviewer",
        "feedbackHash": _sha256(feedback),
        "ok": False,
        "errorCount": 1,
        "errors": ["missing-required-field"],
        "validatedAt": "2026-08-15T00:00:00+00:00",
    }
    result = validate_feedback_evidence(feedback, schema_errors_evidence)
    check(not result["valid"] and "validation-ok-false" in result["errors"], "ok=false accepted", errors)
    check(not result["valid"] and "errorCount-nonzero" in result["errors"], "errorCount nonzero accepted", errors)
    check(not result["valid"] and "errors-not-empty" in result["errors"], "non-empty errors accepted", errors)

    no_feedback_result = validate_feedback_evidence({}, valid_evidence)
    check(not no_feedback_result["valid"] and "feedback-missing" in no_feedback_result["errors"], "empty feedback accepted", errors)


def test_bare_boolean_cannot_complete(errors):
    """Demonstrate that feedbackValid=true alone cannot pass completion after the repair."""
    bare = {
        "allStoriesPassed": True,
        "allAcceptanceCriteriaVerified": True,
        "feedbackValid": True,
        "evidenceComplete": True,
        "qaPassed": True,
        "driftSeverity": "none",
        "unmappedActions": [],
        "permissionGatePassed": True,
        "riskGatePassed": True,
        "codexReviewPassed": True,
    }
    result = evaluate_completion(bare)
    check(result["state"] != "completed", "bare feedbackValid=true bypassed completion gate", errors)
    check("feedbackValid" in result["blockers"], "feedbackValid not in blockers for bare boolean", errors)


def test_completion_rework_and_qa(errors):
    feedback = {"packetId": "FB-POS-001", "result": "completed", "evidenceRefs": ["EV-1"]}
    fv = _make_feedback_validation(feedback)
    base = {
        "allStoriesPassed": True,
        "allAcceptanceCriteriaVerified": True,
        "feedback": feedback,
        "feedbackValidation": fv,
        "evidenceComplete": True,
        "qaPassed": True,
        "driftSeverity": "none",
        "unmappedActions": [],
        "permissionGatePassed": True,
        "riskGatePassed": True,
        "codexReviewPassed": True,
        "agentCompletionClaim": False,
    }
    check(evaluate_completion(base)["state"] == "completed", "complete evidence did not pass", errors)
    claim_only = {key: False for key in base}
    claim_only["agentCompletionClaim"] = True
    claim_only["driftSeverity"] = "P1"
    claim_only["unmappedActions"] = ["untraced"]
    check(evaluate_completion(claim_only)["state"] == "requirements-review", "Agent claim bypassed completion", errors)
    timeout_claim = dict(base)
    timeout_claim["feedbackValidation"] = {}
    timeout_claim["agentCompletionClaim"] = True
    timeout_claim["stopSignal"] = "timeout"
    check(evaluate_completion(timeout_claim)["state"] != "completed", "invalid timeout feedback completed", errors)
    check(route_rework("architecture")["owner"] == "architect", "architecture defect misrouted", errors)
    check(route_rework("implementation")["owner"] == "engineer", "implementation defect misrouted", errors)
    check(route_rework("test")["owner"] == "qa", "test defect misrouted", errors)

    agent_transition = validate_transition("running", "completed", "Claude", base)
    check(not agent_transition["allowed"], "non-Codex actor changed final state", errors)
    incomplete_transition = validate_transition("running", "completed", "Codex", timeout_claim)
    check(not incomplete_transition["allowed"], "Codex bypassed CompletionEvaluator", errors)
    complete_transition = validate_transition("running", "completed", "Codex", base)
    check(complete_transition["allowed"], "valid Codex completion transition rejected", errors)
    reopened = validate_transition("completed", "running", "Codex")
    check(not reopened["allowed"], "terminal completed state was reopened", errors)


def test_concurrency_resources_observability_and_admission(errors):
    stories = [
        {"storyId": "S1", "dependsOn": [], "workspaceFingerprint": "W1", "writeSet": ["a.py"]},
        {"storyId": "S2", "dependsOn": [], "workspaceFingerprint": "W2", "writeSet": ["b.py"]},
        {"storyId": "S3", "dependsOn": [], "workspaceFingerprint": "W2", "writeSet": ["a.py"]},
    ]
    scheduled = schedule_slots(stories)
    check(len(scheduled["scheduled"]) == 2 and scheduled["blocked"][0]["storyId"] == "S3", "slot collision not blocked", errors)
    resources = evaluate_resources({"calls": 11, "tokens": 100}, {"calls": 10, "tokens": 200})
    check(resources["state"] == "resource-limit-reached" and resources["exceeded"] == ["calls"], "resource limit not enforced", errors)
    projection = status_projection({"cycleId": "C", "phaseId": "P", "storyId": "S", "roundNumber": 2, "state": "running", "heartbeatAt": "now", "evidenceRefs": ["E"], "nextAction": "test"})
    check("internalThought" not in projection and projection["state"] == "running", "status view leaked or lost governed state", errors)
    incomplete = evaluate_module_admission({"license": "MIT", "codeRequested": True})
    check(not incomplete["admitted"] and incomplete["classification"] == "reference-only", "incomplete module admitted", errors)
    complete = evaluate_module_admission({
        "license": "MIT", "version": "1.0", "dependencies": ["x"], "isolation": "adapter",
        "exceptionPolicy": "fail-closed", "testEvidence": ["T"], "rollback": "remove-adapter", "codeRequested": True,
    })
    check(complete["admitted"] and complete["classification"] == "code-admission-candidate", "complete module candidate rejected", errors)
    bypass = dict(complete)
    bypass["changesCompletionAuthority"] = True
    check(evaluate_module_admission(bypass)["classification"] == "rejected", "governance-bypass module admitted", errors)

    merge = evaluate_merge({
        "baselineBefore": "B1", "baselineCurrent": "B1", "writeSetConflicts": [],
        "evidenceRefs": ["EV"], "validationPassed": True, "storyId": "S1", "mappedFrAc": ["FR-029"],
    })
    check(merge["mergeAllowed"], "valid merge candidate rejected", errors)
    drifted_merge = evaluate_merge({
        "baselineBefore": "B1", "baselineCurrent": "B2", "writeSetConflicts": ["a.py"],
        "evidenceRefs": [], "validationPassed": False, "storyId": "S1", "mappedFrAc": ["FR-029"],
    })
    check(not drifted_merge["mergeAllowed"] and "baselineUnchanged" in drifted_merge["blockers"], "drifted merge candidate accepted", errors)

    artifact = {
        "artifactId": "ART-1", "version": "1.0", "artifactType": "architecture",
        "owner": "architect", "sourceAnchorId": "A1", "sourceAnchorVersion": "1.0",
        "mappedFrAc": ["FR-007"], "createdAt": "2026-08-16T00:00:00+08:00",
        "derivedFrom": ["SRC-1"],
    }
    check(not validate_artifact_envelope(artifact), "valid artifact envelope rejected", errors)
    no_trace = dict(artifact)
    no_trace["mappedFrAc"] = []
    check(validate_artifact_envelope(no_trace), "untraced artifact envelope accepted", errors)

    interface = {
        "skillName": "handoff-system", "version": "1.0", "owner": "handoff-system",
        "inputSchemaRef": "handoff.json", "outputSchemaRef": "feedback.json",
        "allowedActions": ["execute"], "forbiddenActions": ["complete"],
        "evidenceContract": ["manifest", "feedback"],
        "statusMapping": {"continue": "running"},
    }
    check(not validate_skill_interface(interface), "valid independent Skill interface rejected", errors)
    bypass_interface = dict(interface)
    bypass_interface["changesCompletionAuthority"] = True
    check(validate_skill_interface(bypass_interface), "Skill interface bypass accepted", errors)

    report = build_audit_report(
        [{"sequenceIndex": 1, "observedAt": "now", "eventType": "story-started", "cycleId": "C", "trace": ["FR-032"], "internalThought": "private"}],
        [{"decisionId": "D1", "state": "running", "reasonCode": "verified", "trace": ["AC-031"], "rawPrompt": "private"}],
    )
    serialized = json.dumps(report)
    check(report["reconstructable"], "audit report is not reconstructable", errors)
    check("internalThought" not in serialized and "rawPrompt" not in serialized, "audit report leaked private fields", errors)


def test_declared_negative_fixtures(errors):
    negative_dir = ROOT / "assets" / "fixtures" / "negative"
    required = {
        "NEG-COMPLETION-001-agent-claim.json",
        "NEG-COMPLETION-002-timeout-completed.json",
        "NEG-COMPLETION-003-drift-completed.json",
        "NEG-COMPLETION-004-missing-validation-evidence.json",
        "NEG-COMPLETION-005-hash-mismatch.json",
        "NEG-COMPLETION-006-schema-errors.json",
        "NEG-STATE-001-undeclared-cancelled-state.json",
        "NEG-RECOVERY-001-snapshot-hash.json",
        "NEG-RECOVERY-002-anchor-version.json",
        "NEG-RECOVERY-003-event-sequence.json",
        "NEG-LOOP-001-no-progress.json",
        "NEG-LOOP-002-round-eleven.json",
        "NEG-AUTH-001-workspace-boundary.json",
        "NEG-AUTH-002-incomplete-preauthorization.json",
        "NEG-AUTH-003-user-skill-install.json",
        "NEG-AUTH-004-credential-mismatch.json",
        "NEG-AUTH-005-schema-mismatch.json",
        "NEG-AUTH-006-rounds-overflow.json",
        "NEG-AUTH-007-concurrency-overflow.json",
        "NEG-AUTH-008-stopcondition-mismatch.json",
        "NEG-AUTH-009-expired-policy.json",
        "NEG-AUTH-010-policy-hash-mismatch.json",
        "NEG-AUTH-011-inactive-policy.json",
        "NEG-REGISTRY-001-completion-authority.json",
        "NEG-DRYRUN-001-no-manifest.json",
        "NEG-DRYRUN-002-wrong-packet.json",
        "NEG-DRYRUN-003-wrong-policy-hash.json",
        "NEG-DRYRUN-004-manifest-hash-mismatch.json",
        "NEG-TAKEOVER-001-unrecognized-trigger.json",
        "NEG-TAKEOVER-002-not-authorized.json",
        "NEG-TAKEOVER-003-round-limit.json",
        "NEG-TAKEOVER-004-cross-story.json",
        "NEG-SLOT-001-shared-workspace.json",
        "NEG-MERGE-001-write-conflict.json",
        "NEG-METAGPT-001-missing-admission-evidence.json",
    }
    existing = {path.name for path in negative_dir.glob("*.json")}
    # Generate PH-2 fixtures if they don't exist yet
    ph2_missing = {name for name in required - existing if name.startswith(("NEG-AUTH-00", "NEG-DRYRUN", "NEG-STATUS-002", "NEG-TAKEOVER"))}
    if ph2_missing:
        import subprocess as _sp
        _sp.run(
            [sys.executable, str(ROOT / "scripts" / "development_runtime.py"),
             "generate-ph2-fixtures", "--output-dir", str(ROOT / "assets" / "fixtures")],
            cwd=str(ROOT / "scripts"),
            capture_output=True,
        )
        existing = {path.name for path in negative_dir.glob("*.json")}
    # Generate PH-3 fixtures if they don't exist yet
    ph3_required = {
        "NEG-PH3-001-spawn-failure.json",
        "NEG-PH3-002-timeout.json",
        "NEG-PH3-003-invalid-feedback.json",
        "NEG-PH3-004-p1-drift.json",
        "NEG-PH3-005-unmapped-action.json",
        "NEG-PH3-006-stale-field.json",
        "NEG-PH3-007-evidence-gap.json",
        "NEG-PH3-008-duplicate-side-effects.json",
        "NEG-PH3-009-round-limit.json",
        "NEG-PH3-010-takeover-limit.json",
        "NEG-PH3-011-no-progress.json",
    }
    required = required | ph3_required
    ph3_missing = ph3_required - existing
    if ph3_missing:
        import subprocess as _sp3
        _sp3.run(
            [sys.executable, str(ROOT / "scripts" / "development_runtime.py"),
             "generate-ph3-fixtures", "--output-dir", str(ROOT / "assets" / "fixtures")],
            cwd=str(ROOT / "scripts"),
            capture_output=True,
        )
        existing = {path.name for path in negative_dir.glob("*.json")}
    # Generate CLW-ST-101 fixtures if they don't exist yet
    clw_dir = ROOT / "assets" / "fixtures" / "clw-st-101"
    clw_required = {
        "pos-clw-101-small.json",
        "pos-clw-101-medium.json",
        "neg-clw-001-multi-story.json",
        "neg-clw-002-large-story.json",
    }
    if not clw_dir.exists() or not clw_required.issubset({p.name for p in clw_dir.glob("*.json")}):
        import subprocess as _sp_clw
        _sp_clw.run(
            [sys.executable, str(ROOT / "scripts" / "development_runtime.py"),
             "generate-clw-st101-fixtures", "--output-dir", str(ROOT / "assets" / "fixtures")],
            cwd=str(ROOT / "scripts"),
            capture_output=True,
        )
    # Verify CLW-ST-101 fixtures exist
    if clw_dir.exists():
        for name in clw_required:
            if not (clw_dir / name).exists():
                errors.append(f"CLW-ST-101 fixture missing: {name}")
    else:
        errors.append("CLW-ST-101 fixture directory missing")
    for name in sorted(required - existing):
        errors.append(f"negative fixture missing: {name}")
    for name in required & existing:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        check(data.get("expectedValidation") == "reject", f"{name} must declare reject", errors)
        check(bool(data.get("expectedRejectionRule")), f"{name} missing rejection rule", errors)


def test_negative_fixture_semantics(errors):
    negative_dir = ROOT / "assets" / "fixtures" / "negative"

    for name in [
        "NEG-COMPLETION-001-agent-claim.json",
        "NEG-COMPLETION-002-timeout-completed.json",
        "NEG-COMPLETION-003-drift-completed.json",
        "NEG-COMPLETION-004-missing-validation-evidence.json",
        "NEG-COMPLETION-005-hash-mismatch.json",
        "NEG-COMPLETION-006-schema-errors.json",
    ]:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        result = evaluate_completion(data["input"])
        check(result["state"] == data["expectedState"] and not result["passed"], f"{name} did not exercise completion rejection", errors)

    data = json.loads((negative_dir / "NEG-STATE-001-undeclared-cancelled-state.json").read_text(encoding="utf-8"))
    state_input = data["input"]
    result = validate_transition(state_input["currentState"], state_input["nextState"], state_input["actor"])
    check(
        not result["allowed"]
        and result["state"] == data["expectedState"]
        and result["reason"] == data["expectedRejectionRule"],
        "NEG-STATE-001 semantics failed",
        errors,
    )

    data = json.loads((negative_dir / "NEG-LOOP-001-no-progress.json").read_text(encoding="utf-8"))
    counters = data["input"]["initialCounters"]
    for observation in data["input"]["observations"]:
        result = advance_circuit(counters, observation)
        counters = result["counters"]
    check(result["nextState"] == data["expectedState"] and result["stopReason"] == data["expectedStopReason"], "NEG-LOOP-001 semantics failed", errors)

    data = json.loads((negative_dir / "NEG-LOOP-002-round-eleven.json").read_text(encoding="utf-8"))
    result = advance_circuit(data["input"]["initialCounters"], data["input"]["observation"])
    check(result["nextState"] == data["expectedState"] and result["stopReason"] == data["expectedStopReason"], "NEG-LOOP-002 semantics failed", errors)

    data = json.loads((negative_dir / "NEG-AUTH-003-user-skill-install.json").read_text(encoding="utf-8"))
    result = decide_execution(data["input"]["task"], data["input"]["policy"], data["input"]["claudeAvailable"])
    check(result["decision"] == data["expectedState"], "NEG-AUTH-003 semantics failed", errors)

    for name in ["NEG-SLOT-001-shared-workspace.json", "NEG-MERGE-001-write-conflict.json"]:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        result = schedule_slots(data["input"]["stories"])
        blocked = result["blocked"]
        check(bool(blocked) and blocked[0]["storyId"] == data["expectedBlockedStory"] and data["expectedReason"] in blocked[0]["reasons"], f"{name} semantics failed", errors)

    data = json.loads((negative_dir / "NEG-METAGPT-001-missing-admission-evidence.json").read_text(encoding="utf-8"))
    result = evaluate_module_admission(data["input"])
    check(result["classification"] == data["expectedClassification"] and result["admitted"] is data["expectedAdmitted"], "NEG-METAGPT-001 semantics failed", errors)

    # PH-2 negative fixture semantics
    for name in ["NEG-AUTH-004-credential-mismatch.json", "NEG-AUTH-005-schema-mismatch.json",
                 "NEG-AUTH-006-rounds-overflow.json", "NEG-AUTH-007-concurrency-overflow.json",
                 "NEG-AUTH-008-stopcondition-mismatch.json"]:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        result = preauthorization_matches(data["input"]["required"], data["input"]["policy"])
        check(not result[0] and data["expectedMissingDimensions"][0] in result[1],
              f"{name} semantics failed: {result}", errors)

    # NEG-DRYRUN semantics
    for name in ["NEG-DRYRUN-001-no-manifest.json", "NEG-DRYRUN-002-wrong-packet.json", "NEG-DRYRUN-003-wrong-policy-hash.json"]:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        result = evaluate_dry_run_gate(data["input"]["packetHash"], data["input"]["policyHash"], data["input"]["dryRunRecords"])
        check(not result["allowed"] and result["status"] == data["expectedStatus"],
              f"{name} semantics failed: {result}", errors)

    # NEG-STATUS-002 semantics
    data = json.loads((negative_dir / "NEG-STATUS-002-unknown-state.json").read_text(encoding="utf-8"))
    result = project_status_zh(data["input"]["state"])
    check(result["machineCode"] == data["expectedMachineCode"] and result["statusZh"] == data["expectedStatusZh"],
          "NEG-STATUS-002 semantics failed", errors)

    # NEG-TAKEOVER semantics
    for name in ["NEG-TAKEOVER-001-unrecognized-trigger.json", "NEG-TAKEOVER-002-not-authorized.json", "NEG-TAKEOVER-003-round-limit.json"]:
        data = json.loads((negative_dir / name).read_text(encoding="utf-8"))
        result = decide_takeover(data["input"]["trigger"], data["input"]["cycleId"], data["input"]["storyId"],
                                data["input"]["roundNumber"], data["input"]["policy"], data["input"]["evidenceLineage"])
        check(not result["allowed"] and result["reason"] == data["expectedReason"],
              f"{name} semantics failed: {result}", errors)

    # NEG-TAKEOVER-004: cross-story takeover is forbidden.
    data = json.loads((negative_dir / "NEG-TAKEOVER-004-cross-story.json").read_text(encoding="utf-8"))
    result = decide_takeover(data["input"]["trigger"], data["input"]["cycleId"], data["input"]["storyId"],
                            data["input"]["roundNumber"], data["input"]["policy"], data["input"]["evidenceLineage"],
                            origin_cycle_id=data["input"]["originCycleId"], origin_story_id=data["input"]["originStoryId"])
    check(not result["allowed"] and result["reason"] == data["expectedRejectionRule"],
          "NEG-TAKEOVER-004 semantics failed", errors)

    # CLW-ST-101 negative fixture semantics
    clw_dir = ROOT / "assets" / "fixtures" / "clw-st-101"
    for name in ["neg-clw-001-multi-story.json", "neg-clw-002-large-story.json"]:
        path = clw_dir / name
        if not path.exists():
            errors.append(f"CLW-ST-101 fixture missing: {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_live_handoff_stories(data["input"])
        check(not result["allowed"], f"{name} was allowed when it should be rejected", errors)
        check(result["decision"] == data["expectedDecision"], f"{name} decision mismatch: {result['decision']}", errors)
        if name == "neg-clw-001-multi-story.json":
            check(any(f["rule"] == data["expectedRejectionRule"] for f in result["findings"]),
                  f"{name} rejection rule not found in findings", errors)
        if name == "neg-clw-002-large-story.json":
            check(result.get("splitFinding") is not None, f"{name} did not produce a split finding", errors)
            check(result["splitFinding"]["rule"] == data["expectedRejectionRule"],
                  f"{name} split finding rule mismatch", errors)

    # CLW-ST-101 positive fixture semantics
    for name in ["pos-clw-101-small.json", "pos-clw-101-medium.json"]:
        path = clw_dir / name
        if not path.exists():
            errors.append(f"CLW-ST-101 positive fixture missing: {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_live_handoff_stories(data["input"])
        check(result["allowed"] is True, f"{name} was not allowed: {result['findings']}", errors)
        check(result["decision"] == data["expectedDecision"], f"{name} decision mismatch: {result['decision']}", errors)


def test_ph2_claude_registry(errors):
    """DSCR-ST-2-001: Claude external Agent registry validation (FR-TOT-009, AC-TOT-014, AC-TOT-017)."""
    valid_entry = {
        "agentId": "claude-code-v1",
        "adapterId": "handoff-claude-executor",
        "version": "1.0",
        "capabilities": ["multiFile", "skillDevelopment", "complexRepair", "crossModule"],
        "availability": "available",
        "feedbackSchemaRef": "feedback-packet.schema.json",
        "completionAuthorityIsolated": True,
    }
    findings = validate_claude_registry(valid_entry, [])
    check(not findings, f"valid Claude registry entry rejected: {findings}", errors)

    # Missing required fields
    missing_entry = {"agentId": "claude-incomplete"}
    findings = validate_claude_registry(missing_entry, [])
    check(any(f["rule"] == "registry-required" for f in findings), "missing registry fields not detected", errors)

    # Completion authority not isolated — P0
    auth_entry = dict(valid_entry)
    auth_entry["agentId"] = "claude-with-auth"
    auth_entry["completionAuthorityIsolated"] = False
    findings = validate_claude_registry(auth_entry, [])
    check(any(f["severity"] == "P0" and f["rule"] == "registry-completion-authority-not-isolated" for f in findings), "completion authority not isolated not rejected", errors)

    # Duplicate agentId
    existing = [{"agentId": "claude-code-v1", "adapterId": "other-adapter", "version": "1.0", "capabilities": ["x"], "availability": "available", "feedbackSchemaRef": "s.json", "completionAuthorityIsolated": True}]
    findings = validate_claude_registry(valid_entry, existing)
    check(any(f["rule"] == "registry-duplicate-agentId" for f in findings), "duplicate agentId not detected", errors)

    # Duplicate adapterId
    existing2 = [{"agentId": "other-agent", "adapterId": "handoff-claude-executor", "version": "1.0", "capabilities": ["x"], "availability": "available", "feedbackSchemaRef": "s.json", "completionAuthorityIsolated": True}]
    findings = validate_claude_registry(valid_entry, existing2)
    check(any(f["rule"] == "registry-duplicate-adapterId" for f in findings), "duplicate adapterId not detected", errors)

    unavailable = dict(valid_entry, availability="unknown")
    findings = validate_claude_registry(unavailable, [])
    check(any(f["rule"] == "registry-availability" for f in findings), "invalid availability not detected", errors)


def test_ph2_preauthorization_policy(errors):
    """DSCR-ST-2-002: Preauthorization policy lifecycle (FR-TOT-010, FR-TOT-016, AC-TOT-008, AC-TOT-013)."""
    valid_policy = active_policy()
    findings = validate_preauthorization_policy(valid_policy, now=TEST_NOW)
    check(not findings, f"valid preauthorization policy rejected: {findings}", errors)

    # Missing required fields
    incomplete = dict(valid_policy)
    del incomplete["policyId"]
    del incomplete["stopConditions"]
    findings = validate_preauthorization_policy(incomplete, now=TEST_NOW)
    check(any(f["rule"] == "policy-required" for f in findings), "missing policy fields not detected", errors)

    # Non-active status
    inactive = dict(valid_policy)
    inactive["status"] = "revoked"
    inactive["policyHash"] = compute_policy_hash(inactive)
    findings = validate_preauthorization_policy(inactive, now=TEST_NOW)
    check(any(f["rule"] == "policy-not-active" for f in findings), "non-active policy not detected", errors)

    # Wildcard network
    wildcard = dict(valid_policy)
    wildcard["network"] = ["*"]
    wildcard["policyHash"] = compute_policy_hash(wildcard)
    findings = validate_preauthorization_policy(wildcard, now=TEST_NOW)
    check(any(f["severity"] == "P0" and f["rule"] == "policy-wildcard-network" for f in findings), "wildcard network not rejected", errors)

    # Cross-project reuse
    cross = dict(valid_policy)
    cross["crossProjectReuse"] = True
    cross["policyHash"] = compute_policy_hash(cross)
    findings = validate_preauthorization_policy(cross, now=TEST_NOW)
    check(any(f["severity"] == "P0" and f["rule"] == "policy-cross-project-reuse" for f in findings), "cross-project reuse not rejected", errors)

    # Invalid maxRounds
    bad_rounds = dict(valid_policy)
    bad_rounds["maxRounds"] = 0
    bad_rounds["policyHash"] = compute_policy_hash(bad_rounds)
    findings = validate_preauthorization_policy(bad_rounds, now=TEST_NOW)
    check(any(f["rule"] == "policy-max-rounds-invalid" for f in findings), "invalid maxRounds not detected", errors)

    # Invalid maxConcurrency
    bad_conc = dict(valid_policy)
    bad_conc["maxConcurrency"] = -1
    bad_conc["policyHash"] = compute_policy_hash(bad_conc)
    findings = validate_preauthorization_policy(bad_conc, now=TEST_NOW)
    check(any(f["rule"] == "policy-max-concurrency-invalid" for f in findings), "invalid maxConcurrency not detected", errors)

    # Policy hash is stable
    h1 = compute_policy_hash(valid_policy)
    h2 = compute_policy_hash(valid_policy)
    check(h1 == h2 and len(h1) == 64, "policy hash not stable or not 64 chars", errors)

    expired = dict(valid_policy, expiresAt="2026-08-16T03:00:00+00:00")
    expired["policyHash"] = compute_policy_hash(expired)
    findings = validate_preauthorization_policy(expired, now=TEST_NOW)
    check(any(f["rule"] == "policy-expired" for f in findings), "expired policy not rejected", errors)

    tampered = dict(valid_policy, actions=valid_policy["actions"] + ["publish"])
    findings = validate_preauthorization_policy(tampered, now=TEST_NOW)
    check(any(f["rule"] == "policy-hash-mismatch" for f in findings), "tampered policy hash not rejected", errors)


def test_ph2_auto_approval(errors):
    """DSCR-ST-2-003: Exact-match auto-approval (FR-TOT-011, FR-TOT-015, AC-TOT-007, AC-TOT-008, AC-TOT-011)."""
    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]

    # Exact match with dry-run OK → auto-approved
    task = {"taskId": "ST-2-003", "requiredAuthorization": required_auth}
    result = decide_auto_approval(task, policy, records, now=TEST_NOW)
    check(result["decision"] == "auto-approved", f"exact match not auto-approved: {result}", errors)
    check(result["auditRedacted"] is True, "audit not redacted", errors)
    check(result["matched"] is True, "matched not True", errors)

    # Missing dry-run → blocked
    result = decide_auto_approval(task, policy, [], now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision" and result["reason"] == "dry-run-gate-not-passed", "missing dry-run bypassed gate", errors)

    # A literal status without a hashed manifest cannot satisfy the gate.
    forged_literal = [{"packetHash": required_auth["packetHash"], "policyHash": required_auth["policyHash"], "status": "DRY_RUN_OK"}]
    result = decide_auto_approval(task, policy, forged_literal, now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision", "unhashed dry-run literal bypassed gate", errors)

    # Mismatch in workspace → blocked
    mismatch_task = {"taskId": "ST-2-003-mismatch", "requiredAuthorization": dict(required_auth, workspace="/outside")}
    result = decide_auto_approval(mismatch_task, policy, records, now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision" and result["reason"] == "preauthorization-mismatch", "workspace mismatch auto-approved", errors)
    check("workspace" in result.get("missingDimensions", []), "missingDimensions not populated for workspace", errors)

    # High-risk (userLevelInstall) → blocked even with exact match
    install_task = {"taskId": "ST-2-003-install", "requiredAuthorization": required_auth, "userLevelInstall": True}
    result = decide_auto_approval(install_task, policy, records, now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision" and result["reason"] == "protected-operation-requires-manual-approval", "user-level install auto-approved", errors)

    # High-risk (newBoundary) → blocked
    boundary_task = {"taskId": "ST-2-003-boundary", "requiredAuthorization": required_auth, "newBoundary": True}
    result = decide_auto_approval(boundary_task, policy, records, now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision", "new boundary auto-approved", errors)

    # Non-active policy → blocked
    inactive_policy = dict(policy, status="revoked")
    inactive_policy["policyHash"] = compute_policy_hash(inactive_policy)
    result = decide_auto_approval(task, inactive_policy, records, now=TEST_NOW)
    check(result["decision"] == "blocked-user-decision" and result["reason"] == "policy-invalid-or-inactive", "non-active policy auto-approved", errors)


def test_ph2_dry_run_gate(errors):
    """DSCR-ST-2-004: Dry-run-to-live transition gate (FR-TOT-012, AC-TOT-009)."""
    packet_hash = _sha256({"packetId": "HND-001"})
    policy_hash = _sha256({"policyId": "POL-001"})
    expires_at = "2026-08-17T00:00:00+00:00"

    # No dry-run record → blocked (cannot bypass)
    result = evaluate_dry_run_gate(packet_hash, policy_hash, [], now=TEST_NOW, policy_expires_at=expires_at)
    check(not result["allowed"] and result["status"] == "DRY_RUN_MISSING", "missing dry-run bypassed gate", errors)

    # Valid dry-run record → allowed
    records = [dry_run_record(packet_hash, policy_hash)]
    result = evaluate_dry_run_gate(packet_hash, policy_hash, records, now=TEST_NOW, policy_expires_at=expires_at)
    check(result["allowed"] and result["status"] == "DRY_RUN_OK", "valid dry-run record blocked", errors)

    # Wrong packet hash → blocked
    wrong_packet = _sha256({"packetId": "HND-999"})
    result = evaluate_dry_run_gate(wrong_packet, policy_hash, records, now=TEST_NOW, policy_expires_at=expires_at)
    check(not result["allowed"] and result["status"] == "DRY_RUN_MISSING", "wrong packet hash bypassed gate", errors)

    # Wrong policy hash → blocked
    wrong_policy = _sha256({"policyId": "POL-999"})
    result = evaluate_dry_run_gate(packet_hash, wrong_policy, records, now=TEST_NOW, policy_expires_at=expires_at)
    check(not result["allowed"] and result["status"] == "DRY_RUN_MISSING", "wrong policy hash bypassed gate", errors)

    # Blocked dry-run record → blocked
    blocked_records = [dry_run_record(packet_hash, policy_hash, status="DRY_RUN_BLOCKED")]
    result = evaluate_dry_run_gate(packet_hash, policy_hash, blocked_records, now=TEST_NOW, policy_expires_at=expires_at)
    check(not result["allowed"], "blocked dry-run record bypassed gate", errors)

    tampered = dry_run_record(packet_hash, policy_hash)
    tampered["spawnedProcess"] = True
    result = evaluate_dry_run_gate(packet_hash, policy_hash, [tampered], now=TEST_NOW, policy_expires_at=expires_at)
    check(not result["allowed"] and result["reason"] == "dry-run-manifest-hash-mismatch", "tampered dry-run manifest accepted", errors)

    result = evaluate_dry_run_gate(packet_hash, policy_hash, records, now="2026-08-18T00:00:00+00:00", policy_expires_at=expires_at)
    check(not result["allowed"] and result["reason"] == "policy-expired", "expired policy reused for live transition", errors)


def test_ph2_status_projection(errors):
    """DSCR-ST-2-005: Chinese status projection (FR-TOT-013, FR-TOT-017, AC-TOT-012, AC-TOT-018)."""
    # All 11 governed states have Chinese labels
    all_statuses = project_all_status_zh()
    check(len(all_statuses) == 11, f"expected 11 governed states, got {len(all_statuses)}", errors)
    codes = [s["machineCode"] for s in all_statuses]
    for state in GOVERNED_STATES:
        check(state in codes, f"governed state {state} missing from projection", errors)

    # Each machine code maps to a non-empty Chinese label
    for s in all_statuses:
        check(s["statusZh"] != "", f"empty Chinese label for {s['machineCode']}", errors)

    # Known state projection
    result = project_status_zh("running")
    check(result["machineCode"] == "running" and result["statusZh"] == "运行中", "running state projection wrong", errors)

    result = project_status_zh("completed")
    check(result["machineCode"] == "completed" and result["statusZh"] == "已完成", "completed state projection wrong", errors)

    result = project_status_zh("failed")
    check(result["machineCode"] == "failed" and result["statusZh"] == "失败", "failed state projection wrong", errors)

    # Unknown state maps to failed
    result = project_status_zh("cancelled-or-superseded")
    check(result["machineCode"] == "failed" and result["statusZh"] == "失败", "unknown state did not map to failed", errors)

    result = project_status_zh("nonexistent-state")
    check(result["machineCode"] == "failed", "nonexistent state did not map to failed", errors)

    # STATUS_ZH_MAP covers exactly GOVERNED_STATES
    check(set(STATUS_ZH_MAP.keys()) == set(GOVERNED_STATES), "STATUS_ZH_MAP keys differ from GOVERNED_STATES", errors)


def test_ph2_takeover(errors):
    """DSCR-ST-2-006: Bounded same-Story Codex takeover (FR-TOT-014, FR-TOT-016, AC-TOT-010, AC-TOT-013)."""
    policy = {
        "policyId": "DS-PH2-CLAUDE-PREAUTH-20260816-001",
        "status": "active",
        "maxRounds": 10,
        "maxConcurrency": 1,
        "maxTakeovers": 1,
        "codexTakeoverAllowed": True,
    }
    common = {
        "origin_cycle_id": "C1",
        "origin_story_id": "ST-2-006",
        "authorization_fingerprint": "AUTH-1",
        "origin_authorization_fingerprint": "AUTH-1",
    }

    # Claude unavailable → allowed takeover
    result = decide_takeover("claude-unavailable", "C1", "ST-2-006", 1, policy, ["EV-1"], **common)
    check(result["allowed"] is True, "claude-unavailable takeover rejected", errors)
    check(result["cycleId"] == "C1" and result["storyId"] == "ST-2-006", "takeover did not preserve cycleId/storyId", errors)
    check(result["roundNumber"] == 1, "takeover did not preserve roundNumber", errors)
    check(result["evidenceLineage"] == ["EV-1"], "takeover did not preserve evidence lineage", errors)
    check(result["auditRedacted"] is True, "takeover audit not redacted", errors)

    # Timeout → allowed takeover
    result = decide_takeover("timeout", "C1", "ST-2-006", 2, policy, ["EV-1", "EV-2"], **common)
    check(result["allowed"] is True, "timeout takeover rejected", errors)

    # Invalid feedback → allowed takeover
    result = decide_takeover("invalid-feedback", "C1", "ST-2-006", 3, policy, ["EV-1"], invalid_feedback_count=2, **common)
    check(result["allowed"] is True, "invalid-feedback takeover rejected", errors)

    # Unrecognized trigger → blocked
    result = decide_takeover("unknown-trigger", "C1", "ST-2-006", 1, policy, ["EV-1"], **common)
    check(not result["allowed"] and result["reason"] == "unrecognized-takeover-trigger", "unrecognized trigger accepted", errors)

    # codexTakeoverAllowed is False → blocked
    no_takeover_policy = dict(policy, codexTakeoverAllowed=False)
    result = decide_takeover("claude-unavailable", "C1", "ST-2-006", 1, no_takeover_policy, ["EV-1"], **common)
    check(not result["allowed"] and result["reason"] == "takeover-not-authorized-by-active-policy", "takeover allowed without policy authorization", errors)

    # Round limit reached → blocked
    result = decide_takeover("claude-unavailable", "C1", "OTHER-STORY", 1, policy, ["EV-1"], **common)
    check(not result["allowed"] and result["reason"] == "cross-story-takeover-forbidden", "cross-story takeover accepted", errors)

    result = decide_takeover("timeout", "C1", "ST-2-006", 1, policy, ["EV-1"], takeover_count=1, **common)
    check(not result["allowed"] and result["reason"] == "takeover-limit-reached", "takeover limit bypassed", errors)

    result = decide_takeover("invalid-feedback", "C1", "ST-2-006", 1, policy, ["EV-1"], invalid_feedback_count=1, **common)
    check(not result["allowed"] and result["reason"] == "invalid-feedback-threshold-not-reached", "single invalid feedback triggered takeover", errors)

    # Round exceeds limit → blocked
    result = decide_takeover("timeout", "C1", "ST-2-006", 15, policy, ["EV-1"], **common)
    check(not result["allowed"] and result["reason"] == "round-limit-reached", "takeover allowed beyond round limit", errors)


def test_ph2_schema_contracts(errors):
    """Ensure PH-2 schemas are strict and aligned with their positive fixtures."""
    schema_dir = ROOT / "schemas"
    fixture_dir = ROOT / "assets" / "fixtures" / "phase-story"
    registry_schema = json.loads((schema_dir / "claude-agent-registry.schema.json").read_text(encoding="utf-8"))
    policy_schema = json.loads((schema_dir / "claude-preauthorization.schema.json").read_text(encoding="utf-8"))
    dry_schema = json.loads((schema_dir / "claude-dry-run-manifest.schema.json").read_text(encoding="utf-8"))
    status_schema = json.loads((schema_dir / "claude-status-projection.schema.json").read_text(encoding="utf-8"))
    takeover_schema = json.loads((schema_dir / "codex-takeover-decision.schema.json").read_text(encoding="utf-8"))

    registry = json.loads((fixture_dir / "ph2-registry-positive.json").read_text(encoding="utf-8"))["input"]["entry"]
    policy = json.loads((fixture_dir / "ph2-preauth-positive.json").read_text(encoding="utf-8"))["input"]
    check(set(registry_schema["required"]).issubset(registry), "registry fixture does not satisfy schema required fields", errors)
    check(set(policy_schema["required"]).issubset(policy), "preauthorization fixture does not satisfy schema required fields", errors)
    check(registry_schema.get("additionalProperties") is False, "registry schema is not strict", errors)
    check(policy_schema.get("additionalProperties") is False, "preauthorization schema is not strict", errors)
    check(dry_schema["properties"]["spawnedProcess"].get("const") is False, "dry-run schema permits process spawn", errors)
    check(set(status_schema["properties"]["machineCode"]["enum"]) == set(GOVERNED_STATES), "status schema differs from governed states", errors)
    check({"takeoverId", "allowed", "reason"}.issubset(takeover_schema["required"]), "takeover schema lacks decision identity", errors)
    check(not validate_claude_registry(registry, []), "registry fixture fails runtime validation", errors)
    check(not validate_preauthorization_policy(policy, now=TEST_NOW), "preauthorization fixture fails runtime validation", errors)


def test_ph3_live_loop_positive(errors):
    """DSCR-ST-3-001: Positive live-loop closed-loop (FR-TOT-001, FR-TOT-011, FR-TOT-012, FR-TOT-017, AC-TOT-007, AC-TOT-009, AC-TOT-014)."""
    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]

    feedback = {"packetId": "FDB-PH3-POS", "packetType": "feedback", "version": "1.0"}
    outcome = {
        "feedback": feedback,
        "processEvidence": {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
        "changedFiles": [{"path": "fixture.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none",
        "unmappedActions": [],
        "evidenceRefs": ["EV-PH3-001"],
    }
    packet = {"packetId": "HND-PH3-POS", "requiredAuthorization": required_auth}
    result = run_live_loop(
        packet, policy, records, outcome,
        cycle_id="C-PH3-001", story_id="DSCR-ST-3-001",
        round_number=1, attempt_id="ATT-PH3-POS-001",
        evidence_lineage=["EV-PRE-001"], now=TEST_NOW,
    )
    check(result["state"] == "completed", f"positive live loop did not complete: {result['state']}, blockers={result['blockers']}", errors)
    check(result["cycleId"] == "C-PH3-001", "live loop did not preserve cycleId", errors)
    check(result["storyId"] == "DSCR-ST-3-001", "live loop did not preserve storyId", errors)
    check(result["roundNumber"] == 1, "live loop did not preserve roundNumber", errors)
    check(result["attemptId"] == "ATT-PH3-POS-001", "live loop did not preserve attemptId", errors)
    check(result["autoApproval"]["decision"] == "auto-approved", "live loop did not auto-approve", errors)
    check(result["feedbackValidation"]["valid"], f"live loop feedback validation failed: {result['feedbackValidation']}", errors)
    check(result["lineageValidation"]["valid"], f"live loop lineage validation failed: {result['lineageValidation']}", errors)
    check(not result["sideEffectCheck"]["hasDuplicates"], "live loop detected false duplicate side effects", errors)
    check(result["completionEvaluation"]["passed"], "live loop completion evaluation did not pass", errors)
    check("ATT-PH3-POS-001" in result["evidenceLineage"], "live loop did not update evidence lineage", errors)

    # Lineage validation: stale field detection
    stale_feedback = dict(feedback, cycleId="OLD-CYCLE")
    lineage_result = validate_feedback_lineage(
        stale_feedback, "C-PH3-001", "DSCR-ST-3-001", 1, "ATT-PH3-POS-001",
    )
    check(not lineage_result["valid"] and any("stale-cycleId" in e for e in lineage_result["errors"]), "stale cycleId not detected", errors)

    stale_round = dict(feedback, roundNumber=99)
    lineage_result = validate_feedback_lineage(
        stale_round, "C-PH3-001", "DSCR-ST-3-001", 1, "ATT-PH3-POS-001",
    )
    check(not lineage_result["valid"] and any("stale-roundNumber" in e for e in lineage_result["errors"]), "stale roundNumber not detected", errors)

    stale_attempt = dict(feedback, attemptId="ATT-OLD-001")
    lineage_result = validate_feedback_lineage(
        stale_attempt, "C-PH3-001", "DSCR-ST-3-001", 1, "ATT-PH3-POS-001",
    )
    check(not lineage_result["valid"] and any("stale-attemptId" in e for e in lineage_result["errors"]), "stale attemptId not detected", errors)

    stale_story = dict(feedback, storyId="OLD-STORY")
    lineage_result = validate_feedback_lineage(
        stale_story, "C-PH3-001", "DSCR-ST-3-001", 1, "ATT-PH3-POS-001",
    )
    check(not lineage_result["valid"] and any("stale-storyId" in e for e in lineage_result["errors"]), "stale storyId not detected", errors)

    # Valid lineage with all fields matching
    valid_feedback = dict(feedback, cycleId="C-PH3-001", storyId="DSCR-ST-3-001", roundNumber=1, attemptId="ATT-PH3-POS-001")
    lineage_result = validate_feedback_lineage(
        valid_feedback, "C-PH3-001", "DSCR-ST-3-001", 1, "ATT-PH3-POS-001",
    )
    check(lineage_result["valid"], f"valid lineage rejected: {lineage_result}", errors)

    # Duplicate side-effect detection
    current = [{"path": "shared.py", "trace": ["FR-001"]}]
    previous = [[{"path": "shared.py", "trace": ["FR-001"]}]]
    dup = check_duplicate_side_effects(current, previous)
    check(dup["hasDuplicates"] and dup["duplicateCount"] == 1, "duplicate side effect not detected", errors)

    no_dup = check_duplicate_side_effects(current, [[{"path": "other.py"}]])
    check(not no_dup["hasDuplicates"], "non-overlapping side effect falsely flagged as duplicate", errors)

    empty_dup = check_duplicate_side_effects([], [[{"path": "shared.py"}]])
    check(not empty_dup["hasDuplicates"], "empty current side effects falsely flagged", errors)

    multi_dup = check_duplicate_side_effects(
        [{"path": "a.py"}, {"path": "b.py"}],
        [[{"path": "a.py"}], [{"path": "b.py"}]],
    )
    check(multi_dup["duplicateCount"] == 2, "multi-round duplicates not counted correctly", errors)


def test_ph3_negative_live_cases(errors):
    """DSCR-ST-3-002: Spawn failure, timeout, invalid feedback (FR-TOT-003, FR-TOT-004, FR-TOT-005, FR-TOT-006, FR-TOT-007, AC-TOT-002, AC-TOT-003, AC-TOT-004, AC-TOT-005, AC-TOT-015)."""
    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]

    # Spawn failure
    spawn_outcome = {
        "feedback": None,
        "processEvidence": {"failureClass": "spawn-permission", "spawnSucceeded": False, "timedOut": False, "childExitCode": None},
        "changedFiles": [], "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": [],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-SPAWN", "requiredAuthorization": required_auth},
        policy, records, spawn_outcome,
        cycle_id="C-PH3-002", story_id="DSCR-ST-3-002",
        round_number=1, attempt_id="ATT-PH3-SPAWN-001", now=TEST_NOW,
    )
    check(result["state"] == "blocked-external-dependency", f"spawn failure did not block: {result['state']}", errors)
    check(result["failureClass"] == "spawn-permission", "spawn failure failureClass mismatch", errors)
    check(not result["completionEvaluation"]["passed"], "spawn failure produced completed", errors)

    # Timeout
    timeout_outcome = {
        "feedback": {"packetId": "FDB-PH3-TIMEOUT", "packetType": "feedback", "version": "1.0"},
        "processEvidence": {"failureClass": "timeout", "spawnSucceeded": True, "timedOut": True, "childExitCode": None},
        "changedFiles": [], "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": [],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-TIMEOUT", "requiredAuthorization": required_auth},
        policy, records, timeout_outcome,
        cycle_id="C-PH3-002", story_id="DSCR-ST-3-002",
        round_number=1, attempt_id="ATT-PH3-TIMEOUT-001", now=TEST_NOW,
    )
    check(result["state"] == "blocked-external-dependency", f"timeout did not block: {result['state']}", errors)
    check(result["failureClass"] == "timeout", "timeout failureClass mismatch", errors)
    check(not result["completionEvaluation"]["passed"], "timeout produced completed", errors)

    # Invalid feedback (feedback-missing)
    invalid_outcome = {
        "feedback": {},
        "processEvidence": {"failureClass": "feedback-missing", "spawnSucceeded": True, "timedOut": False, "childExitCode": 0},
        "changedFiles": [], "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": [],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-INVALID", "requiredAuthorization": required_auth},
        policy, records, invalid_outcome,
        cycle_id="C-PH3-002", story_id="DSCR-ST-3-002",
        round_number=1, attempt_id="ATT-PH3-INVALID-001", now=TEST_NOW,
    )
    check(result["state"] == "repair-needed", f"invalid feedback did not route to repair-needed: {result['state']}", errors)
    check(result["failureClass"] == "feedback-missing", "invalid feedback failureClass mismatch", errors)
    check(not result["completionEvaluation"]["passed"], "invalid feedback produced completed", errors)
    check(not result["feedbackValidation"]["valid"], "invalid feedback validation passed", errors)


def test_ph3_drift_and_completion_blocks(errors):
    """DSCR-ST-3-003: Drift, unmapped action, stale field, evidence gap (FR-TOT-001, FR-TOT-008, FR-TOT-017, AC-TOT-003, AC-TOT-006, AC-TOT-012, AC-TOT-017)."""
    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]
    base_feedback = {"packetId": "FDB-PH3-DRIFT", "packetType": "feedback", "version": "1.0"}
    base_pe = {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0}

    # P1 drift
    drift_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "drift.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "P1", "unmappedActions": [], "evidenceRefs": ["EV-DRIFT"],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-DRIFT", "requiredAuthorization": required_auth},
        policy, records, drift_outcome,
        cycle_id="C-PH3-003", story_id="DSCR-ST-3-003",
        round_number=1, attempt_id="ATT-PH3-DRIFT-001", now=TEST_NOW,
    )
    check(result["state"] == "requirements-review", f"P1 drift did not route to requirements-review: {result['state']}", errors)
    check(not result["completionEvaluation"]["passed"], "P1 drift produced completed", errors)
    check("noP0P1Drift" in result["completionEvaluation"]["blockers"], "P1 drift not in blockers", errors)

    # Unmapped action
    unmapped_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "unmapped.py", "trace": ["FR-UNKNOWN"]}],
        "driftSeverity": "none", "unmappedActions": ["untraced-action"], "evidenceRefs": ["EV-UNMAPPED"],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-UNMAPPED", "requiredAuthorization": required_auth},
        policy, records, unmapped_outcome,
        cycle_id="C-PH3-003", story_id="DSCR-ST-3-003",
        round_number=1, attempt_id="ATT-PH3-UNMAPPED-001", now=TEST_NOW,
    )
    check(result["state"] == "requirements-review", f"unmapped action did not route to requirements-review: {result['state']}", errors)
    check(not result["completionEvaluation"]["passed"], "unmapped action produced completed", errors)
    check("noUnmappedActions" in result["completionEvaluation"]["blockers"], "unmapped action not in blockers", errors)

    # Stale field
    stale_feedback = dict(base_feedback, cycleId="OLD-CYCLE")
    stale_outcome = {
        "feedback": stale_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "stale.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": ["EV-STALE"],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-STALE", "requiredAuthorization": required_auth},
        policy, records, stale_outcome,
        cycle_id="C-PH3-003", story_id="DSCR-ST-3-003",
        round_number=1, attempt_id="ATT-PH3-STALE-001", now=TEST_NOW,
    )
    check(result["state"] == "repair-needed", f"stale field did not route to repair-needed: {result['state']}", errors)
    check(not result["completionEvaluation"]["passed"], "stale field produced completed", errors)
    check(not result["lineageValidation"]["valid"], "stale field lineage validation passed", errors)

    # Evidence gap
    gap_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "gap.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": [],
    }
    result = run_live_loop(
        {"packetId": "HND-PH3-GAP", "requiredAuthorization": required_auth},
        policy, records, gap_outcome,
        cycle_id="C-PH3-003", story_id="DSCR-ST-3-003",
        round_number=1, attempt_id="ATT-PH3-GAP-001", now=TEST_NOW,
    )
    check(result["state"] == "repair-needed", f"evidence gap did not route to repair-needed: {result['state']}", errors)
    check(not result["completionEvaluation"]["passed"], "evidence gap produced completed", errors)
    check("evidenceComplete" in result["completionEvaluation"]["blockers"], "evidence gap not in blockers", errors)


def test_ph3_multi_round_and_limits(errors):
    """DSCR-ST-3-004: Multi-round lineage, duplicate side effects, round/takeover limits (FR-TOT-014, FR-TOT-016, FR-TOT-017, AC-TOT-010, AC-TOT-013, AC-TOT-014)."""
    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]
    base_feedback = {"packetId": "FDB-PH3-MULTI", "packetType": "feedback", "version": "1.0"}
    base_pe = {"failureClass": None, "spawnSucceeded": True, "timedOut": False, "childExitCode": 0}

    # Round 1: success with file A
    r1_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "a.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": ["EV-R1"],
    }
    r1 = run_live_loop(
        {"packetId": "HND-PH3-MULTI", "requiredAuthorization": required_auth},
        policy, records, r1_outcome,
        cycle_id="C-PH3-004", story_id="DSCR-ST-3-004",
        round_number=1, attempt_id="ATT-PH3-R1-001",
        evidence_lineage=["EV-PRE-001"], now=TEST_NOW,
    )
    check(r1["state"] == "completed", f"round 1 did not complete: {r1['state']}", errors)
    check("ATT-PH3-R1-001" in r1["evidenceLineage"], "round 1 attemptId not in lineage", errors)
    check("EV-R1" in r1["evidenceLineage"], "round 1 evidence ref not in lineage", errors)

    # Round 2: same Story, same cycle, different file → no duplicate
    r2_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "b.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": ["EV-R2"],
    }
    r2 = run_live_loop(
        {"packetId": "HND-PH3-MULTI", "requiredAuthorization": required_auth},
        policy, records, r2_outcome,
        cycle_id="C-PH3-004", story_id="DSCR-ST-3-004",
        round_number=2, attempt_id="ATT-PH3-R2-001",
        evidence_lineage=r1["evidenceLineage"], now=TEST_NOW,
    )
    check(r2["state"] == "completed", f"round 2 did not complete: {r2['state']}", errors)
    check("ATT-PH3-R2-001" in r2["evidenceLineage"], "round 2 attemptId not in lineage", errors)
    check(not r2["sideEffectCheck"]["hasDuplicates"], "round 2 falsely detected duplicates", errors)

    # Round 3: same Story, same cycle, duplicate file → blocked
    r3_outcome = {
        "feedback": base_feedback, "processEvidence": base_pe,
        "changedFiles": [{"path": "a.py", "trace": ["FR-TOT-001"]}],
        "driftSeverity": "none", "unmappedActions": [], "evidenceRefs": ["EV-R3"],
    }
    r3 = run_live_loop(
        {"packetId": "HND-PH3-MULTI", "requiredAuthorization": required_auth},
        policy, records, r3_outcome,
        cycle_id="C-PH3-004", story_id="DSCR-ST-3-004",
        round_number=3, attempt_id="ATT-PH3-R3-001",
        evidence_lineage=r2["evidenceLineage"],
        previous_changed_files=[[{"path": "a.py"}], [{"path": "b.py"}]],
        now=TEST_NOW,
    )
    check(r3["state"] == "repair-needed", f"duplicate side effects did not route to repair-needed: {r3['state']}", errors)
    check(r3["sideEffectCheck"]["hasDuplicates"], "duplicate side effects not detected", errors)
    check(r3["sideEffectCheck"]["duplicateCount"] == 1, "duplicate count wrong", errors)
    check("a.py" in r3["sideEffectCheck"]["duplicatePaths"], "duplicate path not in list", errors)
    check(not r3["completionEvaluation"]["passed"], "duplicate side effects produced completed", errors)

    # Round limit: circuit stops at 10 rounds
    counters = {"roundCount": 10, "circuitState": "CLOSED"}
    round_limit = advance_circuit(counters, {"actualExecution": False, "completionPassed": False})
    check(round_limit["nextState"] == "loop-limit-reached", "round limit did not stop loop", errors)
    check(round_limit["stopReason"] == "story-round-limit", "round limit stop reason wrong", errors)
    check(round_limit["counters"]["circuitState"] == "OPEN", "circuit not opened at round limit", errors)

    # Takeover limit
    takeover_policy = {"status": "active", "codexTakeoverAllowed": True, "maxRounds": 10, "maxTakeovers": 1}
    takeover_result = decide_takeover(
        "timeout", "C-PH3-004", "DSCR-ST-3-004", 1, takeover_policy, ["EV-1"],
        origin_cycle_id="C-PH3-004", origin_story_id="DSCR-ST-3-004",
        authorization_fingerprint="AUTH-1", origin_authorization_fingerprint="AUTH-1",
        takeover_count=1,
    )
    check(not takeover_result["allowed"] and takeover_result["reason"] == "takeover-limit-reached", "takeover limit not enforced", errors)

    # No-progress circuit: 3 rounds without verified progress
    counters = {}
    for _ in range(3):
        result = advance_circuit(counters, {"actualExecution": True, "verifiedProgress": False})
        counters = result["counters"]
    check(result["nextState"] == "loop-limit-reached", "no-progress did not stop loop", errors)
    check(result["stopReason"] == "no-verified-progress", "no-progress stop reason wrong", errors)
    check(counters["circuitState"] == "OPEN", "circuit not opened on no-progress", errors)

    # Takeover preserves lineage
    takeover_ok = decide_takeover(
        "timeout", "C-PH3-004", "DSCR-ST-3-004", 2, takeover_policy, ["EV-1", "EV-2"],
        origin_cycle_id="C-PH3-004", origin_story_id="DSCR-ST-3-004",
        authorization_fingerprint="AUTH-1", origin_authorization_fingerprint="AUTH-1",
        takeover_count=0,
    )
    check(takeover_ok["allowed"], "valid takeover rejected", errors)
    check(takeover_ok["cycleId"] == "C-PH3-004", "takeover did not preserve cycleId", errors)
    check(takeover_ok["storyId"] == "DSCR-ST-3-004", "takeover did not preserve storyId", errors)
    check(takeover_ok["roundNumber"] == 2, "takeover did not preserve roundNumber", errors)
    check(takeover_ok["evidenceLineage"] == ["EV-1", "EV-2"], "takeover did not preserve evidence lineage", errors)


def test_ph3_negative_fixture_semantics(errors):
    """Run PH-3 negative fixtures through their target functions."""
    negative_dir = ROOT / "assets" / "fixtures" / "negative"

    policy = active_policy()
    required_auth = required_authorization(policy)
    records = [dry_run_record(required_auth["packetHash"], required_auth["policyHash"])]

    for name in [
        "NEG-PH3-001-spawn-failure.json",
        "NEG-PH3-002-timeout.json",
        "NEG-PH3-003-invalid-feedback.json",
        "NEG-PH3-004-p1-drift.json",
        "NEG-PH3-005-unmapped-action.json",
        "NEG-PH3-006-stale-field.json",
        "NEG-PH3-007-evidence-gap.json",
        "NEG-PH3-008-duplicate-side-effects.json",
    ]:
        path = negative_dir / name
        if not path.exists():
            errors.append(f"PH-3 fixture missing: {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        inp = data["input"]
        # Use active_policy for consistent preauthorization
        inp_policy = policy
        inp_packet = {"packetId": f"HND-{data['fixtureId']}", "requiredAuthorization": required_auth}
        result = run_live_loop(
            inp_packet, inp_policy, records, inp["simulatedOutcome"],
            cycle_id=inp.get("cycleId", "C-PH3-001"),
            story_id=inp.get("storyId", "DSCR-ST-3-001"),
            round_number=inp.get("roundNumber", 1),
            attempt_id=inp.get("attemptId", "ATT-PH3-001"),
            evidence_lineage=inp.get("evidenceLineage"),
            previous_changed_files=inp.get("previousChangedFiles"),
            now=TEST_NOW,
        )
        check(result["state"] == data["expectedState"],
              f"{name} expected {data['expectedState']}, got {result['state']}: blockers={result['blockers']}", errors)
        check(not result["completionEvaluation"]["passed"],
              f"{name} completion evaluation passed when it should not", errors)

    # NEG-PH3-009: round limit
    data = json.loads((negative_dir / "NEG-PH3-009-round-limit.json").read_text(encoding="utf-8"))
    result = advance_circuit(data["input"]["initialCounters"], data["input"]["observation"])
    check(result["nextState"] == data["expectedState"] and result["stopReason"] == data["expectedStopReason"],
          f"NEG-PH3-009 semantics failed: {result}", errors)

    # NEG-PH3-010: takeover limit
    data = json.loads((negative_dir / "NEG-PH3-010-takeover-limit.json").read_text(encoding="utf-8"))
    result = decide_takeover(
        data["input"]["trigger"], data["input"]["cycleId"], data["input"]["storyId"],
        data["input"]["roundNumber"], data["input"]["policy"], data["input"]["evidenceLineage"],
        takeover_count=data["input"]["takeoverCount"],
    )
    check(not result["allowed"] and result["reason"] == data["expectedReason"],
          f"NEG-PH3-010 semantics failed: {result}", errors)

    # NEG-PH3-011: no progress
    data = json.loads((negative_dir / "NEG-PH3-011-no-progress.json").read_text(encoding="utf-8"))
    counters = data["input"]["initialCounters"]
    for observation in data["input"]["observations"]:
        result = advance_circuit(counters, observation)
        counters = result["counters"]
    check(result["nextState"] == data["expectedState"] and result["stopReason"] == data["expectedStopReason"],
          f"NEG-PH3-011 semantics failed: {result}", errors)


def test_clw_st101_story_profile_and_split_gate(errors):
    """CLW-ST-101: Story Profile validation and live handoff single-Story + Large split gate.

    Covers:
    - Positive: Small Story executable
    - Positive: Medium Story executable
    - Negative: Multiple Stories rejected (FR-CLW-001, AC-CLW-001)
    - Negative: Large Story must be split (FR-CLW-002, AC-CLW-002)
    - Story Profile defaults and validation
    """
    # --- Story Profile defaults ---
    check(set(STORY_PROFILE_DEFAULTS.keys()) == {"small", "medium", "large"}, "STORY_PROFILE_DEFAULTS must have small/medium/large", errors)
    check(STORY_PROFILE_SIZES == ("small", "medium", "large"), "STORY_PROFILE_SIZES must be small/medium/large", errors)

    small_profile = get_default_story_profile("small")
    check(small_profile["size"] == "small", "small profile size mismatch", errors)
    check(small_profile["maxRounds"] >= 1 and small_profile["maxRounds"] <= 10, "small profile maxRounds out of range", errors)
    check(small_profile["initialTimeoutSeconds"] == 900, "small initialTimeout must be 15 minutes", errors)
    check(small_profile["extensionSliceSeconds"] == 600, "small extensionSlice must be 10 minutes", errors)
    check(small_profile["noProgressTimeoutSeconds"] == 1200, "small noProgressTimeout must be 20 minutes", errors)
    check(small_profile["attemptHardDeadlineSeconds"] == 2700, "small attemptHardDeadline must be 45 minutes", errors)
    check(small_profile["storyTotalDeadlineSeconds"] == 5400, "small storyTotalDeadline must be 90 minutes", errors)

    medium_profile = get_default_story_profile("medium")
    check(medium_profile["size"] == "medium", "medium profile size mismatch", errors)
    check(medium_profile["initialTimeoutSeconds"] == 1800, "medium initialTimeout must be 30 minutes", errors)
    check(medium_profile["extensionSliceSeconds"] == 900, "medium extensionSlice must be 15 minutes", errors)
    check(medium_profile["noProgressTimeoutSeconds"] == 1800, "medium noProgressTimeout must be 30 minutes", errors)
    check(medium_profile["attemptHardDeadlineSeconds"] == 5400, "medium attemptHardDeadline must be 90 minutes", errors)
    check(medium_profile["storyTotalDeadlineSeconds"] == 14400, "medium storyTotalDeadline must be 240 minutes", errors)

    large_profile = get_default_story_profile("large")
    check(large_profile["size"] == "large", "large profile size mismatch", errors)
    check(large_profile.get("splitRequired") is True, "large profile must require splitting", errors)
    check("attemptHardDeadlineSeconds" not in large_profile, "large profile must not carry an execution budget", errors)

    # Mutating default should not affect baseline
    small_profile["maxRounds"] = 99
    check(get_default_story_profile("small")["maxRounds"] != 99, "get_default_story_profile did not return a copy", errors)

    # Unknown size raises
    try:
        get_default_story_profile("xlarge")
        errors.append("get_default_story_profile should raise for unknown size")
    except ValueError:
        pass

    # --- validate_story_profile ---
    check(not validate_story_profile(get_default_story_profile("small")), "valid small profile rejected", errors)
    check(not validate_story_profile(get_default_story_profile("medium")), "valid medium profile rejected", errors)
    check(not validate_story_profile(get_default_story_profile("large")), "valid large classification rejected", errors)

    # Missing fields
    incomplete = {"size": "small"}
    findings = validate_story_profile(incomplete)
    check(any(f["rule"] == "story-profile-required" for f in findings), "missing profile fields not detected", errors)

    # Invalid size
    bad_size = dict(get_default_story_profile("small"))
    bad_size["size"] = "xlarge"
    findings = validate_story_profile(bad_size)
    check(any(f["rule"] == "story-profile-size" for f in findings), "invalid size not detected", errors)

    # Invalid maxRounds (zero)
    bad_rounds = dict(get_default_story_profile("small"))
    bad_rounds["maxRounds"] = 0
    findings = validate_story_profile(bad_rounds)
    check(any(f["rule"] == "story-profile-max-rounds" for f in findings), "zero maxRounds not detected", errors)

    # Invalid maxRounds (11)
    bad_rounds_11 = dict(get_default_story_profile("small"))
    bad_rounds_11["maxRounds"] = 11
    findings = validate_story_profile(bad_rounds_11)
    check(any(f["rule"] == "story-profile-max-rounds" for f in findings), "maxRounds=11 not detected", errors)

    # Deadline ordering violation
    bad_order = dict(get_default_story_profile("small"))
    bad_order["initialTimeoutSeconds"] = bad_order["noProgressTimeoutSeconds"] + 1
    findings = validate_story_profile(bad_order)
    check(any(f["rule"] == "story-profile-deadline-order" for f in findings), "initialTimeout > noProgressTimeout not detected", errors)

    # Large Stories are classifiers only; adding execution budgets is forbidden.
    large_with_budget = dict(get_default_story_profile("large"))
    large_with_budget["attemptHardDeadlineSeconds"] = 9999
    findings = validate_story_profile(large_with_budget)
    check(any(f["rule"] == "large-story-budget-forbidden" for f in findings), "Large Story execution budget not rejected", errors)

    bad_order2 = dict(get_default_story_profile("small"))
    bad_order2["attemptHardDeadlineSeconds"] = bad_order2["storyTotalDeadlineSeconds"] + 1
    findings = validate_story_profile(bad_order2)
    check(any(f["rule"] == "story-profile-deadline-order" for f in findings), "attemptHardDeadline > storyTotalDeadline not detected", errors)

    # --- evaluate_live_handoff_stories: positive Small ---
    small_packet = {
        "packetId": "HND-CLW-SMALL-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("small"),
        "stories": [{"storyId": "CLW-ST-101-SMALL", "title": "Small", "goal": "Small goal."}],
    }
    result = evaluate_live_handoff_stories(small_packet)
    check(result["allowed"] is True, f"Small story not allowed: {result}", errors)
    check(result["decision"] == "execute", f"Small story decision wrong: {result['decision']}", errors)
    check(result["story"]["storyId"] == "CLW-ST-101-SMALL", "Small story id mismatch", errors)
    check(not result["findings"], f"Small story had findings: {result['findings']}", errors)
    check(result["splitFinding"] is None, "Small story produced a split finding", errors)

    # --- evaluate_live_handoff_stories: positive Medium ---
    medium_packet = {
        "packetId": "HND-CLW-MEDIUM-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("medium"),
        "stories": [{"storyId": "CLW-ST-101-MEDIUM", "title": "Medium", "goal": "Medium goal."}],
    }
    result = evaluate_live_handoff_stories(medium_packet)
    check(result["allowed"] is True, f"Medium story not allowed: {result}", errors)
    check(result["decision"] == "execute", f"Medium story decision wrong: {result['decision']}", errors)
    check(result["story"]["storyId"] == "CLW-ST-101-MEDIUM", "Medium story id mismatch", errors)

    # --- Negative: Multiple Stories (FR-CLW-001, AC-CLW-001) ---
    multi_packet = {
        "packetId": "HND-CLW-MULTI-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("small"),
        "stories": [
            {"storyId": "CLW-ST-101-A", "title": "First", "goal": "First goal."},
            {"storyId": "CLW-ST-101-B", "title": "Second", "goal": "Second goal."},
        ],
    }
    result = evaluate_live_handoff_stories(multi_packet)
    check(result["allowed"] is False, "multi-story packet was allowed", errors)
    check(result["decision"] == "blocked", f"multi-story decision wrong: {result['decision']}", errors)
    check(any(f["rule"] == "multi-story-rejected" and f["severity"] == "P0" for f in result["findings"]), "multi-story rejection rule not found", errors)

    # --- Negative: Large Story (FR-CLW-002, AC-CLW-002) ---
    large_packet = {
        "packetId": "HND-CLW-LARGE-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("large"),
        "stories": [{"storyId": "CLW-ST-101-LARGE", "title": "Large", "goal": "Large goal."}],
    }
    result = evaluate_live_handoff_stories(large_packet)
    check(result["allowed"] is False, "Large story was allowed without split", errors)
    check(result["decision"] == "split-required", f"Large story decision wrong: {result['decision']}", errors)
    check(result["splitFinding"] is not None, "Large story did not produce a split finding", errors)
    check(result["splitFinding"]["rule"] == "large-story-split-required", "split finding rule mismatch", errors)
    check(result["splitFinding"]["requiredAction"] == "split-story-before-execution", "split finding requiredAction mismatch", errors)
    check(result["splitFinding"]["storyId"] == "CLW-ST-101-LARGE", "split finding storyId mismatch", errors)
    check("FR-CLW-002" in result["splitFinding"]["trace"], "split finding missing FR-CLW-002 trace", errors)
    check("AC-CLW-002" in result["splitFinding"]["trace"], "split finding missing AC-CLW-002 trace", errors)

    # --- Edge: empty stories ---
    empty_packet = {
        "packetId": "HND-CLW-EMPTY-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("small"),
        "stories": [],
    }
    result = evaluate_live_handoff_stories(empty_packet)
    check(result["allowed"] is False, "empty stories packet was allowed", errors)
    check(result["decision"] == "blocked", f"empty stories decision wrong: {result['decision']}", errors)

    # --- Edge: missing storyProfile ---
    no_profile_packet = {
        "packetId": "HND-CLW-NOPROFILE-001",
        "packetType": "handoff",
        "version": "1.0",
        "stories": [{"storyId": "CLW-ST-101-NP", "title": "No profile", "goal": "No profile."}],
    }
    result = evaluate_live_handoff_stories(no_profile_packet)
    check(result["allowed"] is False, "missing profile packet was allowed", errors)
    check(any(f["rule"] == "story-profile-missing" for f in result["findings"]), "missing storyProfile not detected", errors)

    # --- Edge: Large + multiple stories: multi-story takes priority (P0) ---
    large_multi_packet = {
        "packetId": "HND-CLW-LARGE-MULTI-001",
        "packetType": "handoff",
        "version": "1.0",
        "storyProfile": get_default_story_profile("large"),
        "stories": [
            {"storyId": "CLW-L-A", "title": "Large A", "goal": "Goal A."},
            {"storyId": "CLW-L-B", "title": "Large B", "goal": "Goal B."},
        ],
    }
    result = evaluate_live_handoff_stories(large_multi_packet)
    check(result["allowed"] is False, "large+multi packet was allowed", errors)
    check(result["decision"] == "blocked", f"large+multi decision should be blocked (P0 priority), got {result['decision']}", errors)
    check(any(f["rule"] == "multi-story-rejected" and f["severity"] == "P0" for f in result["findings"]), "large+multi should have multi-story P0 finding", errors)


def main():
    errors = []
    test_authority_and_execution(errors)
    test_governed_state_contract(errors)
    test_event_snapshot_recovery(errors)
    test_progress_circuit_and_timeout(errors)
    test_feedback_validation_evidence(errors)
    test_bare_boolean_cannot_complete(errors)
    test_completion_rework_and_qa(errors)
    test_concurrency_resources_observability_and_admission(errors)
    test_declared_negative_fixtures(errors)
    test_negative_fixture_semantics(errors)
    test_ph2_claude_registry(errors)
    test_ph2_preauthorization_policy(errors)
    test_ph2_auto_approval(errors)
    test_ph2_dry_run_gate(errors)
    test_ph2_status_projection(errors)
    test_ph2_takeover(errors)
    test_ph2_schema_contracts(errors)
    test_ph3_live_loop_positive(errors)
    test_ph3_negative_live_cases(errors)
    test_ph3_drift_and_completion_blocks(errors)
    test_ph3_multi_round_and_limits(errors)
    test_ph3_negative_fixture_semantics(errors)
    test_clw_st101_story_profile_and_split_gate(errors)
    if errors:
        print("DEVELOPMENT_RUNTIME_FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("DEVELOPMENT_RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
