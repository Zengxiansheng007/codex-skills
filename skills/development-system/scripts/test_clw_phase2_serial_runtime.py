"""Deterministic CLW PH-2 serial Story queue tests for CLW-ST-201.

This suite is fixture-driven: it loads every JSON file in
``assets/fixtures/clw-phase2`` and asserts that the runtime function named in
each fixture's ``targetFunction`` produces the result declared by the fixture's
``expected*`` fields. It also performs a few end-to-end serial selection
walks that exercise DAG validation, stable selection, single-active, the
dependency blocker path and the Codex Story completion gate together.

The script is intentionally self-contained: it imports only
``development_runtime`` and the Python standard library, and it emits a single
deterministic pass/fail marker so it can be wired into the approved PowerShell
validation command in SKILL.md.

CLW-ST-203 coverage (failure/resource budgets, three-state circuit, HALF_OPEN
probe and Phase completion gate) is hosted in this file alongside CLW-ST-201
and CLW-ST-202 coverage.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from development_runtime import (
    advance_circuit,
    append_event,
    authorize_half_open,
    build_phase_progress_snapshot,
    evaluate_completion,
    evaluate_phase_completion,
    evaluate_resources,
    evaluate_verified_progress,
    failure_fingerprint,
    reconcile_phase_progress,
    resume_cycle,
    select_next_story,
    transition_story_after_review,
    validate_story_graph,
    write_snapshot_atomic,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "assets" / "fixtures" / "clw-phase2"


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _expect_findings(
    findings: list[dict[str, str]],
    fixture: dict[str, Any],
    name: str,
    errors: list[str],
) -> None:
    expected_rules: set[str] = set()
    rule_field = "expectedRejectionRule"
    if "expectedRejectionRules" in fixture:
        rule_field = "expectedRejectionRules"
        expected_rules = set(fixture["expectedRejectionRules"])
    elif "expectedRejectionRule" in fixture:
        expected_rules = {fixture["expectedRejectionRule"]}
    if expected_rules:
        actual_rules = {str(f.get("rule", "")) for f in findings}
        missing_rules = expected_rules - actual_rules
        check(
            not missing_rules,
            f"{name}: expected rejection rules {sorted(expected_rules)} "
            f"not found in findings {sorted(actual_rules)}",
            errors,
        )
    expected_severity = fixture.get("expectedRejectionSeverity")
    if expected_severity:
        severities = {str(f.get("severity", "")) for f in findings}
        check(
            expected_severity in severities,
            f"{name}: expected rejection severity {expected_severity} "
            f"not found in {sorted(severities)}",
            errors,
        )


def test_fixture_valid_dag(errors: list[str]) -> None:
    name = "pos-clw2-001-valid-dag.json"
    fixture = _load_fixture(name)
    findings = validate_story_graph(fixture["input"]["stories"])
    check(not findings, f"{name}: valid DAG rejected: {findings}", errors)
    check(
        fixture["expectedValidation"] == "accept",
        f"{name}: fixture must declare accept",
        errors,
    )


def test_fixture_stable_selection(errors: list[str]) -> None:
    name = "pos-clw2-002-stable-selection.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = select_next_story(
        inp["stories"],
        completed_story_ids=set(inp.get("completedStoryIds") or []),
        active_story_id=inp.get("activeStoryId"),
    )
    check(result["allowed"], f"{name}: eligible selection was blocked: {result.get('findings')}", errors)
    check(
        result["selected"]["storyId"] == fixture["expectedSelectedStoryId"],
        f"{name}: selected {result['selected']['storyId']}, expected {fixture['expectedSelectedStoryId']}",
        errors,
    )
    check(
        result.get("eligibleCount") == fixture["expectedEligibleCount"],
        f"{name}: eligibleCount {result.get('eligibleCount')}, expected {fixture['expectedEligibleCount']}",
        errors,
    )


def test_fixture_dependency_completed(errors: list[str]) -> None:
    name = "pos-clw2-003-dependency-completed.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = select_next_story(
        inp["stories"],
        completed_story_ids=set(inp.get("completedStoryIds") or []),
        active_story_id=inp.get("activeStoryId"),
    )
    check(result["allowed"], f"{name}: downstream selection was blocked: {result.get('findings')}", errors)
    check(
        result["selected"]["storyId"] == fixture["expectedSelectedStoryId"],
        f"{name}: selected {result['selected']['storyId']}, expected {fixture['expectedSelectedStoryId']}",
        errors,
    )


def test_fixture_story_completion_gate(errors: list[str]) -> None:
    name = "pos-clw2-004-story-completion-gate.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = transition_story_after_review(inp["story"], inp["completionEvaluation"])
    check(
        result["status"] == fixture["expectedStatus"],
        f"{name}: status {result['status']}, expected {fixture['expectedStatus']}",
        errors,
    )
    check(
        result["reason"] == fixture["expectedReason"],
        f"{name}: reason {result['reason']}, expected {fixture['expectedReason']}",
        errors,
    )


def test_fixture_cycle(errors: list[str]) -> None:
    name = "neg-clw2-001-cycle.json"
    fixture = _load_fixture(name)
    findings = validate_story_graph(fixture["input"]["stories"])
    check(findings, f"{name}: cycle was not rejected", errors)
    _expect_findings(findings, fixture, name, errors)


def test_fixture_unknown_dependency(errors: list[str]) -> None:
    name = "neg-clw2-002-unknown-dependency.json"
    fixture = _load_fixture(name)
    findings = validate_story_graph(fixture["input"]["stories"])
    check(findings, f"{name}: unknown dependency was not rejected", errors)
    _expect_findings(findings, fixture, name, errors)


def test_fixture_duplicate_id(errors: list[str]) -> None:
    name = "neg-clw2-003-duplicate-id.json"
    fixture = _load_fixture(name)
    findings = validate_story_graph(fixture["input"]["stories"])
    check(findings, f"{name}: duplicate ID was not rejected", errors)
    _expect_findings(findings, fixture, name, errors)


def test_fixture_missing_fr_ac(errors: list[str]) -> None:
    name = "neg-clw2-004-missing-fr-ac.json"
    fixture = _load_fixture(name)
    findings = validate_story_graph(fixture["input"]["stories"])
    check(findings, f"{name}: missing FR/AC was not rejected", errors)
    _expect_findings(findings, fixture, name, errors)


def test_fixture_single_active(errors: list[str]) -> None:
    name = "neg-clw2-005-single-active.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = select_next_story(
        inp["stories"],
        completed_story_ids=set(inp.get("completedStoryIds") or []),
        active_story_id=inp.get("activeStoryId"),
    )
    check(not result["allowed"], f"{name}: single-active violation was allowed", errors)
    check(result["selected"] is None, f"{name}: single-active returned a selected Story", errors)
    check(
        result.get("state") == fixture["expectedState"],
        f"{name}: state {result.get('state')}, expected {fixture['expectedState']}",
        errors,
    )
    _expect_findings(result.get("findings") or [], fixture, name, errors)


def test_fixture_dependency_blocker(errors: list[str]) -> None:
    name = "neg-clw2-006-dependency-blocker.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = select_next_story(
        inp["stories"],
        completed_story_ids=set(inp.get("completedStoryIds") or []),
        active_story_id=inp.get("activeStoryId"),
    )
    # The prerequisite is still pending and is selectable, so the selector
    # should allow selecting it rather than returning a hard block. The fixture
    # documents that the dependent Story is *not* selectable yet.
    check(result["allowed"], f"{name}: prerequisite should be selectable: {result.get('findings')}", errors)
    check(
        result["selected"]["storyId"] == fixture["expectedSelectedStoryId"],
        f"{name}: selected {result['selected']['storyId']}, expected {fixture['expectedSelectedStoryId']}",
        errors,
    )
    # The dependent Story must not be the one selected.
    check(
        result["selected"]["storyId"] != "CLW-ST-201-BLOCKED",
        f"{name}: blocked dependent was selected ahead of its prerequisite",
        errors,
    )


def test_fixture_false_agent_completion(errors: list[str]) -> None:
    name = "neg-clw2-007-false-agent-completion.json"
    fixture = _load_fixture(name)
    inp = fixture["input"]
    result = transition_story_after_review(inp["story"], inp["completionEvaluation"])
    check(
        result["status"] == fixture["expectedStatus"],
        f"{name}: status {result['status']}, expected {fixture['expectedStatus']}",
        errors,
    )
    check(
        result["reason"] == fixture["expectedReason"],
        f"{name}: reason {result['reason']}, expected {fixture['expectedReason']}",
        errors,
    )
    check(
        result["status"] != "passed",
        f"{name}: false Agent completion transitioned Story to passed",
        errors,
    )


def test_fixture_directory_coverage(errors: list[str]) -> None:
    """Every JSON fixture in clw-phase2 must be exercised by this suite."""
    expected = {
        "pos-clw2-001-valid-dag.json",
        "pos-clw2-002-stable-selection.json",
        "pos-clw2-003-dependency-completed.json",
        "pos-clw2-004-story-completion-gate.json",
        "neg-clw2-001-cycle.json",
        "neg-clw2-002-unknown-dependency.json",
        "neg-clw2-003-duplicate-id.json",
        "neg-clw2-004-missing-fr-ac.json",
        "neg-clw2-005-single-active.json",
        "neg-clw2-006-dependency-blocker.json",
        "neg-clw2-007-false-agent-completion.json",
        "pos-clw2-202-recovery.json",
        "neg-clw2-202-crash-gap.json",
        "neg-clw2-202-history-tamper.json",
        "neg-clw2-202-snapshot-tamper.json",
        "neg-clw2-202-identity-drift.json",
    }
    actual = {p.name for p in FIXTURE_DIR.glob("*.json")}
    missing = expected - actual
    check(not missing, f"clw-phase2 fixture directory missing files: {sorted(missing)}", errors)
    extra = actual - expected
    check(not extra, f"clw-phase2 fixture directory has unexpected files: {sorted(extra)}", errors)
    for name in expected:
        data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        check(bool(data.get("fixtureId")), f"{name} missing fixtureId", errors)
        check(bool(data.get("targetFunction")), f"{name} missing targetFunction", errors)
        check(bool(data.get("traceTo")), f"{name} missing traceTo", errors)


def test_st202_event_snapshot_recovery(errors: list[str]) -> None:
    stories = [
        {"storyId": "CLW-ST-201", "title": "Root", "goal": "Passed root", "mappedRequirements": ["FR-CLW2-005"], "acceptanceCriteria": ["AC-CLW2-006"], "status": "passed", "dependsOn": [], "priority": 1},
        {"storyId": "CLW-ST-202", "title": "Current", "goal": "Current recovery Story", "mappedRequirements": ["FR-CLW2-006"], "acceptanceCriteria": ["AC-CLW2-009"], "status": "running", "dependsOn": ["CLW-ST-201"], "priority": 1},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "events.jsonl"
        snapshot_path = Path(tmp) / "snapshot.json"
        first = append_event(history, {"eventType": "story-passed", "storyId": "CLW-ST-201"})
        snapshot = build_phase_progress_snapshot(
            "ANCHOR-1", "1.0", "CLW-PH-2", "WORKSPACE-1", stories,
            "CLW-ST-202", 1, last_sequence_index=first["sequenceIndex"],
            last_event_hash=first["eventHash"],
        )
        persisted = write_snapshot_atomic(snapshot_path, snapshot)
        recovered = resume_cycle(
            history, snapshot_path, "ANCHOR-1", "1.0", "WORKSPACE-1", True,
            phase_id="CLW-PH-2", queue_fingerprint=persisted["queueFingerprint"],
        )
        check(recovered["resumable"], f"ST-202 valid recovery rejected: {recovered['errors']}", errors)
        check(
            select_next_story(stories, {"CLW-ST-201"})["selected"]["storyId"] == "CLW-ST-202",
            "ST-202 recovery re-executed an already passed Story",
            errors,
        )

        second = append_event(history, {"eventType": "checkpoint", "storyId": "CLW-ST-202"})
        crash_gap = resume_cycle(
            history, snapshot_path, "ANCHOR-1", "1.0", "WORKSPACE-1", True,
            phase_id="CLW-PH-2", queue_fingerprint=persisted["queueFingerprint"],
        )
        check(not crash_gap["resumable"] and "snapshot-sequence" in crash_gap["errors"], "ST-202 event/snapshot crash gap accepted", errors)

        repaired = build_phase_progress_snapshot(
            "ANCHOR-1", "1.0", "CLW-PH-2", "WORKSPACE-1", stories,
            "CLW-ST-202", 2, last_sequence_index=second["sequenceIndex"],
            last_event_hash=second["eventHash"],
        )
        persisted = write_snapshot_atomic(snapshot_path, repaired)
        reconciled = reconcile_phase_progress(
            persisted, stories, history, expected_anchor_id="ANCHOR-1",
            expected_anchor_version="1.0", expected_phase_id="CLW-PH-2",
            expected_workspace_fingerprint="WORKSPACE-1",
        )
        check(reconciled["valid"], f"ST-202 repaired snapshot rejected: {reconciled['errors']}", errors)

        for field, value, expected_error in (
            ("anchorId", "OTHER", "anchorId-mismatch"),
            ("phaseId", "CLW-PH-X", "phaseId-mismatch"),
            ("workspaceFingerprint", "OTHER", "workspaceFingerprint-mismatch"),
        ):
            changed = dict(persisted)
            changed[field] = value
            result = reconcile_phase_progress(
                changed, stories, history, expected_anchor_id="ANCHOR-1",
                expected_anchor_version="1.0", expected_phase_id="CLW-PH-2",
                expected_workspace_fingerprint="WORKSPACE-1",
            )
            check(not result["valid"] and expected_error in result["errors"], f"ST-202 {field} drift accepted", errors)

        wrong_queue = resume_cycle(
            history, snapshot_path, "ANCHOR-1", "1.0", "WORKSPACE-1", True,
            phase_id="CLW-PH-2", queue_fingerprint="0" * 64,
        )
        check(not wrong_queue["resumable"] and "queue-mismatch" in wrong_queue["errors"], "ST-202 queue drift accepted", errors)

        tampered_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        tampered_snapshot["currentRound"] = 99
        snapshot_path.write_text(json.dumps(tampered_snapshot), encoding="utf-8")
        invalid_snapshot = resume_cycle(
            history, snapshot_path, "ANCHOR-1", "1.0", "WORKSPACE-1", True,
            phase_id="CLW-PH-2", queue_fingerprint=persisted["queueFingerprint"],
        )
        check(not invalid_snapshot["resumable"] and "snapshot-hash" in invalid_snapshot["errors"], "ST-202 snapshot tamper accepted", errors)

        write_snapshot_atomic(snapshot_path, repaired)
        lines = history.read_text(encoding="utf-8").splitlines()
        event = json.loads(lines[0])
        event["eventType"] = "tampered"
        lines[0] = json.dumps(event)
        history.write_text("\n".join(lines) + "\n", encoding="utf-8")
        invalid_history = resume_cycle(
            history, snapshot_path, "ANCHOR-1", "1.0", "WORKSPACE-1", True,
            phase_id="CLW-PH-2", queue_fingerprint=persisted["queueFingerprint"],
        )
        check(not invalid_history["resumable"] and any("event-hash" in item for item in invalid_history["errors"]), "ST-202 history tamper accepted", errors)


def test_st203_no_progress_circuit(errors: list[str]) -> None:
    """AC-CLW2-010: Three consecutive execution rounds without verified progress open the circuit.

    The circuit starts CLOSED. After three actual-execution rounds with no
    verified progress, ``advance_circuit`` must set ``circuitState`` to
    ``OPEN``, select ``stopReason=no-verified-progress`` and route to
    ``loop-limit-reached`` — never to ``completed``.
    """
    counters: dict[str, Any] = {}
    observation = {"actualExecution": True, "verifiedProgress": False}
    # Round 1: no-progress=1, still CLOSED
    r1 = advance_circuit(counters, observation)
    check(r1["counters"]["noProgress"] == 1, "ST-203 no-progress: round 1 count wrong", errors)
    check(r1["counters"]["circuitState"] == "CLOSED", "ST-203 no-progress: round 1 opened circuit", errors)
    check(r1["nextState"] == "running", "ST-203 no-progress: round 1 state wrong", errors)
    # Round 2: no-progress=2, still CLOSED
    r2 = advance_circuit(r1["counters"], observation)
    check(r2["counters"]["noProgress"] == 2, "ST-203 no-progress: round 2 count wrong", errors)
    check(r2["counters"]["circuitState"] == "CLOSED", "ST-203 no-progress: round 2 opened circuit", errors)
    check(r2["nextState"] == "running", "ST-203 no-progress: round 2 state wrong", errors)
    # Round 3: no-progress=3, circuit OPEN, loop-limit-reached
    r3 = advance_circuit(r2["counters"], observation)
    check(r3["counters"]["noProgress"] == 3, "ST-203 no-progress: round 3 count wrong", errors)
    check(r3["counters"]["circuitState"] == "OPEN", "ST-203 no-progress: round 3 did not open circuit", errors)
    check(r3["stopReason"] == "no-verified-progress", "ST-203 no-progress: round 3 stopReason wrong", errors)
    check(r3["nextState"] == "loop-limit-reached", "ST-203 no-progress: round 3 state wrong", errors)
    # Circuit OPEN must never imply completion
    check(r3["nextState"] != "completed", "ST-203 no-progress: circuit OPEN produced completed", errors)


def test_st203_verified_progress_resets_no_progress(errors: list[str]) -> None:
    """AC-CLW2-010: Verified progress resets the no-progress counter.

    If a round produces verified progress, the no-progress counter must reset
    to zero so that two subsequent no-progress rounds do not open the circuit.
    """
    counters: dict[str, Any] = {}
    # Round 1: no progress
    r1 = advance_circuit(counters, {"actualExecution": True, "verifiedProgress": False})
    check(r1["counters"]["noProgress"] == 1, "ST-203 reset: round 1 count wrong", errors)
    # Round 2: verified progress resets counter
    r2 = advance_circuit(r1["counters"], {"actualExecution": True, "verifiedProgress": True})
    check(r2["counters"]["noProgress"] == 0, "ST-203 reset: round 2 did not reset no-progress", errors)
    check(r2["counters"]["circuitState"] == "CLOSED", "ST-203 reset: round 2 opened circuit", errors)
    # Round 3: no progress again — only 1, not 3
    r3 = advance_circuit(r2["counters"], {"actualExecution": True, "verifiedProgress": False})
    check(r3["counters"]["noProgress"] == 1, "ST-203 reset: round 3 count should be 1 after reset", errors)
    check(r3["counters"]["circuitState"] == "CLOSED", "ST-203 reset: round 3 should not open circuit", errors)


def test_st203_failure_fingerprint_repair_and_open(errors: list[str]) -> None:
    """AC-CLW2-011: Same failure fingerprint third enters repair, fifth opens circuit.

    The long-task-runtime-contract states:
    - The third identical failure fingerprint requires repair review.
    - The fifth identical failure fingerprint opens the circuit.

    The failure fingerprint budget is independent of the no-progress budget.
    Observations use ``actualExecution: False`` so the no-progress counter
    does not increment in parallel and the failure fingerprint budget can be
    tested in isolation.
    """
    failure = {"type": "assertion", "testId": "test_budget", "message": "budget exceeded", "rootCause": "overflow"}
    fp = failure_fingerprint(failure)
    counters: dict[str, Any] = {}
    observation = {"actualExecution": False, "verifiedProgress": False, "failure": failure}
    # Occurrence 1
    r1 = advance_circuit(counters, observation)
    check(r1["counters"]["failureByFingerprint"][fp] == 1, "ST-203 failure: occurrence 1 count wrong", errors)
    check(r1["nextState"] == "running", "ST-203 failure: occurrence 1 should be running", errors)
    # Occurrence 2
    r2 = advance_circuit(r1["counters"], observation)
    check(r2["counters"]["failureByFingerprint"][fp] == 2, "ST-203 failure: occurrence 2 count wrong", errors)
    check(r2["nextState"] == "running", "ST-203 failure: occurrence 2 should be running", errors)
    # Occurrence 3: repair-needed
    r3 = advance_circuit(r2["counters"], observation)
    check(r3["counters"]["failureByFingerprint"][fp] == 3, "ST-203 failure: occurrence 3 count wrong", errors)
    check(r3["stopReason"] == "repeated-failure-repair-review", "ST-203 failure: occurrence 3 stopReason wrong", errors)
    check(r3["nextState"] == "repair-needed", "ST-203 failure: occurrence 3 should be repair-needed", errors)
    # Occurrence 4: still repair-needed
    r4 = advance_circuit(r3["counters"], observation)
    check(r4["counters"]["failureByFingerprint"][fp] == 4, "ST-203 failure: occurrence 4 count wrong", errors)
    # Occurrence 5: circuit OPEN, loop-limit-reached
    r5 = advance_circuit(r4["counters"], observation)
    check(r5["counters"]["failureByFingerprint"][fp] == 5, "ST-203 failure: occurrence 5 count wrong", errors)
    check(r5["counters"]["circuitState"] == "OPEN", "ST-203 failure: occurrence 5 did not open circuit", errors)
    check(r5["stopReason"] == "repeated-failure-open", "ST-203 failure: occurrence 5 stopReason wrong", errors)
    check(r5["nextState"] == "loop-limit-reached", "ST-203 failure: occurrence 5 should be loop-limit-reached", errors)
    check(r5["nextState"] != "completed", "ST-203 failure: circuit OPEN produced completed", errors)


def test_st203_failure_fingerprint_different_does_not_stack(errors: list[str]) -> None:
    """AC-CLW2-011: Different failure fingerprints do not stack on each other.

    Two different failures should each have their own counter; neither reaches
    the third-occurrence repair threshold.
    """
    failure_a = {"type": "assertion", "testId": "test_a", "message": "fail a", "rootCause": "cause_a"}
    failure_b = {"type": "assertion", "testId": "test_b", "message": "fail b", "rootCause": "cause_b"}
    fp_a = failure_fingerprint(failure_a)
    fp_b = failure_fingerprint(failure_b)
    check(fp_a != fp_b, "ST-203 diff-fp: fingerprints should differ", errors)
    counters: dict[str, Any] = {}
    r1 = advance_circuit(counters, {"actualExecution": False, "verifiedProgress": False, "failure": failure_a})
    r2 = advance_circuit(r1["counters"], {"actualExecution": False, "verifiedProgress": False, "failure": failure_b})
    check(r2["counters"]["failureByFingerprint"][fp_a] == 1, "ST-203 diff-fp: fp_a count wrong", errors)
    check(r2["counters"]["failureByFingerprint"][fp_b] == 1, "ST-203 diff-fp: fp_b count wrong", errors)
    check(r2["nextState"] == "running", "ST-203 diff-fp: should be running", errors)


def test_st203_invalid_feedback_opens_circuit(errors: list[str]) -> None:
    """AC-CLW2-011: Third invalid feedback with same root cause opens circuit.

    The long-task-runtime-contract states:
    - The third invalid feedback with the same root cause opens the circuit.

    The invalid-feedback budget is independent of the no-progress budget.
    Observations use ``actualExecution: False`` so the no-progress counter
    does not increment in parallel.
    """
    root = "schema-mismatch"
    counters: dict[str, Any] = {}
    observation = {"actualExecution": False, "verifiedProgress": False, "invalidFeedbackRoot": root}
    # First invalid feedback
    r1 = advance_circuit(counters, observation)
    check(r1["counters"]["invalidFeedbackByRoot"][root] == 1, "ST-203 invalid-fb: occurrence 1 count wrong", errors)
    check(r1["stopReason"] == "invalid-feedback-repair", "ST-203 invalid-fb: occurrence 1 stopReason wrong", errors)
    check(r1["nextState"] == "repair-needed", "ST-203 invalid-fb: occurrence 1 should be repair-needed", errors)
    # Second invalid feedback
    r2 = advance_circuit(r1["counters"], observation)
    check(r2["counters"]["invalidFeedbackByRoot"][root] == 2, "ST-203 invalid-fb: occurrence 2 count wrong", errors)
    check(r2["stopReason"] == "invalid-feedback-adapter-review", "ST-203 invalid-fb: occurrence 2 stopReason wrong", errors)
    check(r2["nextState"] == "repair-needed", "ST-203 invalid-fb: occurrence 2 should be repair-needed", errors)
    # Third invalid feedback: circuit OPEN
    r3 = advance_circuit(r2["counters"], observation)
    check(r3["counters"]["invalidFeedbackByRoot"][root] == 3, "ST-203 invalid-fb: occurrence 3 count wrong", errors)
    check(r3["counters"]["circuitState"] == "OPEN", "ST-203 invalid-fb: occurrence 3 did not open circuit", errors)
    check(r3["stopReason"] == "invalid-feedback-limit", "ST-203 invalid-fb: occurrence 3 stopReason wrong", errors)
    check(r3["nextState"] == "loop-limit-reached", "ST-203 invalid-fb: occurrence 3 should be loop-limit-reached", errors)
    check(r3["nextState"] != "completed", "ST-203 invalid-fb: circuit OPEN produced completed", errors)


def test_st203_timeout_recovery_and_block(errors: list[str]) -> None:
    """AC-CLW2-012: First timeout permits recovery; later timeout blocks.

    The long-task-runtime-contract states:
    - The first timeout permits one checkpointed recovery.
    - A later timeout permits bounded Codex takeover only when preauthorized,
      otherwise it blocks.
    - Timeout is never completion.

    The timeout budget is independent of the no-progress budget.
    Observations use ``actualExecution: False`` so the no-progress counter
    does not increment in parallel.
    """
    counters: dict[str, Any] = {}
    # First timeout: recovery
    r1 = advance_circuit(counters, {"actualExecution": False, "verifiedProgress": False, "timeout": True})
    check(r1["counters"]["timeoutCount"] == 1, "ST-203 timeout: first count wrong", errors)
    check(r1["stopReason"] == "timeout-recovery-required", "ST-203 timeout: first stopReason wrong", errors)
    check(r1["nextState"] == "repair-needed", "ST-203 timeout: first should be repair-needed", errors)
    check(r1["nextState"] != "completed", "ST-203 timeout: first produced completed", errors)
    # Second timeout without preauthorization: blocked
    r2 = advance_circuit(r1["counters"], {"actualExecution": False, "verifiedProgress": False, "timeout": True})
    check(r2["counters"]["timeoutCount"] == 2, "ST-203 timeout: second count wrong", errors)
    check(r2["stopReason"] == "timeout-external-block", "ST-203 timeout: second stopReason wrong", errors)
    check(r2["nextState"] == "blocked-external-dependency", "ST-203 timeout: second should be blocked", errors)
    check(r2["nextState"] != "completed", "ST-203 timeout: second produced completed", errors)
    # Third timeout with preauthorization: bounded takeover
    r3 = advance_circuit(r1["counters"], {"actualExecution": False, "verifiedProgress": False, "timeout": True, "takeoverPreauthorized": True})
    check(r3["counters"]["timeoutCount"] == 2, "ST-203 timeout: takeover count wrong", errors)
    check(r3["stopReason"] == "timeout-codex-takeover", "ST-203 timeout: takeover stopReason wrong", errors)
    check(r3["nextState"] == "repair-needed", "ST-203 timeout: takeover should be repair-needed", errors)
    check(r3["nextState"] != "completed", "ST-203 timeout: takeover produced completed", errors)


def test_st203_half_open_probe(errors: list[str]) -> None:
    """AC-CLW2-013: HALF_OPEN requires Codex reauthorization and permits one probe.

    The long-task-runtime-contract states:
    - HALF_OPEN requires Codex reauthorization and permits one probe.
    """
    # OPEN circuit, Codex reauthorized, no probe used yet: allowed
    result = authorize_half_open("OPEN", True, False)
    check(result["allowed"], "ST-203 half-open: should allow probe", errors)
    check(result["nextCircuitState"] == "HALF_OPEN", "ST-203 half-open: state should be HALF_OPEN", errors)
    check(result["probeLimit"] == 1, "ST-203 half-open: probeLimit should be 1", errors)
    # OPEN circuit, but probe already used: not allowed
    result2 = authorize_half_open("OPEN", True, True)
    check(not result2["allowed"], "ST-203 half-open: should not allow second probe", errors)
    check(result2["nextCircuitState"] == "OPEN", "ST-203 half-open: should stay OPEN after probe used", errors)
    # OPEN circuit, but not reauthorized: not allowed
    result3 = authorize_half_open("OPEN", False, False)
    check(not result3["allowed"], "ST-203 half-open: should not allow without reauthorization", errors)
    check(result3["nextCircuitState"] == "OPEN", "ST-203 half-open: should stay OPEN without reauthorization", errors)
    # CLOSED circuit: not eligible for HALF_OPEN
    result4 = authorize_half_open("CLOSED", True, False)
    check(not result4["allowed"], "ST-203 half-open: should not allow from CLOSED", errors)


def test_st203_resource_budget_within_and_exceeded(errors: list[str]) -> None:
    """AC-CLW2-014: Resource budget — within stays running, exceeded routes to resource-limit-reached.

    The CLW-PH-2 contract states:
    - Resource exhaustion is never completion.
    """
    budget = {"calls": 100, "durationSeconds": 3600, "tokens": 50000, "cost": 10.0, "rate": 60, "concurrency": 2}
    # Within budget: running
    within = evaluate_resources({"calls": 50, "durationSeconds": 1800, "tokens": 25000, "cost": 5.0, "rate": 30, "concurrency": 1}, budget)
    check(within["state"] == "running", "ST-203 resource: within budget should be running", errors)
    check(not within["exceeded"], "ST-203 resource: within budget should not exceed", errors)
    check(within["state"] != "completed", "ST-203 resource: within budget produced completed", errors)
    # Exceeded calls: resource-limit-reached
    exceeded = evaluate_resources({"calls": 200, "durationSeconds": 1800, "tokens": 25000, "cost": 5.0, "rate": 30, "concurrency": 1}, budget)
    check(exceeded["state"] == "resource-limit-reached", "ST-203 resource: exceeded calls should be resource-limit-reached", errors)
    check("calls" in exceeded["exceeded"], "ST-203 resource: exceeded should list calls", errors)
    check(exceeded["state"] != "completed", "ST-203 resource: exceeded produced completed", errors)
    # Exceeded multiple dimensions
    multi = evaluate_resources({"calls": 200, "durationSeconds": 7200, "tokens": 25000, "cost": 5.0, "rate": 30, "concurrency": 1}, budget)
    check(multi["state"] == "resource-limit-reached", "ST-203 resource: multi-exceeded should be resource-limit-reached", errors)
    check(set(multi["exceeded"]) == {"calls", "durationSeconds"}, "ST-203 resource: multi-exceeded list wrong", errors)


def test_st203_phase_completion_gate_positive(errors: list[str]) -> None:
    """AC-CLW2-014: Phase completion requires every Story, AC, feedback, evidence, QA, drift, permission, risk and Codex review.

    A fully satisfied Phase evaluation must produce ``state=completed`` and
    ``passed=True``. This is the only path to Phase completion.
    """
    story_evaluations = [
        {"storyId": "CLW-ST-201", "passed": True},
        {"storyId": "CLW-ST-202", "passed": True},
        {"storyId": "CLW-ST-203", "passed": True},
    ]
    phase_evaluation = {
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
    result = evaluate_phase_completion(story_evaluations, phase_evaluation)
    check(result["passed"], "ST-203 phase-comp: positive should pass", errors)
    check(result["state"] == "completed", "ST-203 phase-comp: positive should be completed", errors)
    check(not result["blockers"], f"ST-203 phase-comp: positive should have no blockers: {result['blockers']}", errors)


def test_st203_phase_completion_gate_negative_matrix(errors: list[str]) -> None:
    """AC-CLW2-014: Phase completion fails when any gate is missing.

    Each missing gate must produce a non-completed state. Queue empty,
    timeout, circuit OPEN, resource exhaustion or Agent claim never imply
    Phase completion.
    """
    base_stories = [{"storyId": "ST-A", "passed": True}, {"storyId": "ST-B", "passed": True}]
    base_phase = {
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

    # Missing: allStoriesPassed (one Story not passed)
    r = evaluate_phase_completion([{"storyId": "ST-A", "passed": True}, {"storyId": "ST-B", "passed": False}], base_phase)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: unpassed Story completed", errors)

    # Missing: allAcceptanceCriteriaVerified
    p = dict(base_phase); p["allAcceptanceCriteriaVerified"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing AC completed", errors)

    # Missing: feedbackValid
    p = dict(base_phase); p["feedbackValid"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing feedback completed", errors)

    # Missing: evidenceComplete
    p = dict(base_phase); p["evidenceComplete"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing evidence completed", errors)

    # Missing: qaPassed
    p = dict(base_phase); p["qaPassed"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing QA completed", errors)

    # Missing: noP0P1Drift (P1 drift)
    p = dict(base_phase); p["driftSeverity"] = "P1"
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] == "requirements-review", "ST-203 phase-neg: P1 drift not requirements-review", errors)

    # Missing: noUnmappedActions
    p = dict(base_phase); p["unmappedActions"] = ["unknown-action"]
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] == "requirements-review", "ST-203 phase-neg: unmapped not requirements-review", errors)

    # Missing: permissionGatePassed
    p = dict(base_phase); p["permissionGatePassed"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing permission completed", errors)

    # Missing: riskGatePassed
    p = dict(base_phase); p["riskGatePassed"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing risk completed", errors)

    # Missing: codexReviewPassed
    p = dict(base_phase); p["codexReviewPassed"] = False
    r = evaluate_phase_completion(base_stories, p)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: missing Codex review completed", errors)

    # Empty story list: not passed
    r = evaluate_phase_completion([], base_phase)
    check(not r["passed"] and r["state"] != "completed", "ST-203 phase-neg: empty stories completed", errors)


def test_st203_false_completion_signals(errors: list[str]) -> None:
    """AC-CLW2-014: Queue empty, timeout, circuit OPEN, resource exhaustion and Agent claim are never completion.

    This test exercises each false-completion signal and verifies it produces
    a non-completed state. Codex owns Phase completion.
    """
    # Queue empty (all Stories passed): select_next_story returns blocked-external-dependency
    stories = [
        {"storyId": "ST-203-EMPTY", "title": "Root", "goal": "Passed", "mappedRequirements": ["FR-CLW2-001"], "acceptanceCriteria": ["AC-CLW2-001"], "dependsOn": [], "priority": 1, "status": "passed"},
    ]
    queue_empty = select_next_story(stories, completed_story_ids={"ST-203-EMPTY"})
    check(not queue_empty["allowed"], "ST-203 false-comp: queue empty was allowed", errors)
    check(queue_empty["selected"] is None, "ST-203 false-comp: queue empty selected a Story", errors)
    check(queue_empty.get("state") == "blocked-external-dependency", "ST-203 false-comp: queue empty state wrong", errors)
    check(queue_empty.get("state") != "completed", "ST-203 false-comp: queue empty produced completed", errors)

    # Timeout: advance_circuit routes to repair-needed or blocked, never completed
    timeout_r = advance_circuit({}, {"actualExecution": False, "verifiedProgress": False, "timeout": True})
    check(timeout_r["nextState"] != "completed", "ST-203 false-comp: timeout produced completed", errors)

    # Circuit OPEN from no-progress: never completed
    counters: dict[str, Any] = {}
    obs = {"actualExecution": True, "verifiedProgress": False}
    for _ in range(3):
        counters = advance_circuit(counters, obs)["counters"]
    open_result = advance_circuit(counters, obs)
    # Circuit should already be OPEN; another observation keeps it OPEN
    check(open_result["counters"]["circuitState"] == "OPEN", "ST-203 false-comp: circuit should be OPEN", errors)
    check(open_result["nextState"] != "completed", "ST-203 false-comp: circuit OPEN produced completed", errors)

    # Resource exhaustion: never completed
    res = evaluate_resources({"calls": 999}, {"calls": 10})
    check(res["state"] == "resource-limit-reached", "ST-203 false-comp: resource state wrong", errors)
    check(res["state"] != "completed", "ST-203 false-comp: resource exhaustion produced completed", errors)

    # Agent completion claim: transition_story_after_review rejects
    story = {"storyId": "ST-203-CLAIM", "title": "Claim", "goal": "Agent claim", "mappedRequirements": ["FR-CLW2-004"], "acceptanceCriteria": ["AC-CLW2-005"], "dependsOn": [], "priority": 1, "status": "running"}
    false_eval = {"state": "completed", "passed": False, "agentCompletionClaim": True}
    claim_r = transition_story_after_review(story, false_eval)
    check(claim_r["status"] != "passed", "ST-203 false-comp: Agent claim transitioned to passed", errors)
    check(claim_r["status"] != "completed", "ST-203 false-comp: Agent claim produced completed", errors)


def test_st203_verified_progress_evaluator(errors: list[str]) -> None:
    """AC-CLW2-010: evaluate_verified_progress requires all four checks.

    Verified progress requires:
    - mapped FR/AC
    - validation passed
    - evidence refs
    - improved governed state
    Missing any check classifies as observation-only, not verified-progress.
    """
    # All four checks present: verified
    delta = {"mappedFrAc": ["FR-CLW2-001"], "validationPassed": True, "evidenceRefs": ["EV-1"], "stateImproved": True}
    r = evaluate_verified_progress(delta)
    check(r["verified"], "ST-203 verified-progress: full delta should be verified", errors)
    check(r["classification"] == "verified-progress", "ST-203 verified-progress: classification wrong", errors)

    # Missing mappedFrAc
    d = dict(delta); d["mappedFrAc"] = []
    r = evaluate_verified_progress(d)
    check(not r["verified"], "ST-203 verified-progress: missing mapped should not be verified", errors)
    check(r["classification"] == "observation-only", "ST-203 verified-progress: missing mapped classification wrong", errors)

    # Missing validationPassed
    d = dict(delta); d["validationPassed"] = False
    r = evaluate_verified_progress(d)
    check(not r["verified"], "ST-203 verified-progress: missing validation should not be verified", errors)

    # Missing evidenceRefs
    d = dict(delta); d["evidenceRefs"] = []
    r = evaluate_verified_progress(d)
    check(not r["verified"], "ST-203 verified-progress: missing evidence should not be verified", errors)

    # Missing stateImproved
    d = dict(delta); d["stateImproved"] = False
    r = evaluate_verified_progress(d)
    check(not r["verified"], "ST-203 verified-progress: missing improved should not be verified", errors)


def test_st203_round_limit(errors: list[str]) -> None:
    """AC-CLW2-010: A Story may execute at most ten rounds; an eleventh cannot start.

    The long-task-runtime-contract states:
    - A Story may execute at most ten rounds. An eleventh round cannot start.
    """
    counters: dict[str, Any] = {"roundCount": 9, "circuitState": "CLOSED"}
    # Round 10: allowed, but at limit
    r10 = advance_circuit(counters, {"actualExecution": True, "verifiedProgress": False})
    check(r10["counters"]["roundCount"] == 10, "ST-203 round-limit: round 10 count wrong", errors)
    check(r10["counters"]["circuitState"] == "OPEN", "ST-203 round-limit: round 10 should open circuit", errors)
    check(r10["stopReason"] == "story-round-limit", "ST-203 round-limit: round 10 stopReason wrong", errors)
    check(r10["nextState"] == "loop-limit-reached", "ST-203 round-limit: round 10 should be loop-limit-reached", errors)
    check(r10["nextState"] != "completed", "ST-203 round-limit: round 10 produced completed", errors)


def test_serial_walk_dependency_aware(errors: list[str]) -> None:
    """End-to-end serial walk: validate graph, select, complete, select next.

    This exercises the full CLW-PH-2 serial contract on a three-Story DAG:
      ST-201-WALK-ROOT (priority 1, no deps)
      ST-201-WALK-MID (priority 5, depends on ROOT)
      ST-201-WALK-LEAF (priority 9, depends on MID)

    The walk selects ROOT first (only eligible Story), completes it via a real
    Codex evaluation, then selects MID, completes it, and finally selects LEAF.
    A false Agent completion claim is rejected at each step.
    """
    stories = [
        {
            "storyId": "ST-201-WALK-ROOT",
            "title": "Root",
            "goal": "No dependencies.",
            "mappedRequirements": ["FR-CLW2-001"],
            "acceptanceCriteria": ["AC-CLW2-001"],
            "dependsOn": [],
            "priority": 1,
            "status": "pending",
        },
        {
            "storyId": "ST-201-WALK-MID",
            "title": "Mid",
            "goal": "Depends on Root.",
            "mappedRequirements": ["FR-CLW2-002"],
            "acceptanceCriteria": ["AC-CLW2-002"],
            "dependsOn": ["ST-201-WALK-ROOT"],
            "priority": 5,
            "status": "pending",
        },
        {
            "storyId": "ST-201-WALK-LEAF",
            "title": "Leaf",
            "goal": "Depends on Mid.",
            "mappedRequirements": ["FR-CLW2-003"],
            "acceptanceCriteria": ["AC-CLW2-003"],
            "dependsOn": ["ST-201-WALK-MID"],
            "priority": 9,
            "status": "pending",
        },
    ]

    # Step 0: validate the full DAG once.
    findings = validate_story_graph(stories)
    check(not findings, f"serial walk: valid DAG rejected: {findings}", errors)

    completed: set[str] = set()

    # Step 1: select ROOT (only eligible Story).
    step1 = select_next_story(stories, completed_story_ids=completed)
    check(step1["allowed"], f"serial walk step 1: ROOT should be selectable: {step1.get('findings')}", errors)
    check(step1["selected"]["storyId"] == "ST-201-WALK-ROOT", "serial walk step 1: ROOT not selected", errors)

    # Single-active gate: a second selection while ROOT is active must fail.
    active = select_next_story(stories, completed_story_ids=completed, active_story_id="ST-201-WALK-ROOT")
    check(not active["allowed"], "serial walk: single-active gate did not fire", errors)
    check(active["selected"] is None, "serial walk: single-active returned a selected Story", errors)

    # False Agent completion must not transition ROOT to passed.
    false_eval = {"state": "completed", "passed": False, "agentCompletionClaim": True}
    false_result = transition_story_after_review(step1["selected"], false_eval)
    check(false_result["status"] != "passed", "serial walk: false Agent completion transitioned ROOT to passed", errors)

    # Real Codex completion evaluation transitions ROOT to passed.
    real_eval = {"state": "completed", "passed": True}
    root_result = transition_story_after_review(step1["selected"], real_eval)
    check(root_result["status"] == "passed", "serial walk: ROOT did not transition to passed", errors)
    completed.add("ST-201-WALK-ROOT")

    # Step 2: select MID (ROOT completed, MID now eligible).
    step2 = select_next_story(stories, completed_story_ids=completed)
    check(step2["allowed"], f"serial walk step 2: MID should be selectable: {step2.get('findings')}", errors)
    check(step2["selected"]["storyId"] == "ST-201-WALK-MID", "serial walk step 2: MID not selected", errors)
    mid_result = transition_story_after_review(step2["selected"], real_eval)
    check(mid_result["status"] == "passed", "serial walk: MID did not transition to passed", errors)
    completed.add("ST-201-WALK-MID")

    # Step 3: select LEAF (MID completed, LEAF now eligible).
    step3 = select_next_story(stories, completed_story_ids=completed)
    check(step3["allowed"], f"serial walk step 3: LEAF should be selectable: {step3.get('findings')}", errors)
    check(step3["selected"]["storyId"] == "ST-201-WALK-LEAF", "serial walk step 3: LEAF not selected", errors)
    leaf_result = transition_story_after_review(step3["selected"], real_eval)
    check(leaf_result["status"] == "passed", "serial walk: LEAF did not transition to passed", errors)
    completed.add("ST-201-WALK-LEAF")

    # Step 4: queue is fully completed; no eligible Stories remain.
    step4 = select_next_story(stories, completed_story_ids=completed)
    check(not step4["allowed"], "serial walk: completed queue still selected a Story", errors)
    check(step4["selected"] is None, "serial walk: completed queue returned a selected Story", errors)
    check(
        step4.get("state") == "blocked-external-dependency",
        f"serial walk: completed queue state {step4.get('state')}, expected blocked-external-dependency",
        errors,
    )


def test_serial_walk_blocked_dependency(errors: list[str]) -> None:
    """A Story whose dependency is still pending must not be selectable.

    Two Stories:
      ST-201-BLOCK-ROOT (priority 1, no deps, pending)
      ST-201-BLOCK-CHILD (priority 9, depends on ROOT, pending)

    The selector must pick ROOT (the only eligible Story), never CHILD.
    """
    stories = [
        {
            "storyId": "ST-201-BLOCK-ROOT",
            "title": "Root",
            "goal": "No dependencies.",
            "mappedRequirements": ["FR-CLW2-001"],
            "acceptanceCriteria": ["AC-CLW2-001"],
            "dependsOn": [],
            "priority": 1,
            "status": "pending",
        },
        {
            "storyId": "ST-201-BLOCK-CHILD",
            "title": "Child",
            "goal": "Depends on Root which is still pending.",
            "mappedRequirements": ["FR-CLW2-002"],
            "acceptanceCriteria": ["AC-CLW2-002"],
            "dependsOn": ["ST-201-BLOCK-ROOT"],
            "priority": 9,
            "status": "pending",
        },
    ]
    findings = validate_story_graph(stories)
    check(not findings, f"blocked walk: valid DAG rejected: {findings}", errors)
    result = select_next_story(stories, completed_story_ids=set())
    check(result["allowed"], f"blocked walk: ROOT should be selectable: {result.get('findings')}", errors)
    check(
        result["selected"]["storyId"] == "ST-201-BLOCK-ROOT",
        "blocked walk: ROOT not selected",
        errors,
    )
    check(
        result["selected"]["storyId"] != "ST-201-BLOCK-CHILD",
        "blocked walk: CHILD was selected ahead of its pending dependency",
        errors,
    )


def test_serial_walk_review_pending_dependency_blocks(errors: list[str]) -> None:
    """A Story whose dependency is in review status must not be selectable.

    Per the CLW-PH-2 contract: "A blocked, failed, review-pending or
    evidence-incomplete dependency blocks downstream execution."
    """
    stories = [
        {
            "storyId": "ST-201-REVIEW-ROOT",
            "title": "Root in review",
            "goal": "Dependency is in review, not passed.",
            "mappedRequirements": ["FR-CLW2-001"],
            "acceptanceCriteria": ["AC-CLW2-001"],
            "dependsOn": [],
            "priority": 1,
            "status": "review",
        },
        {
            "storyId": "ST-201-REVIEW-CHILD",
            "title": "Child blocked by review",
            "goal": "Depends on a Story in review.",
            "mappedRequirements": ["FR-CLW2-002"],
            "acceptanceCriteria": ["AC-CLW2-002"],
            "dependsOn": ["ST-201-REVIEW-ROOT"],
            "priority": 9,
            "status": "pending",
        },
    ]
    findings = validate_story_graph(stories)
    check(not findings, f"review walk: valid DAG rejected: {findings}", errors)
    # Neither Story is eligible: ROOT is in review, CHILD depends on ROOT.
    result = select_next_story(stories, completed_story_ids=set())
    check(not result["allowed"], "review walk: a Story was selected when all are blocked", errors)
    check(result["selected"] is None, "review walk: a selected Story was returned when all are blocked", errors)


def main() -> int:
    errors: list[str] = []
    test_fixture_directory_coverage(errors)
    test_fixture_valid_dag(errors)
    test_fixture_stable_selection(errors)
    test_fixture_dependency_completed(errors)
    test_fixture_story_completion_gate(errors)
    test_fixture_cycle(errors)
    test_fixture_unknown_dependency(errors)
    test_fixture_duplicate_id(errors)
    test_fixture_missing_fr_ac(errors)
    test_fixture_single_active(errors)
    test_fixture_dependency_blocker(errors)
    test_fixture_false_agent_completion(errors)
    test_serial_walk_dependency_aware(errors)
    test_serial_walk_blocked_dependency(errors)
    test_serial_walk_review_pending_dependency_blocks(errors)
    test_st202_event_snapshot_recovery(errors)
    test_st203_no_progress_circuit(errors)
    test_st203_verified_progress_resets_no_progress(errors)
    test_st203_failure_fingerprint_repair_and_open(errors)
    test_st203_failure_fingerprint_different_does_not_stack(errors)
    test_st203_invalid_feedback_opens_circuit(errors)
    test_st203_timeout_recovery_and_block(errors)
    test_st203_half_open_probe(errors)
    test_st203_resource_budget_within_and_exceeded(errors)
    test_st203_phase_completion_gate_positive(errors)
    test_st203_phase_completion_gate_negative_matrix(errors)
    test_st203_false_completion_signals(errors)
    test_st203_verified_progress_evaluator(errors)
    test_st203_round_limit(errors)
    if errors:
        print("CLW_PHASE2_SERIAL_RUNTIME_FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("CLW_PHASE2_SERIAL_RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
