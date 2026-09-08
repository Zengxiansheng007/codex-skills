"""End-to-end contract tests for the Development System full refactor."""

import json
import tempfile
from pathlib import Path

from development_runtime import (
    _sha256,
    GOVERNED_STATES,
    append_event,
    compute_policy_hash,
    decide_execution,
    evaluate_completion,
    evaluate_merge,
    evaluate_verified_progress,
    resume_cycle,
    validate_artifact_envelope,
    validate_phase_story,
    validate_skill_interface,
    validate_transition,
    write_snapshot_atomic,
)


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "assets" / "fixtures" / "phase-story" / "full-refactor-baseline.json"
EXTERNAL_BASELINE = ROOT.parent.parent / "requirements" / "development-system-phase-story-requirements-final-2026-08-14.json"
EXPECTED_GOVERNED_STATES = [
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
]


def check(condition, message, errors):
    if not condition:
        errors.append(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_requirement_baseline(errors):
    check(BASELINE.exists(), f"requirements baseline missing: {BASELINE}", errors)
    if not BASELINE.exists():
        return
    data = load(BASELINE)
    check(data.get("status") == "confirmed-baseline", "requirements baseline is not confirmed", errors)
    check(len(data.get("functionalRequirements", [])) == 32, "expected FR-001..FR-032", errors)
    check(len(data.get("nonFunctionalRequirements", [])) == 8, "expected NFR-001..NFR-008", errors)
    check(len(data.get("acceptanceCriteria", [])) == 34, "expected AC-001..AC-034", errors)
    phases = data.get("phases", [])
    stories = [story for phase in phases for story in phase.get("stories", [])]
    check(len(phases) == 7, "expected PH-01..PH-07", errors)
    check(len(stories) == 33, "expected 33 stories", errors)
    story_ids = {story.get("storyId") for story in stories}
    for phase in phases:
        check(bool(phase.get("entryCriteria")) and bool(phase.get("exitCriteria")), f"{phase.get('phaseId')} missing entry/exit", errors)
        for story in phase.get("stories", []):
            check(bool(story.get("mappedRequirements")), f"{story.get('storyId')} missing requirement trace", errors)
            check(bool(story.get("acceptanceCriteria")), f"{story.get('storyId')} missing AC trace", errors)
            for dependency in story.get("dependsOn", []):
                if dependency.startswith("PH") and "-ST-" in dependency:
                    check(dependency in story_ids, f"{story.get('storyId')} has unknown dependency {dependency}", errors)
    if EXTERNAL_BASELINE.exists():
        external = load(EXTERNAL_BASELINE)
        check(external.get("version") == data.get("version"), "portable baseline version differs from authority baseline", errors)
        external_map = {
            story["storyId"]: (story.get("mappedRequirements", []), story.get("acceptanceCriteria", []), story.get("dependsOn", []))
            for phase in external.get("phases", []) for story in phase.get("stories", [])
        }
        portable_map = {
            story["storyId"]: (story.get("mappedRequirements", []), story.get("acceptanceCriteria", []), story.get("dependsOn", []))
            for phase in phases for story in phase.get("stories", [])
        }
        check(external_map == portable_map, "portable baseline differs from authority Story trace", errors)


def test_schema_and_reference_inventory(errors):
    schemas = {
        "requirement-anchor.schema.json": ["anchorId", "authorityOrder", "frAc"],
        "artifact-envelope.schema.json": ["artifactId", "owner", "mappedFrAc"],
        "phase-story.schema.json": ["phaseId", "entryCriteria", "stories"],
        "runtime-state.schema.json": ["cycleId", "state", "circuitState"],
        "event-history.schema.json": ["sequenceIndex", "previousHash", "eventHash"],
        "snapshot.schema.json": ["lastSequenceIndex", "lastEventHash", "snapshotHash"],
        "completion-evaluation.schema.json": ["codexReviewPassed", "unmappedActions", "riskGatePassed", "feedback", "feedbackValidation", "feedbackHash", "schemaRef", "validatorId", "validatedAt"],
        "execution-slot.schema.json": ["workspaceFingerprint", "writeSet", "baselineFingerprint"],
        "role-profile.schema.json": ["profileId", "globallyDiscoverable", "entryGate"],
        "skill-interface.schema.json": ["inputSchemaRef", "outputSchemaRef", "statusMapping"],
        "resource-policy.schema.json": ["durationSeconds", "tokens", "concurrency"],
        "module-admission.schema.json": ["license", "testEvidence", "rollback"],
    }
    for name, fields in schemas.items():
        path = ROOT / "schemas" / name
        check(path.exists(), f"schema missing: {name}", errors)
        if not path.exists():
            continue
        data = load(path)
        check(data.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"{name} wrong draft", errors)
        text = path.read_text(encoding="utf-8")
        for field in fields:
            check(f'"{field}"' in text, f"{name} missing {field}", errors)

    runtime_schema = load(ROOT / "schemas" / "runtime-state.schema.json")
    anchor_schema = load(ROOT / "schemas" / "requirement-anchor.schema.json")
    check(runtime_schema["properties"]["state"]["enum"] == EXPECTED_GOVERNED_STATES, "runtime-state schema differs from DS-PSR-001", errors)
    check(anchor_schema["properties"]["nextState"]["enum"] == EXPECTED_GOVERNED_STATES, "requirement-anchor nextState differs from DS-PSR-001", errors)
    check(list(GOVERNED_STATES) == EXPECTED_GOVERNED_STATES, "runtime constant differs from DS-PSR-001", errors)

    report_builder_text = (ROOT / "scripts" / "build_refactor_reports.py").read_text(encoding="utf-8")
    check('"feedbackValid"' not in report_builder_text, "report builder still emits legacy feedbackValid", errors)
    for term in ["feedbackValidation", "feedbackHash", "evaluate_completion", "installationState"]:
        check(term in report_builder_text, f"report builder missing {term}", errors)

    references = {
        "handoff-interface-contract.md": ["handoff-system", "validate_skill_interface", "AC-034"],
        "rework-and-gate-reopen-contract.md": ["Artifact Owner", "route_rework", "AC-020"],
        "event-history-and-recovery-contract.md": ["Atomic Snapshot", "resume_cycle", "AC-024"],
        "state-and-completion-contract.md": ["CompletionEvaluator", "validate_transition", "AC-011"],
        "long-task-runtime-contract.md": ["Ralph L2", "HALF_OPEN", "ten rounds"],
        "workspace-and-approval-contract.md": ["preauthorization_matches", "User-level Skill installation", "AC-013"],
        "claude-first-execution-contract.md": ["Claude-first", "takeover", "AC-016"],
        "software-company-pipeline-contract.md": ["product-requirement", "project-planner", "qa"],
        "multi-agent-concurrency-contract.md": ["execution slot", "evaluate_merge", "AC-028"],
        "observability-and-resource-contract.md": ["status_projection", "resource-limit-reached", "build_audit_report"],
        "metagpt-module-admission.md": ["code-admission-candidate", "governance bypass", "AC-034"],
    }
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for name, terms in references.items():
        path = ROOT / "references" / name
        check(path.exists(), f"reference missing: {name}", errors)
        check(name in skill_text, f"SKILL.md does not link {name}", errors)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for term in terms:
                check(term in text, f"{name} missing {term}", errors)


def test_negative_fixture_encoding_and_trace(errors):
    negative = ROOT / "assets" / "fixtures" / "negative"
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
        "NEG-SLOT-001-shared-workspace.json",
        "NEG-MERGE-001-write-conflict.json",
        "NEG-METAGPT-001-missing-admission-evidence.json",
    }
    for name in required:
        path = negative / name
        check(path.exists(), f"negative fixture missing: {name}", errors)
        if not path.exists():
            continue
        check(not path.read_bytes().startswith(b"\xef\xbb\xbf"), f"{name} contains UTF-8 BOM", errors)
        data = load(path)
        check(data.get("expectedValidation") == "reject", f"{name} is not reject fixture", errors)
        check(bool(data.get("expectedRejectionRule")), f"{name} missing rejection rule", errors)
        check(bool(data.get("traceTo")), f"{name} missing traceTo", errors)


def test_vertical_slice(errors):
    artifact = {
        "artifactId": "ART-E2E-1", "version": "1.0", "artifactType": "implementation",
        "owner": "engineer", "sourceAnchorId": "A1", "sourceAnchorVersion": "1.0",
        "mappedFrAc": ["FR-024", "AC-014"], "createdAt": "2026-08-16T00:00:00+08:00",
        "derivedFrom": ["ST-1"],
    }
    check(not validate_artifact_envelope(artifact), "vertical slice artifact rejected", errors)

    phase = {
        "phaseId": "PH-02", "goal": "single story", "entryCriteria": ["PH-01 passed"],
        "exitCriteria": ["AC-014 evidence"],
        "stories": [{
            "storyId": "PH2-ST-003", "title": "live loop", "goal": "execute one story",
            "mappedRequirements": ["FR-010"], "acceptanceCriteria": ["AC-014"],
            "dependsOn": [], "testability": "feedback and QA", "evidenceRequirements": ["manifest", "feedback"],
        }],
    }
    check(not validate_phase_story(phase), "vertical slice phase/story rejected", errors)

    policy = {
        "policyId": "POL-VERTICAL-001", "version": "1.0", "status": "active",
        "validFrom": "2026-08-16T00:00:00+08:00", "expiresAt": "2099-01-01T00:00:00+08:00",
        "workspaceRoots": [str(ROOT)], "actions": ["read", "edit", "test"],
        "data": ["workspace-source"], "network": ["public-docs"],
        "tools": ["python", "claude"], "credentialBoundary": "inherit-claude-auth-only",
        "feedbackSchema": "feedback-packet.schema.json", "maxTimeoutSeconds": 900,
        "maxRounds": 1, "maxConcurrency": 1, "maxTakeovers": 1,
        "stopConditions": ["p0-drift", "timeout"], "codexTakeoverAllowed": True,
        "crossProjectReuse": False,
    }
    policy["policyHash"] = compute_policy_hash(policy)
    task = {
        "signals": ["skillDevelopment"],
        "requiredAuthorization": {
            "policyId": policy["policyId"], "policyHash": policy["policyHash"],
            "workspace": str(ROOT), "actions": ["read", "edit", "test"],
            "data": ["workspace-source"], "network": ["public-docs"],
            "tools": ["python", "claude"], "credentialBoundary": "inherit-claude-auth-only",
            "feedbackSchema": "feedback-packet.schema.json", "timeoutSeconds": 600,
            "rounds": 1, "concurrency": 1, "stopConditions": ["p0-drift", "timeout"],
        },
    }
    check(decide_execution(task, policy, True)["decision"] == "claude-first", "vertical slice did not select Claude-first", errors)

    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "events.jsonl"
        snapshot_path = Path(tmp) / "snapshot.json"
        event = append_event(history, {
            "eventType": "story-validated", "cycleId": "C1", "actor": "Codex",
            "phaseId": "PH-02", "storyId": "PH2-ST-003", "roundNumber": 1,
            "trace": ["AC-014"], "evidenceRefs": ["EV-1"],
        })
        write_snapshot_atomic(snapshot_path, {
            "cycleId": "C1", "anchorId": "A1", "anchorVersion": "1.0",
            "workspaceFingerprint": "W1", "lastSequenceIndex": event["sequenceIndex"],
            "lastEventHash": event["eventHash"], "state": "running", "phaseId": "PH-02",
            "storyId": "PH2-ST-003", "roundNumber": 1, "heartbeatAt": "fresh",
            "evidenceRefs": ["EV-1"], "nextAction": "completion-review",
        })
        check(resume_cycle(history, snapshot_path, "A1", "1.0", "W1", True)["resumable"], "vertical slice recovery rejected", errors)

    check(evaluate_verified_progress({"mappedFrAc": ["AC-014"], "validationPassed": True, "evidenceRefs": ["EV-1"], "stateImproved": True})["verified"], "vertical slice progress not verified", errors)
    check(evaluate_merge({"baselineBefore": "B1", "baselineCurrent": "B1", "writeSetConflicts": [], "evidenceRefs": ["EV-1"], "validationPassed": True, "storyId": "PH2-ST-003", "mappedFrAc": ["AC-014"]})["mergeAllowed"], "vertical slice merge rejected", errors)

    interface = {
        "skillName": "handoff-system", "version": "1.0", "owner": "handoff-system",
        "inputSchemaRef": "handoff-packet.schema.json", "outputSchemaRef": "feedback-packet.schema.json",
        "allowedActions": ["execute"], "forbiddenActions": ["complete"],
        "evidenceContract": ["manifest", "feedback"], "statusMapping": {"continue": "running"},
    }
    check(not validate_skill_interface(interface), "vertical slice independent Skill interface rejected", errors)

    completion_feedback = {"packetId": "FB-VS-001", "result": "completed", "evidenceRefs": ["EV-1"]}
    completion = {
        "allStoriesPassed": True, "allAcceptanceCriteriaVerified": True,
        "feedback": completion_feedback,
        "feedbackValidation": {
            "schemaRef": "feedback-packet.schema.json",
            "validatorId": "handoff-feedback-reviewer",
            "feedbackHash": _sha256(completion_feedback),
            "ok": True, "errorCount": 0,
            "validatedAt": "2026-08-15T00:00:00+00:00",
        },
        "evidenceComplete": True, "qaPassed": True, "driftSeverity": "none", "unmappedActions": [],
        "permissionGatePassed": True, "riskGatePassed": True, "codexReviewPassed": True,
    }
    check(evaluate_completion(completion)["state"] == "completed", "vertical slice completion failed", errors)
    check(validate_transition("running", "completed", "Codex", completion)["allowed"], "vertical slice completion transition rejected", errors)


def main():
    errors = []
    test_requirement_baseline(errors)
    test_schema_and_reference_inventory(errors)
    test_negative_fixture_encoding_and_trace(errors)
    test_vertical_slice(errors)
    if errors:
        print("FULL_REFACTOR_CONTRACT_FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("FULL_REFACTOR_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
