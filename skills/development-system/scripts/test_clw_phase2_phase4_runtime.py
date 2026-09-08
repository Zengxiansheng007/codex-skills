"""Deterministic CLW PH-2, PH-3 and PH-4 contract tests."""

import json
import tempfile
from pathlib import Path

from development_runtime import (
    append_event,
    build_merge_candidate,
    build_phase_progress_snapshot,
    evaluate_declared_vs_observed_write_set,
    evaluate_phase_completion,
    match_agent_capability,
    normalize_write_set,
    reconcile_phase_progress,
    review_agent_feedback,
    schedule_isolated_slots,
    select_next_story,
    transition_story_after_review,
    validate_agent_profile,
    validate_execution_slot,
    validate_story_graph,
)


def check(condition, message, errors):
    if not condition:
        errors.append(message)


def story(story_id, depends_on=None, priority=0, status="pending"):
    return {
        "storyId": story_id,
        "title": story_id,
        "goal": "deterministic fixture",
        "mappedRequirements": ["FR-" + story_id],
        "acceptanceCriteria": ["AC-" + story_id],
        "dependsOn": list(depends_on or []),
        "priority": priority,
        "status": status,
    }


def test_phase2(errors):
    stories = [story("ST-A", priority=1), story("ST-B", ["ST-A"], priority=5), story("ST-C", priority=2)]
    check(not validate_story_graph(stories), "valid Story graph rejected", errors)
    selected = select_next_story(stories, set())
    check(selected["allowed"] and selected["selected"]["storyId"] == "ST-C", "stable priority/ID selection failed", errors)
    active = select_next_story(stories, set(), active_story_id="ST-A")
    check(not active["allowed"] and active["findings"][0]["rule"] == "single-active-story", "single active Story gate failed", errors)

    bad = [story("ST-A", ["UNKNOWN"]), story("ST-A")]
    rules = {finding["rule"] for finding in validate_story_graph(bad)}
    check({"story-id-duplicate", "story-dependency-unknown"}.issubset(rules), "duplicate/unknown dependency not rejected", errors)

    passed = transition_story_after_review(stories[0], {"state": "completed", "passed": True})
    rejected = transition_story_after_review(stories[0], {"state": "completed", "passed": False})
    check(passed["status"] == "passed" and rejected["status"] != "passed", "Story completion gate can be bypassed", errors)

    snapshot = build_phase_progress_snapshot("A1", "1.0", "PH-2", "W1", stories, "ST-C", 1)
    check(reconcile_phase_progress(snapshot, stories)["valid"], "valid phase snapshot rejected", errors)
    changed = json.loads(json.dumps(snapshot))
    changed["queueFingerprint"] = "0" * 64
    check(not reconcile_phase_progress(changed, stories)["valid"], "tampered queue fingerprint accepted", errors)
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "events.jsonl"
        event = append_event(history, {"eventType": "story-selected", "cycleId": "C1", "trace": ["FR-CLW2-003"]})
        stale = reconcile_phase_progress(snapshot, stories, history)
        check(
            not stale["valid"] and "history:snapshot-sequence" in stale["errors"],
            "stale pre-event snapshot was accepted",
            errors,
        )
        aligned_snapshot = build_phase_progress_snapshot(
            "A1", "1.0", "PH-2", "W1", stories, "ST-C", 1,
            last_sequence_index=event["sequenceIndex"],
            last_event_hash=event["eventHash"],
        )
        check(
            reconcile_phase_progress(aligned_snapshot, stories, history)["valid"],
            "event-aligned history reconciliation failed",
            errors,
        )

    phase_pass = evaluate_phase_completion(
        [{"storyId": "ST-A", "passed": True}, {"storyId": "ST-B", "passed": True}],
        {"allAcceptanceCriteriaVerified": True, "feedbackValid": True, "evidenceComplete": True, "qaPassed": True,
         "driftSeverity": "none", "unmappedActions": [], "permissionGatePassed": True, "riskGatePassed": True,
         "codexReviewPassed": True},
    )
    check(phase_pass["passed"] and phase_pass["state"] == "completed", "valid Phase completion rejected", errors)
    phase_fail = evaluate_phase_completion([{"passed": True}], {"allAcceptanceCriteriaVerified": True})
    check(not phase_fail["passed"], "incomplete Phase was marked completed", errors)


def test_phase3(errors):
    norm = normalize_write_set(["SRC\\One.py", "src/two.py"])
    check(norm["valid"] and norm["paths"] == ["src/one.py", "src/two.py"], "Windows write set normalization failed", errors)
    check(not normalize_write_set(["src", "src/one.py"])["valid"], "parent-child overlap accepted", errors)
    check(not normalize_write_set(["../escape.py"])["valid"], "path escape accepted", errors)

    slots = []
    for sid, path, branch, write_set in (
        ("ST-A", "W-A", "slot/a", ["src/a.py"]),
        ("ST-B", "W-B", "slot/b", ["src/b.py"]),
        ("ST-C", "W-C", "slot/c", ["src/c.py"]),
    ):
        slots.append({**story(sid), "parallelEligible": True, "workspaceFingerprint": path, "branch": branch, "writeSet": write_set})
    schedule = schedule_isolated_slots(slots, set(), max_slots=2)
    check([s["storyId"] for s in schedule["scheduled"]] == ["ST-A", "ST-B"], "bounded stable slot scheduling failed", errors)
    check(schedule["blocked"][0]["reasons"] == ["concurrency-limit"], "third slot was not bounded", errors)

    conflict = [
        {**story("ST-A"), "parallelEligible": True, "workspaceFingerprint": "W-A", "branch": "slot/a", "writeSet": ["src"]},
        {**story("ST-B"), "parallelEligible": True, "workspaceFingerprint": "W-B", "branch": "slot/b", "writeSet": ["src/b.py"]},
    ]
    blocked = schedule_isolated_slots(conflict, set(), max_slots=2)
    check(blocked["blocked"] and "write-set-conflict" in blocked["blocked"][0]["reasons"], "cross-slot parent-child conflict accepted", errors)

    slot = {
        "slotId": "S1", "storyId": "ST-A", "agentId": "claude", "worktreePath": "C:/approved/s1",
        "branch": "slot/a", "workspaceFingerprint": "W-A", "baselineFingerprint": "BASE", "permissionPolicy": "P1",
        "declaredWriteSet": ["src/a.py"], "state": "running", "mappedFrAc": ["FR-A", "AC-A"],
    }
    check(not validate_execution_slot(slot, "C:/approved"), "valid execution slot rejected", errors)
    check(validate_execution_slot({**slot, "agentMayMerge": True}, "C:/approved"), "Agent merge permission accepted", errors)
    drift = evaluate_declared_vs_observed_write_set(["src/a.py"], ["src/b.py"])
    check(not drift["allowed"] and drift["state"] == "requirements-review", "observed write-set drift accepted", errors)
    candidate = build_merge_candidate(slot, "HEAD", "d" * 64, [{"id": "T1", "passed": True}], ["EV-1"])
    check(len(candidate["candidateHash"]) == 64 and candidate["storyId"] == "ST-A", "merge candidate identity missing", errors)


def test_phase4(errors):
    profile = {
        "profileId": "midscene-windows-v1", "agentId": "midscene", "adapterId": "handoff-midscene-executor",
        "version": "1.0", "capabilities": ["ui-observe", "ui-act"], "inputSchemaRef": "handoff-packet.schema.json",
        "outputSchemaRef": "feedback-packet.schema.json", "allowedActions": ["observe", "click"],
        "forbiddenActions": ["install", "publish"], "statusMapping": {"done": "running"},
        "completionAuthorityIsolated": True,
    }
    check(not validate_agent_profile(profile), "valid Agent profile rejected", errors)
    bad = {**profile, "completionAuthorityIsolated": False, "allowedActions": ["install"]}
    check(any(item["severity"] == "P0" for item in validate_agent_profile(bad)), "unsafe Agent profile accepted", errors)
    matched = match_agent_capability({"capabilities": ["ui-observe"], "actions": ["observe"]}, profile)
    denied = match_agent_capability({"capabilities": ["ui-observe"], "actions": ["publish"]}, profile)
    check(matched["matched"] and not denied["matched"], "capability/permission match failed", errors)
    missing_cap = match_agent_capability({"capabilities": ["ui-observe", "ui-admin"], "actions": ["observe"]}, profile)
    check(not missing_cap["matched"] and missing_cap["state"] == "risk-gate-required" and "ui-admin" in missing_cap["missingCapabilities"], "missing capability did not fail closed", errors)
    for field in ("profileId", "agentId", "adapterId", "version", "capabilities", "inputSchemaRef", "outputSchemaRef", "allowedActions", "forbiddenActions", "statusMapping"):
        incomplete = dict(profile)
        incomplete.pop(field)
        check(any(item["rule"] == "agent-profile-required" and item["message"] == field for item in validate_agent_profile(incomplete)), f"missing profile field {field} was not rejected", errors)
    check(any(item["severity"] == "P0" for item in validate_agent_profile(profile, [profile])), "duplicate Agent identity was accepted", errors)
    overlap = {**profile, "allowedActions": ["observe"], "forbiddenActions": ["observe"]}
    check(any(item["rule"] == "agent-action-overlap" for item in validate_agent_profile(overlap)), "allow/deny action overlap was accepted", errors)
    feedback = {"cycleId": "C1", "storyId": "ST-1", "status": "running", "evidenceRefs": ["EV-1"]}
    check(review_agent_feedback(feedback, {"cycleId": "C1", "storyId": "ST-1"})["accepted"], "valid unified feedback rejected", errors)
    stale = review_agent_feedback({**feedback, "cycleId": "OLD"}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not stale["accepted"] and stale["state"] == "requirements-review", "stale Agent feedback accepted", errors)
    missing_evidence = review_agent_feedback({"cycleId": "C1", "storyId": "ST-1", "status": "running"}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not missing_evidence["accepted"] and missing_evidence["state"] == "repair-needed", "missing feedback evidence did not route to repair", errors)
    unmapped = review_agent_feedback({**feedback, "unmappedActions": ["publish"]}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not unmapped["accepted"] and unmapped["state"] == "repair-needed", "unmapped action was accepted", errors)
    drift_p1 = review_agent_feedback({**feedback, "driftSeverity": "P1"}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not drift_p1["accepted"] and drift_p1["state"] == "repair-needed", "P1 drift did not route to repair", errors)
    drift_p0 = review_agent_feedback({**feedback, "driftSeverity": "P0"}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not drift_p0["accepted"] and drift_p0["state"] == "requirements-review", "P0 drift did not route to requirements review", errors)
    claim = review_agent_feedback({**feedback, "status": "completed", "completionClaim": True}, {"cycleId": "C1", "storyId": "ST-1"})
    check(not claim["accepted"] and claim["state"] == "repair-needed", "Agent completion claim bypassed review", errors)


def main():
    errors = []
    test_phase2(errors)
    test_phase3(errors)
    test_phase4(errors)
    if errors:
        print("CLW_PHASE2_PHASE4_RUNTIME_FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("CLW_PHASE2_PHASE4_RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
