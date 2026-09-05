"""从进程结束后的文件证据构建并校验 PyCharm 外部验收链。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .path_utils import io_path
from .strict_json import load_strict_json


class PyCharmAcceptanceError(RuntimeError):
    """稳定、无私有值的外部验收错误。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _self_hash(document: Mapping[str, Any], field: str) -> str:
    return canonical_hash({key: value for key, value in document.items() if key != field})


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _path_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(str(path.resolve(strict=True)).lower().encode("utf-8")).hexdigest()


def _schema_issue(document: Mapping[str, Any], schema: str) -> bool:
    try:
        return bool(validate_document(dict(document), schema))
    except Exception:
        return True


def build_pycharm_process_evidence(
    *,
    helper_path: str | Path,
    session_id: str,
    observed_process_exit_code: int,
    pytest_exitstatus: int,
    stdout: str | bytes,
    stderr: str | bytes,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """由外部进程控制器生成脱敏证据；只持久化stdout/stderr哈希。"""
    helper = Path(helper_path).resolve(strict=True)
    if tuple(part.lower() for part in helper.parts[-3:]) != ("helpers", "pycharm", "_jb_pytest_runner.py"):
        raise PyCharmAcceptanceError("E_PROCESS_EVIDENCE_HELPER_PATH_INVALID")
    stdout_bytes = stdout.encode("utf-8") if isinstance(stdout, str) else bytes(stdout)
    stderr_bytes = stderr.encode("utf-8") if isinstance(stderr, str) else bytes(stderr)
    document: dict[str, Any] = {
        "schema_version": "ui-test.pycharm-process-evidence.v1",
        "session_id": session_id,
        "helper_path_hash": _path_hash(helper),
        "helper_content_hash": _file_hash(helper),
        "observed_process_exit_code": int(observed_process_exit_code),
        "pytest_exitstatus": int(pytest_exitstatus),
        "stdout_hash": "sha256:" + hashlib.sha256(stdout_bytes).hexdigest(),
        "stderr_hash": "sha256:" + hashlib.sha256(stderr_bytes).hexdigest(),
        "recorded_at": recorded_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    document["process_evidence_hash"] = canonical_hash(document)
    if _schema_issue(document, "pycharm-process-evidence-v1.schema.json"):
        raise PyCharmAcceptanceError("E_PROCESS_EVIDENCE_SCHEMA_INVALID")
    return document


def validate_pycharm_acceptance_chain(
    *,
    run_result: Mapping[str, Any],
    finalization_commit: Mapping[str, Any],
    finalization_receipt: Mapping[str, Any],
    pytest_session_result: Mapping[str, Any],
    acceptance_result: Mapping[str, Any],
    approval_record: Mapping[str, Any],
    execution_context: Mapping[str, Any],
    terminal: Mapping[str, Any],
    process_evidence: Mapping[str, Any],
) -> list[str]:
    """验证Schema、自哈希、内容哈希、身份、terminal、session与真实进程证据互链。"""
    issues: list[str] = []
    named_documents = {
        "run-result": run_result,
        "commit": finalization_commit,
        "receipt": finalization_receipt,
        "session": pytest_session_result,
        "acceptance": acceptance_result,
        "approval": approval_record,
        "context": execution_context,
        "terminal": terminal,
        "process-evidence": process_evidence,
    }
    non_objects = [name for name, document in named_documents.items() if not isinstance(document, Mapping)]
    if non_objects:
        return ["chain-document-not-object:" + name for name in sorted(non_objects)]
    schema_documents = (
        (run_result, "run-result-v5.schema.json", "run-result-schema"),
        (finalization_commit, "finalization-commit-v1.schema.json", "commit-schema"),
        (finalization_receipt, "run-finalization-receipt-v1.schema.json", "receipt-schema"),
        (pytest_session_result, "pytest-session-result-v1.schema.json", "session-schema"),
        (acceptance_result, "pycharm-acceptance-result-v1.schema.json", "acceptance-schema"),
        (approval_record, "r2-approval-record-v2.schema.json", "approval-schema"),
        (execution_context, "execution-context-v3.schema.json", "context-schema"),
        (process_evidence, "pycharm-process-evidence-v1.schema.json", "process-evidence-schema"),
    )
    for document, schema, code in schema_documents:
        if not isinstance(document, Mapping) or _schema_issue(document, schema):
            issues.append(code)

    self_hashes = (
        (run_result, "run_result_hash", "run-result-hash"),
        (finalization_commit, "commit_hash", "commit-hash"),
        (finalization_receipt, "receipt_hash", "receipt-hash"),
        (pytest_session_result, "session_result_hash", "session-hash"),
        (acceptance_result, "acceptance_hash", "acceptance-hash"),
        (process_evidence, "process_evidence_hash", "process-evidence-hash"),
    )
    for document, field, code in self_hashes:
        if document.get(field) != _self_hash(document, field):
            issues.append(code)

    identity_fields = ("session_id", "run_id", "node_id")
    identity = tuple(run_result.get(field) for field in identity_fields)
    for document, code in (
        (finalization_commit, "commit-identity"),
        (finalization_receipt, "receipt-identity"),
        (acceptance_result, "acceptance-identity"),
    ):
        if tuple(document.get(field) for field in identity_fields) != identity:
            issues.append(code)
    if execution_context.get("session_id") != identity[0] or execution_context.get("run_id") != identity[1] or execution_context.get("node_id") != identity[2]:
        issues.append("context-identity")
    if process_evidence.get("session_id") != identity[0] or pytest_session_result.get("session_id") != identity[0]:
        issues.append("process-session-identity")

    run_content_hash = canonical_hash(dict(run_result))
    commit_content_hash = canonical_hash(dict(finalization_commit))
    receipt_content_hash = canonical_hash(dict(finalization_receipt))
    session_content_hash = canonical_hash(dict(pytest_session_result))
    process_content_hash = canonical_hash(dict(process_evidence))
    expected_run_ref = "objects/" + run_content_hash.removeprefix("sha256:") + ".json"
    if finalization_commit.get("run_result_ref") != expected_run_ref:
        issues.append("commit-run-ref")
    if finalization_commit.get("run_result_hash") != run_result.get("run_result_hash"):
        issues.append("commit-run-hash")
    if finalization_receipt.get("commit_manifest_hash") != commit_content_hash:
        issues.append("receipt-commit-hash")
    for field in ("run_result_ref", "run_result_hash", "evidence_index_ref", "evidence_index_hash"):
        if finalization_receipt.get(field) != finalization_commit.get(field):
            issues.append("receipt-closure-" + field)

    context_hash = canonical_hash(dict(execution_context))
    approval_hash = canonical_hash(dict(approval_record))
    approval_boundary = {
        "run_id": approval_record.get("run_id"),
        "case_id": approval_record.get("case_id"),
        "environment": approval_record.get("environment"),
        "allowed_action": approval_record.get("allowed_action"),
        "channel": approval_record.get("channel"),
        "max_submit_count": approval_record.get("max_submit_count"),
    }
    if approval_record.get("boundary_hash") != canonical_hash(approval_boundary):
        issues.append("approval-boundary-hash")
    if run_result.get("execution_context_hash") != context_hash or acceptance_result.get("execution_context_hash") != context_hash:
        issues.append("context-hash-link")
    if acceptance_result.get("execution_context_ref") != run_result.get("execution_context_ref"):
        issues.append("context-ref-link")
    if run_result.get("approval_hash") != approval_hash or acceptance_result.get("authorization_hash") != approval_hash:
        issues.append("approval-hash-link")
    for field in ("run_id", "node_id", "case_id", "branch_id"):
        if approval_record.get(field) != run_result.get(field):
            issues.append("approval-identity-" + field)

    nodes = [
        node
        for node in pytest_session_result.get("nodes", [])
        if node.get("run_id") == identity[1] and node.get("node_id") == identity[2]
    ]
    if len(nodes) != 1:
        issues.append("session-node-not-unique")
    else:
        node = nodes[0]
        if node.get("terminal_hash") != canonical_hash(dict(terminal)):
            issues.append("session-terminal-hash")
        if node.get("receipt_hash") != receipt_content_hash or node.get("finalization_status") != "committed":
            issues.append("session-receipt-link")
        if acceptance_result.get("terminal_ref") != node.get("terminal_ref") or acceptance_result.get("terminal_hash") != node.get("terminal_hash"):
            issues.append("acceptance-terminal-link")
        if acceptance_result.get("finalization_receipt_ref") != node.get("receipt_ref"):
            issues.append("acceptance-receipt-ref")
    if terminal.get("status") != "passed" or terminal.get("commit_manifest_hash") != commit_content_hash or terminal.get("receipt_hash") != receipt_content_hash:
        issues.append("terminal-finalization-closure")
    if acceptance_result.get("finalization_commit_ref") != terminal.get("commit_manifest_ref"):
        issues.append("acceptance-commit-ref")
    if acceptance_result.get("finalization_receipt_ref") != terminal.get("receipt_ref"):
        issues.append("acceptance-terminal-receipt-ref")

    origin = execution_context.get("origin_evidence", {})
    if execution_context.get("execution_origin") != "pycharm" or pytest_session_result.get("execution_origin") != "pycharm":
        issues.append("pycharm-origin-required")
    if process_evidence.get("helper_path_hash") != origin.get("runner_path_hash"):
        issues.append("helper-path-hash-link")
    if process_evidence.get("helper_content_hash") != origin.get("runner_content_hash"):
        issues.append("helper-content-hash-link")
    if acceptance_result.get("helper_identity_digest") != process_evidence.get("helper_content_hash"):
        issues.append("acceptance-helper-hash")
    if acceptance_result.get("console_evidence_hash") != process_content_hash:
        issues.append("acceptance-process-evidence-hash")
    if process_evidence.get("pytest_exitstatus") != pytest_session_result.get("pytest_exitstatus"):
        issues.append("process-pytest-exit-mismatch")
    if acceptance_result.get("pytest_session_exitstatus") != pytest_session_result.get("pytest_exitstatus"):
        issues.append("acceptance-pytest-exit-mismatch")
    if acceptance_result.get("observed_process_exit_code") != process_evidence.get("observed_process_exit_code"):
        issues.append("acceptance-process-exit-mismatch")
    if acceptance_result.get("finalization_commit_hash") != commit_content_hash:
        issues.append("acceptance-commit-hash")
    if acceptance_result.get("finalization_receipt_hash") != receipt_content_hash:
        issues.append("acceptance-receipt-hash")
    if acceptance_result.get("pytest_session_result_hash") != session_content_hash:
        issues.append("acceptance-session-hash")

    if acceptance_result.get("overall_status") == "passed":
        passed_requirements = (
            run_result.get("overall_status") == "passed",
            finalization_commit.get("status") == "committed",
            finalization_receipt.get("status") == "committed",
            finalization_receipt.get("recovery_mode") == "none",
            terminal.get("status") == "passed",
            pytest_session_result.get("pytest_exitstatus") == 0,
            pytest_session_result.get("session_status") == "passed",
            pytest_session_result.get("all_required_nodes_committed") is True,
            process_evidence.get("observed_process_exit_code") == 0,
            acceptance_result.get("post_run_recovery") is False,
            acceptance_result.get("pycharm_integration") == "passed",
            acceptance_result.get("human_r2") == "passed",
            approval_record.get("approval_source") == "pycharm-project-policy",
            approval_record.get("decision") == "approved",
        )
        if not all(passed_requirements):
            issues.append("acceptance-passed-without-complete-chain")
    return sorted(set(issues))


def _build_pycharm_acceptance_result(
    *,
    run_result: Mapping[str, Any],
    finalization_commit: Mapping[str, Any],
    finalization_receipt: Mapping[str, Any],
    pytest_session_result: Mapping[str, Any],
    approval_record: Mapping[str, Any],
    execution_context: Mapping[str, Any],
    terminal: Mapping[str, Any],
    process_evidence: Mapping[str, Any],
    authorization_ref: str,
    process_evidence_ref: str,
    finalization_commit_ref: str,
    finalization_receipt_ref: str,
    pytest_session_result_ref: str,
    evaluation_authority: str,
    post_run_recovery: bool = False,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """使用已读回的完整证据对象生成AcceptanceResult；不接受裸exit或helper摘要。"""
    identity = tuple(run_result.get(field) for field in ("session_id", "run_id", "node_id"))
    nodes = [
        node for node in pytest_session_result.get("nodes", [])
        if node.get("run_id") == identity[1] and node.get("node_id") == identity[2]
    ]
    if len(nodes) != 1:
        raise PyCharmAcceptanceError("E_ACCEPTANCE_SESSION_NODE_NOT_UNIQUE")
    node = nodes[0]
    passed = all(
        (
            run_result.get("overall_status") == "passed",
            finalization_commit.get("status") == "committed",
            finalization_receipt.get("status") == "committed",
            finalization_receipt.get("recovery_mode") == "none",
            terminal.get("status") == "passed",
            pytest_session_result.get("pytest_exitstatus") == 0,
            pytest_session_result.get("session_status") == "passed",
            pytest_session_result.get("all_required_nodes_committed") is True,
            process_evidence.get("observed_process_exit_code") == 0,
            post_run_recovery is False,
            approval_record.get("approval_source") == "pycharm-project-policy",
        )
    )
    status = "passed" if passed else "failed"
    result: dict[str, Any] = {
        "schema_version": "ui-test.pycharm-acceptance-result.v1",
        "acceptance_id": "ACCEPT-" + canonical_hash(
            {"session_id": identity[0], "run_id": identity[1], "node_id": identity[2]}
        ).removeprefix("sha256:")[:24],
        "session_id": identity[0],
        "run_id": identity[1],
        "node_id": identity[2],
        "case_id": run_result["case_id"],
        "branch_id": run_result["branch_id"],
        "helper_identity_digest": process_evidence["helper_content_hash"],
        "authorization_ref": authorization_ref,
        "authorization_hash": canonical_hash(dict(approval_record)),
        "approval_source": approval_record.get("approval_source"),
        "execution_context_ref": run_result["execution_context_ref"],
        "execution_context_hash": canonical_hash(dict(execution_context)),
        "terminal_ref": node["terminal_ref"],
        "terminal_hash": canonical_hash(dict(terminal)),
        "run_result_ref": finalization_commit["run_result_ref"],
        "run_result_hash": run_result["run_result_hash"],
        "finalization_commit_ref": finalization_commit_ref,
        "finalization_commit_hash": canonical_hash(dict(finalization_commit)),
        "finalization_receipt_ref": finalization_receipt_ref,
        "finalization_receipt_hash": canonical_hash(dict(finalization_receipt)),
        "pytest_session_result_ref": pytest_session_result_ref,
        "pytest_session_result_hash": canonical_hash(dict(pytest_session_result)),
        "console_evidence_ref": process_evidence_ref,
        "console_evidence_hash": canonical_hash(dict(process_evidence)),
        "pytest_session_exitstatus": pytest_session_result["pytest_exitstatus"],
        "observed_process_exit_code": process_evidence["observed_process_exit_code"],
        "post_run_recovery": post_run_recovery,
        "pycharm_integration": status,
        "human_r2": status,
        "overall_status": status,
        "evaluation_authority": evaluation_authority,
        "evaluated_at": evaluated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    result["acceptance_hash"] = canonical_hash(result)
    issues = validate_pycharm_acceptance_chain(
        run_result=run_result,
        finalization_commit=finalization_commit,
        finalization_receipt=finalization_receipt,
        pytest_session_result=pytest_session_result,
        acceptance_result=result,
        approval_record=approval_record,
        execution_context=execution_context,
        terminal=terminal,
        process_evidence=process_evidence,
    )
    if issues:
        raise PyCharmAcceptanceError("E_ACCEPTANCE_CHAIN_INVALID:" + ",".join(issues))
    return result


def build_pycharm_acceptance_from_files(
    *,
    helper_path: str | Path,
    run_result_path: str | Path,
    finalization_commit_path: str | Path,
    finalization_receipt_path: str | Path,
    pytest_session_result_path: str | Path,
    approval_record_path: str | Path,
    execution_context_path: str | Path,
    terminal_path: str | Path,
    process_evidence_path: str | Path,
    authorization_ref: str,
    process_evidence_ref: str,
    finalization_commit_ref: str,
    finalization_receipt_ref: str,
    pytest_session_result_ref: str,
    evaluation_authority: str,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """从精确文件读回构建验收；真实exit只来自Schema有效的外部进程证据。"""
    helper = Path(helper_path).resolve(strict=True)
    if tuple(part.lower() for part in helper.parts[-3:]) != ("helpers", "pycharm", "_jb_pytest_runner.py"):
        raise PyCharmAcceptanceError("E_ACCEPTANCE_HELPER_PATH_INVALID")
    process_evidence = load_strict_json(io_path(process_evidence_path))
    if process_evidence.get("helper_path_hash") != _path_hash(helper):
        raise PyCharmAcceptanceError("E_ACCEPTANCE_HELPER_PATH_HASH_MISMATCH")
    if process_evidence.get("helper_content_hash") != _file_hash(helper):
        raise PyCharmAcceptanceError("E_ACCEPTANCE_HELPER_CONTENT_HASH_MISMATCH")
    terminal_target = io_path(terminal_path)
    post_run_recovery = (terminal_target.parent / "recovery.jsonl").exists()
    return _build_pycharm_acceptance_result(
        run_result=load_strict_json(io_path(run_result_path)),
        finalization_commit=load_strict_json(io_path(finalization_commit_path)),
        finalization_receipt=load_strict_json(io_path(finalization_receipt_path)),
        pytest_session_result=load_strict_json(io_path(pytest_session_result_path)),
        approval_record=load_strict_json(io_path(approval_record_path)),
        execution_context=load_strict_json(io_path(execution_context_path)),
        terminal=load_strict_json(terminal_target),
        process_evidence=process_evidence,
        authorization_ref=authorization_ref,
        process_evidence_ref=process_evidence_ref,
        finalization_commit_ref=finalization_commit_ref,
        finalization_receipt_ref=finalization_receipt_ref,
        pytest_session_result_ref=pytest_session_result_ref,
        evaluation_authority=evaluation_authority,
        post_run_recovery=post_run_recovery,
        evaluated_at=evaluated_at,
    )
