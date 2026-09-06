"""Synthetic V2 ledger tests; every formal-file mutation stays inside TemporaryDirectory."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from grill_artifact_checks import BoundaryError
from grill_session_runtime import (
    LedgerError,
    _fingerprint,
    _decision_fingerprint,
    close_session,
    consume_exception,
    create_checkpoint,
    create_exception,
    finish_exception,
    main,
    reconcile_format_only_drift,
    ensure_mutable_ledger,
    new_ledger,
    pause_session,
    render_report,
    reopen_question,
    resume_session,
    start_writeback,
    validate_ledger,
    verify_writeback,
)
from validate_grill_report import extract_session


RUNTIME = Path(__file__).with_name("grill_session_runtime.py")


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(RUNTIME), *arguments], text=True, capture_output=True, check=False)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configured_ledger(root: Path) -> tuple[dict, Path]:
    formal = root / "formal"
    formal.mkdir()
    target = formal / "requirements-prd-v0.1.md"
    target.write_text("before", encoding="utf-8")
    session_path = root / "ledger.json"
    ledger = new_ledger("grill-v2-test", "requirements", session_path=session_path)
    ledger["workspaceRoot"] = str(root)
    ledger["protectedAssets"] = [{"path": "formal/requirements-prd-v0.1.md", "kind": "file"}]
    ledger["writebackPolicy"]["approvedScopes"] = [{"path": "formal", "kind": "directory"}]
    ledger["questions"] = [{"id": "Q-001", "question": "Approve the formal scope?", "purpose": "scope", "recommendedAnswer": "approve", "blockingDecision": "scope", "status": "confirmed", "severity": "P0", "userResponse": "approved", "reopenHistory": []}]
    return ledger, target


def closure() -> dict:
    return {"statement": "The full review is closed.", "source": "user", "recordedAt": datetime.now(timezone.utc).isoformat()}


def plan(target: Path) -> dict:
    return {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]}


def test_default_batch_and_actual_postconditions(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    ledger["phase"] = "grilling"; ledger["result"] = "in-progress"
    close_session(ledger, closure())
    create_checkpoint(ledger, tmp, "CP-001")
    target.write_text("after", encoding="utf-8")
    frozen = plan(target)
    target.write_text("before", encoding="utf-8")
    start_writeback(ledger, tmp, "B-001", "CP-001", frozen)
    target.write_text("after", encoding="utf-8")  # Simulates downstream formal merge against a real temporary file.
    receipt = {"batchId": "B-001", "decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]}
    verify_writeback(ledger, tmp, receipt)
    assert ledger["phase"] == "writeback-complete" and ledger["result"] == "completed"
    history_size = len(ledger["history"])
    verify_writeback(ledger, tmp, receipt)
    assert len(ledger["history"]) == history_size  # Verified receipt retry is a no-op.


def test_partial_receipt_records_recovery(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    target.write_text("after", encoding="utf-8"); frozen = plan(target); target.write_text("before", encoding="utf-8")
    start_writeback(ledger, tmp, "B-001", "CP-001", frozen)
    target.write_text("partial", encoding="utf-8")
    receipt = {"batchId": "B-001", "decisionFingerprint": _fingerprint([]), "items": frozen["items"]}
    verify_writeback(ledger, tmp, receipt)
    assert ledger["result"] == "partial-failure" and ledger["writebackReceipts"][0]["items"][0]["status"] == "hash-mismatch"
    target.write_text("after", encoding="utf-8")
    verify_writeback(ledger, tmp, receipt)
    assert ledger["result"] == "completed"  # Retry verifies real postconditions without repeating a merge.


def test_unresolved_p0_and_concrete_risk_acceptance(tmp: Path) -> None:
    ledger, _ = configured_ledger(tmp)
    ledger["questions"][0]["status"] = "needs-evidence"
    issues = validate_ledger(ledger)
    assert any(item["rule"] == "unresolved-p0-missing-open-item" for item in issues)
    ledger["openItems"] = [{"id": "O-001", "severity": "P0", "sourceQuestion": "Q-001"}]
    assert any(item["rule"] == "concrete-risk-acceptance-required" for item in validate_ledger(ledger, "close"))
    ledger["riskAcceptances"] = [{"openItemId": "O-001", "risk": "source evidence missing", "acceptanceBasis": "user accepts bounded risk", "scope": "this decision", "acceptedBy": "user"}]
    assert not any(item["rule"] == "concrete-risk-acceptance-required" for item in validate_ledger(ledger, "close"))


def test_pause_resume_reopen_preserves_history(tmp: Path) -> None:
    ledger, _ = configured_ledger(tmp)
    pause_session(ledger, "Q-001"); resume_session(ledger)
    assert ledger["phase"] == "grilling" and ledger["recovery"]["nextQuestionId"] == "Q-001"
    ledger["decisions"] = [{"id": "D-001", "sourceQuestion": "Q-001", "status": "effective"}]
    ledger["effectiveDecisions"] = ["D-001"]
    reopen_question(ledger, "Q-001", "external evidence changed", "E-002")
    assert ledger["questions"][0]["reopenHistory"][0]["evidenceRef"] == "E-002"
    assert ledger["decisions"][0]["status"] == "superseded"


def test_exception_is_bounded_and_single_use(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    create_checkpoint(ledger, tmp, "CP-001")
    create_exception(ledger, tmp, "EX-001", "user message", [{"path": "formal/requirements-prd-v0.1.md", "kind": "file"}], "CP-001")
    consume_exception(ledger, tmp, "EX-001", "formal/requirements-prd-v0.1.md")
    assert ledger["exceptions"][0]["status"] == "consumed"
    try:
        consume_exception(ledger, tmp, "EX-001", "formal/requirements-prd-v0.1.md")
    except LedgerError:
        pass
    else:
        raise AssertionError("a consumed exception must not be reusable")
    target.write_text("approved exception edit", encoding="utf-8")
    finish_exception(ledger, tmp, "EX-001", [{"id": "I-EX", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}], "CP-EX")
    assert ledger["exceptions"][0]["status"] == "verified" and not ledger["recovery"].get("exceptionPendingId")


def test_external_drift_and_new_version_block_batch(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    (target.parent / "requirements-prd-v2.1.md").write_text("external", encoding="utf-8")
    try:
        start_writeback(ledger, tmp, "B-001", "CP-001", {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]})
    except LedgerError as exc:
        assert "external drift" in str(exc)
    else:
        raise AssertionError("new protected version must require external-drift review")


def test_legacy_is_read_only_and_storage_cannot_overlap(tmp: Path) -> None:
    legacy = {"sessionId": "legacy", "status": "complete"}
    assert not any(item["severity"] == "P0" for item in validate_ledger(legacy, "read"))
    assert any(item["rule"] == "legacy-write-denied" for item in validate_ledger(legacy, "write"))
    ledger, _ = configured_ledger(tmp)
    ledger["protectedAssets"] = [{"path": "ledger.json", "kind": "file"}]
    try:
        ensure_mutable_ledger(ledger, tmp / "ledger.json")
    except LedgerError as exc:
        assert "process-artifact-protected-overlap" in str(exc)
    else:
        raise AssertionError("ledger path must not overlap formal protected assets")


def test_non_overwrite_initialization(tmp: Path) -> None:
    path = tmp / "existing.json"
    path.write_text("user data", encoding="utf-8")
    try:
        new_ledger("id", "requirements", session_path=path)
    except LedgerError:
        pass
    else:
        raise AssertionError("init must not overwrite an existing user file")


def test_report_is_exact_ledger_projection(tmp: Path) -> None:
    ledger, _ = configured_ledger(tmp)
    close_session(ledger, closure(), "conclusions-only")
    report = tmp / "report.html"
    ledger["processArtifacts"].append({"kind": "report", "path": str(report)})
    render_report(ledger, report)
    projected, _ = extract_session(report)
    assert projected == ledger


def test_forged_closure_and_checkpoint_evidence_are_refused(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    ledger["phase"] = "review-ended"; ledger["result"] = "ready-for-writeback"
    create_checkpoint(ledger, tmp, "CP-001")
    try:
        start_writeback(ledger, tmp, "B-001", "CP-001", {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]})
    except LedgerError as exc:
        assert "closure-evidence-required" in str(exc)
    else:
        raise AssertionError("forged review-ended state must not start writeback")
    ledger["phase"] = "grilling"; ledger["result"] = "in-progress"
    close_session(ledger, closure())
    ledger["checkpoints"][0]["snapshotHash"] = "0" * 64
    try:
        start_writeback(ledger, tmp, "B-002", "CP-001", {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]})
    except LedgerError as exc:
        assert "forged or stale" in str(exc)
    else:
        raise AssertionError("forged checkpoint hash must not start writeback")


def test_format_only_reconciliation_keeps_unrelated_decisions(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    ledger["questions"].append({"id": "Q-002", "question": "Keep unrelated decision?", "purpose": "scope", "recommendedAnswer": "yes", "blockingDecision": "unrelated", "status": "confirmed", "severity": "P1", "userResponse": "yes"})
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    target.write_text("format-only external change", encoding="utf-8")
    create_checkpoint(ledger, tmp, "CP-OBS")
    assert not ledger["checkpoints"][-1]["approvedForWriteback"]
    reconcile_format_only_drift(ledger, tmp, "CP-001", "CP-REC", "reviewed formatting evidence", ["Q-001"])
    assert ledger["questions"][1]["status"] == "confirmed"  # Unaffected decisions stay intact.


def test_conversation_only_init_writes_no_ledger(tmp: Path) -> None:
    session = tmp / "must-not-exist.json"
    assert main(["init", "--session", str(session), "--session-id", "chat-only", "--scenario", "requirements", "--record-mode", "conversation-only", "--workspace-root", str(tmp)]) == 0
    assert not session.exists()


def test_cli_open_p0_answer_and_exception_finish(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    ledger["questions"][0]["status"] = "proposed"; ledger["questions"][0].pop("userResponse")
    ledger["openItems"] = [{"id": "O-001", "severity": "P0", "sourceQuestion": "Q-001"}]
    session = tmp / "ledger.json"; session.write_text(json.dumps(ledger), encoding="utf-8")
    result = run_cli("record-answer", "--session", str(session), "--question", "Q-001", "--answer", "approved", "--status", "confirmed")
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_cli("checkpoint", "--session", str(session), "--workspace-root", str(tmp), "--checkpoint-id", "CP-001")
    assert result.returncode == 0, result.stdout + result.stderr
    scope = tmp / "scope.json"; scope.write_text(json.dumps({"scope": [{"path": "formal/requirements-prd-v0.1.md", "kind": "file"}]}), encoding="utf-8")
    result = run_cli("create-exception", "--session", str(session), "--workspace-root", str(tmp), "--exception-id", "EX-001", "--authorization", "user scope", "--scope", str(scope), "--checkpoint-id", "CP-001")
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_cli("consume-exception", "--session", str(session), "--workspace-root", str(tmp), "--exception-id", "EX-001", "--target", "formal/requirements-prd-v0.1.md")
    assert result.returncode == 0, result.stdout + result.stderr
    target.write_text("exception cli edit", encoding="utf-8")
    post = tmp / "post.json"; post.write_text(json.dumps({"items": [{"id": "I-EX", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]}), encoding="utf-8")
    result = run_cli("finish-exception", "--session", str(session), "--workspace-root", str(tmp), "--exception-id", "EX-001", "--postconditions", str(post), "--checkpoint-id", "CP-EX")
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_cli("record-answer", "--session", str(session), "--question", "Q-001", "--answer", "still confirmed", "--status", "confirmed")
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_propose_question_and_prepare_plan_round_trip(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    session = tmp / "ledger.json"; plan_path = tmp / "batch-plan.json"
    ledger["processArtifacts"].append({"kind": "writeback-plan", "path": str(plan_path)})
    session.write_text(json.dumps(ledger), encoding="utf-8")
    proposal = tmp / "question.json"; proposal.write_text(json.dumps({"id": "Q-002", "question": "Approve the final batch?", "purpose": "batch", "recommendedAnswer": "approve", "blockingDecision": "batch", "severity": "P0", "evidence": ["E-002"]}), encoding="utf-8")
    result = run_cli("propose-question", "--session", str(session), "--question-json", str(proposal))
    assert result.returncode == 0, result.stdout + result.stderr
    proposed = json.loads(session.read_text(encoding="utf-8"))
    assert proposed["questions"][-1]["status"] == "proposed" and proposed["openItems"][-1]["sourceQuestion"] == "Q-002"
    result = run_cli("record-answer", "--session", str(session), "--question", "Q-002", "--answer", "approved", "--status", "confirmed")
    assert result.returncode == 0, result.stdout + result.stderr
    closure_path = tmp / "closure.json"; closure_path.write_text(json.dumps(closure()), encoding="utf-8")
    result = run_cli("close", "--session", str(session), "--closure", str(closure_path))
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_cli("checkpoint", "--session", str(session), "--workspace-root", str(tmp), "--checkpoint-id", "CP-001")
    assert result.returncode == 0, result.stdout + result.stderr
    target.write_text("public planned update", encoding="utf-8")
    expected_after = digest(target)
    target.write_text("before", encoding="utf-8")
    items = tmp / "items.json"; items.write_text(json.dumps({"items": [{"id": "I-001", "path": str(target), "expectedSha256": expected_after}]}), encoding="utf-8")
    result = run_cli("prepare-writeback-plan", "--session", str(session), "--items", str(items), "--output", str(plan_path))
    assert result.returncode == 0, result.stdout + result.stderr
    prepared = json.loads(plan_path.read_text(encoding="utf-8"))
    assert prepared["items"][0]["path"] == "formal/requirements-prd-v0.1.md" and prepared["decisionFingerprint"]
    before_plan = plan_path.read_bytes()
    duplicate = tmp / "duplicate-items.json"; duplicate.write_text(json.dumps({"items": [{"id": "I-002", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": expected_after}, {"id": "I-003", "path": str(target), "expectedSha256": expected_after}]}), encoding="utf-8")
    result = run_cli("prepare-writeback-plan", "--session", str(session), "--items", str(duplicate), "--output", str(plan_path))
    assert result.returncode != 0 and plan_path.read_bytes() == before_plan
    result = run_cli("begin-writeback", "--session", str(session), "--workspace-root", str(tmp), "--batch-id", "B-001", "--checkpoint-id", "CP-001", "--plan", str(plan_path))
    assert result.returncode == 0, result.stdout + result.stderr
    target.write_text("public planned update", encoding="utf-8")
    receipt = tmp / "receipt.json"; receipt.write_text(json.dumps({"batchId": "B-001", "decisionFingerprint": prepared["decisionFingerprint"], "items": prepared["items"]}), encoding="utf-8")
    result = run_cli("verify-writeback", "--session", str(session), "--workspace-root", str(tmp), "--receipt", str(receipt))
    assert result.returncode == 0, result.stdout + result.stderr


def test_decision_text_change_invalidates_frozen_plan(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    ledger["decisions"] = [{"id": "D-001", "sourceQuestion": "Q-001", "status": "effective", "decision": "first wording"}]
    ledger["effectiveDecisions"] = ["D-001"]
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    frozen = {"decisionFingerprint": _decision_fingerprint(ledger), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(target)}]}
    ledger["decisions"][0]["decision"] = "changed wording under same ID"
    try:
        start_writeback(ledger, tmp, "B-001", "CP-001", frozen)
    except LedgerError as exc:
        assert "decision fingerprint is stale" in str(exc)
    else:
        raise AssertionError("same-ID decision content changes must invalidate a frozen plan")


def test_unchanged_postcondition_is_explicit_noop(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    frozen = plan(target)
    start_writeback(ledger, tmp, "B-001", "CP-001", frozen)
    receipt = {"batchId": "B-001", "decisionFingerprint": _fingerprint([]), "items": frozen["items"]}
    verify_writeback(ledger, tmp, receipt)
    receipt_entry = ledger["writebackReceipts"][0]
    assert receipt_entry["status"] == "verified-noop" and receipt_entry["outcome"] == "no-op" and not receipt_entry["contentChanged"] and not receipt_entry["mergePerformed"]


def test_absolute_plan_target_normalizes_and_alias_is_rejected(tmp: Path) -> None:
    ledger, target = configured_ledger(tmp)
    close_session(ledger, closure()); create_checkpoint(ledger, tmp, "CP-001")
    target.write_text("after", encoding="utf-8")
    absolute_plan = {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": str(target), "expectedSha256": digest(target)}]}
    target.write_text("before", encoding="utf-8")
    start_writeback(ledger, tmp, "B-001", "CP-001", absolute_plan)
    planned = ledger["writebackReceipts"][0]["plannedItems"]
    assert planned[0]["path"] == "formal/requirements-prd-v0.1.md"
    target.write_text("after", encoding="utf-8")
    verify_writeback(ledger, tmp, {"batchId": "B-001", "decisionFingerprint": _fingerprint([]), "items": planned})
    assert ledger["result"] == "completed"
    alias_root = tmp / "alias"; alias_root.mkdir()
    alias_ledger, alias_target = configured_ledger(alias_root)
    close_session(alias_ledger, closure()); create_checkpoint(alias_ledger, alias_root, "CP-001")
    duplicate_plan = {"decisionFingerprint": _fingerprint([]), "items": [{"id": "I-001", "path": "formal/requirements-prd-v0.1.md", "expectedSha256": digest(alias_target)}, {"id": "I-002", "path": str(alias_target), "expectedSha256": digest(alias_target)}]}
    try:
        start_writeback(alias_ledger, alias_root, "B-001", "CP-001", duplicate_plan)
    except LedgerError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("relative and absolute aliases must not produce two planned targets")


if __name__ == "__main__":
    # Each test uses a fresh root to prevent artifacts from one scenario becoming another's baseline.
    for test in (test_default_batch_and_actual_postconditions, test_partial_receipt_records_recovery, test_unresolved_p0_and_concrete_risk_acceptance, test_pause_resume_reopen_preserves_history, test_exception_is_bounded_and_single_use, test_external_drift_and_new_version_block_batch, test_legacy_is_read_only_and_storage_cannot_overlap, test_non_overwrite_initialization, test_report_is_exact_ledger_projection, test_forged_closure_and_checkpoint_evidence_are_refused, test_format_only_reconciliation_keeps_unrelated_decisions, test_conversation_only_init_writes_no_ledger, test_cli_open_p0_answer_and_exception_finish, test_cli_propose_question_and_prepare_plan_round_trip, test_decision_text_change_invalidates_frozen_plan, test_unchanged_postcondition_is_explicit_noop, test_absolute_plan_target_normalizes_and_alias_is_rejected):
        with tempfile.TemporaryDirectory() as directory:
            test(Path(directory))
    print("ok: Grill V2 phase contract tests passed")
