"""RunResultV5 与 evidence index 的 finalization 事务协调器。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .case_contracts import canonical_hash, validate_document
from .finalization_store import FinalizationStore


CandidateValidator = Callable[[dict[str, Any], dict[str, Any], Path], Sequence[Any] | None]
FaultInjector = Callable[[str], None]
_LEGACY_RUN_RESULTS = {"ui-test.run-result.v3", "ui-test.run-result.v4"}
_TRANSACTIONAL_RUN_RESULT = "ui-test.run-result.v5"


class FinalizationTransactionError(RuntimeError):
    """事务错误仅携带稳定错误码。"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _with_hash(document: dict[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(document)
    result.pop(field, None)
    result[field] = canonical_hash(result)
    return result


class FinalizationTransaction:
    """先安装不可变 object，再以一个 commit manifest 发布提交点。"""

    def __init__(
        self,
        run_root: str | Path,
        *,
        candidate_validator: CandidateValidator | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.store = FinalizationStore(run_root)
        self.run_root = self.store.run_root
        self._candidate_validator = candidate_validator
        self._clock = clock or _utc_now

    @staticmethod
    def _fault(injector: FaultInjector | None, stage: str) -> None:
        if injector is not None:
            injector(stage)

    @staticmethod
    def _identity_value(document: Mapping[str, Any], field: str) -> str:
        value = document.get(field)
        if not isinstance(value, str) or not value:
            raise FinalizationTransactionError(f"E_FINALIZATION_IDENTITY_MISSING:{field}")
        return value

    @staticmethod
    def _schema_valid(document: dict[str, Any], schema_name: str, error_code: str) -> None:
        try:
            issues = validate_document(document, schema_name)
        except Exception as exc:
            raise FinalizationTransactionError("E_FINALIZATION_SCHEMA_VALIDATOR_FAILED") from exc
        if issues:
            raise FinalizationTransactionError(error_code)

    @staticmethod
    def _candidate_hash(
        *,
        transaction_id: str,
        session_id: str,
        run_id: str,
        node_id: str,
        pre_terminal_events_hash: str,
        run_result_ref: str,
        run_result_hash: str,
        evidence_index_ref: str,
        evidence_index_hash: str,
    ) -> str:
        return canonical_hash(
            {
                "transaction_id": transaction_id,
                "session_id": session_id,
                "run_id": run_id,
                "node_id": node_id,
                "pre_terminal_events_hash": pre_terminal_events_hash,
                "run_result_ref": run_result_ref,
                "run_result_hash": run_result_hash,
                "evidence_index_ref": evidence_index_ref,
                "evidence_index_hash": evidence_index_hash,
            }
        )

    def _validate_candidate(self, run_result: dict[str, Any], evidence_index: dict[str, Any]) -> None:
        schema_version = run_result.get("schema_version")
        if schema_version in _LEGACY_RUN_RESULTS:
            # V3/V4 继续走旧 reader；禁止借新事务重新赋予历史结果执行资格。
            raise FinalizationTransactionError("E_FINALIZATION_LEGACY_RUN_RESULT_READ_ONLY")
        if schema_version != _TRANSACTIONAL_RUN_RESULT:
            raise FinalizationTransactionError("E_FINALIZATION_RUN_RESULT_VERSION_UNSUPPORTED")

        self._schema_valid(run_result, "run-result-v5.schema.json", "E_FINALIZATION_RUN_RESULT_SCHEMA_INVALID")
        self._schema_valid(evidence_index, "evidence-index-v2.schema.json", "E_FINALIZATION_EVIDENCE_INDEX_SCHEMA_INVALID")
        expected_run_hash = canonical_hash({key: value for key, value in run_result.items() if key != "run_result_hash"})
        if run_result.get("run_result_hash") != expected_run_hash:
            raise FinalizationTransactionError("E_FINALIZATION_RUN_RESULT_HASH_MISMATCH")
        for field in ("run_id", "case_id", "branch_id", "run_result_hash", "resolved_test_data_ref", "resolved_test_data_hash"):
            if evidence_index.get(field) != run_result.get(field):
                raise FinalizationTransactionError(f"E_FINALIZATION_EVIDENCE_LINK_MISMATCH:{field}")

        if self._candidate_validator is not None:
            try:
                issues = self._candidate_validator(run_result, evidence_index, self.run_root) or []
            except Exception as exc:
                raise FinalizationTransactionError("E_FINALIZATION_CANDIDATE_VALIDATOR_FAILED") from exc
            if issues:
                raise FinalizationTransactionError("E_FINALIZATION_CANDIDATE_INVALID")

    def _prepare(
        self,
        *,
        transaction_id: str,
        run_id: str,
        node_id: str,
        run_result: Mapping[str, Any],
        evidence_index: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        if not isinstance(run_result, Mapping) or not isinstance(evidence_index, Mapping):
            raise FinalizationTransactionError("E_FINALIZATION_CANDIDATE_NOT_OBJECT")
        prepared_run = copy.deepcopy(dict(run_result))
        prepared_evidence = copy.deepcopy(dict(evidence_index))
        if self._identity_value(prepared_run, "transaction_id") != transaction_id:
            raise FinalizationTransactionError("E_FINALIZATION_IDENTITY_MISMATCH:transaction_id")
        if self._identity_value(prepared_run, "run_id") != run_id:
            raise FinalizationTransactionError("E_FINALIZATION_IDENTITY_MISMATCH:run_id")
        if self._identity_value(prepared_run, "node_id") != node_id:
            raise FinalizationTransactionError("E_FINALIZATION_IDENTITY_MISMATCH:node_id")

        run_descriptor = self.store.describe_document(prepared_run)
        # evidence index 只引用最终不可变 object，不引用 staging 或旧固定文件名。
        prepared_evidence["run_result_ref"] = run_descriptor["ref"]
        prepared_evidence["run_result_hash"] = prepared_run.get("run_result_hash")
        self._validate_candidate(prepared_run, prepared_evidence)
        evidence_descriptor = self.store.describe_document(prepared_evidence)
        return prepared_run, prepared_evidence, run_descriptor, evidence_descriptor

    def _build_manifest(
        self,
        *,
        transaction_id: str,
        run_id: str,
        node_id: str,
        run_result: Mapping[str, Any],
        run_descriptor: Mapping[str, Any],
        evidence_descriptor: Mapping[str, Any],
        committed_at: str,
    ) -> dict[str, Any]:
        session_id = self._identity_value(run_result, "session_id")
        pre_terminal_hash = self._identity_value(run_result, "pre_terminal_events_hash")
        manifest = {
            "schema_version": "ui-test.finalization-commit.v1",
            "transaction_id": transaction_id,
            "session_id": session_id,
            "run_id": run_id,
            "node_id": node_id,
            "status": "committed",
            "candidate_hash": self._candidate_hash(
                transaction_id=transaction_id,
                session_id=session_id,
                run_id=run_id,
                node_id=node_id,
                pre_terminal_events_hash=pre_terminal_hash,
                run_result_ref=str(run_descriptor["ref"]),
                run_result_hash=str(run_result["run_result_hash"]),
                evidence_index_ref=str(evidence_descriptor["ref"]),
                evidence_index_hash=str(evidence_descriptor["content_hash"]),
            ),
            "pre_terminal_events_hash": pre_terminal_hash,
            "run_result_ref": run_descriptor["ref"],
            "run_result_hash": run_result["run_result_hash"],
            "evidence_index_ref": evidence_descriptor["ref"],
            "evidence_index_hash": evidence_descriptor["content_hash"],
            "atomic_publish": True,
            "committed_at": committed_at,
        }
        manifest = _with_hash(manifest, "commit_hash")
        self._schema_valid(manifest, "finalization-commit-v1.schema.json", "E_FINALIZATION_COMMIT_SCHEMA_INVALID")
        return manifest

    def _validate_manifest(self, manifest: Mapping[str, Any]) -> None:
        if not isinstance(manifest, dict):
            raise FinalizationTransactionError("E_FINALIZATION_COMMIT_INVALID")
        self._schema_valid(manifest, "finalization-commit-v1.schema.json", "E_FINALIZATION_COMMIT_INVALID")
        expected_hash = canonical_hash({key: value for key, value in manifest.items() if key != "commit_hash"})
        expected_candidate = self._candidate_hash(
            transaction_id=str(manifest.get("transaction_id", "")),
            session_id=str(manifest.get("session_id", "")),
            run_id=str(manifest.get("run_id", "")),
            node_id=str(manifest.get("node_id", "")),
            pre_terminal_events_hash=str(manifest.get("pre_terminal_events_hash", "")),
            run_result_ref=str(manifest.get("run_result_ref", "")),
            run_result_hash=str(manifest.get("run_result_hash", "")),
            evidence_index_ref=str(manifest.get("evidence_index_ref", "")),
            evidence_index_hash=str(manifest.get("evidence_index_hash", "")),
        )
        if manifest.get("commit_hash") != expected_hash or manifest.get("candidate_hash") != expected_candidate:
            raise FinalizationTransactionError("E_FINALIZATION_COMMIT_INVALID")

    def _manifest_matches(
        self,
        manifest: Mapping[str, Any],
        *,
        transaction_id: str,
        run_id: str,
        node_id: str,
        run_result: Mapping[str, Any],
        run_descriptor: Mapping[str, Any],
        evidence_descriptor: Mapping[str, Any],
    ) -> bool:
        try:
            self._validate_manifest(manifest)
        except FinalizationTransactionError:
            return False
        return (
            manifest.get("transaction_id") == transaction_id
            and manifest.get("session_id") == run_result.get("session_id")
            and manifest.get("run_id") == run_id
            and manifest.get("node_id") == node_id
            and manifest.get("pre_terminal_events_hash") == run_result.get("pre_terminal_events_hash")
            and manifest.get("run_result_ref") == run_descriptor.get("ref")
            and manifest.get("run_result_hash") == run_result.get("run_result_hash")
            and manifest.get("evidence_index_ref") == evidence_descriptor.get("ref")
            and manifest.get("evidence_index_hash") == evidence_descriptor.get("content_hash")
        )

    def _build_committed_receipt(self, manifest: Mapping[str, Any], *, recorded_at: str) -> dict[str, Any]:
        receipt = {
            "schema_version": "ui-test.run-finalization-receipt.v1",
            "transaction_id": manifest["transaction_id"],
            "session_id": manifest["session_id"],
            "run_id": manifest["run_id"],
            "node_id": manifest["node_id"],
            "status": "committed",
            "recovery_mode": "none",
            "commit_manifest_ref": "finalization/finalization-commit.json",
            "commit_manifest_hash": canonical_hash(dict(manifest)),
            "run_result_ref": manifest["run_result_ref"],
            "run_result_hash": manifest["run_result_hash"],
            "evidence_index_ref": manifest["evidence_index_ref"],
            "evidence_index_hash": manifest["evidence_index_hash"],
            "recorded_at": recorded_at,
        }
        receipt = _with_hash(receipt, "receipt_hash")
        self._schema_valid(receipt, "run-finalization-receipt-v1.schema.json", "E_FINALIZATION_RECEIPT_SCHEMA_INVALID")
        return receipt

    def _build_post_run_failure_receipt(self, manifest: Mapping[str, Any], *, recorded_at: str) -> dict[str, Any]:
        receipt = {
            "schema_version": "ui-test.run-finalization-receipt.v1",
            "transaction_id": manifest["transaction_id"],
            "session_id": manifest["session_id"],
            "run_id": manifest["run_id"],
            "node_id": manifest["node_id"],
            "status": "failed",
            "recovery_mode": "post-run",
            "commit_manifest_ref": "finalization/finalization-commit.json",
            "commit_manifest_hash": canonical_hash(dict(manifest)),
            "run_result_ref": manifest["run_result_ref"],
            "run_result_hash": manifest["run_result_hash"],
            "evidence_index_ref": manifest["evidence_index_ref"],
            "evidence_index_hash": manifest["evidence_index_hash"],
            "error_code": "E_FINALIZATION_POST_RUN_RECOVERY_REQUIRED",
            "exception_class": "FinalizationInterrupted",
            "message_digest": canonical_hash(
                {"reason": "commit-without-receipt", "transaction_id": manifest["transaction_id"]}
            ),
            "recorded_at": recorded_at,
        }
        receipt = _with_hash(receipt, "receipt_hash")
        self._schema_valid(receipt, "run-finalization-receipt-v1.schema.json", "E_FINALIZATION_RECEIPT_SCHEMA_INVALID")
        return receipt

    def _validate_standalone_failure_receipt(self, receipt: Mapping[str, Any]) -> None:
        if not isinstance(receipt, dict) or receipt.get("status") != "failed":
            raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")
        self._schema_valid(receipt, "run-finalization-receipt-v1.schema.json", "E_FINALIZATION_RECEIPT_INVALID")
        expected_hash = canonical_hash({key: value for key, value in receipt.items() if key != "receipt_hash"})
        if receipt.get("receipt_hash") != expected_hash:
            raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")

    def _validate_receipt(self, receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
        if not isinstance(receipt, dict):
            raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")
        self._schema_valid(receipt, "run-finalization-receipt-v1.schema.json", "E_FINALIZATION_RECEIPT_INVALID")
        expected_hash = canonical_hash({key: value for key, value in receipt.items() if key != "receipt_hash"})
        for field in ("transaction_id", "session_id", "run_id", "node_id"):
            if receipt.get(field) != manifest.get(field):
                raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")
        if receipt.get("receipt_hash") != expected_hash:
            raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")
        if receipt.get("status") == "committed":
            expected = {
                "recovery_mode": "none",
                "commit_manifest_ref": "finalization/finalization-commit.json",
                "commit_manifest_hash": canonical_hash(dict(manifest)),
                "run_result_ref": manifest["run_result_ref"],
                "run_result_hash": manifest["run_result_hash"],
                "evidence_index_ref": manifest["evidence_index_ref"],
                "evidence_index_hash": manifest["evidence_index_hash"],
            }
            if any(receipt.get(key) != value for key, value in expected.items()):
                raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")
        elif receipt.get("status") != "failed":
            raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_INVALID")

    def record_failure(
        self,
        *,
        transaction_id: str,
        session_id: str,
        run_id: str,
        node_id: str,
        error_code: str,
        exception_class: str,
        message_digest: str,
        recovery_mode: str = "none",
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        """在未提交事务上原子记录脱敏失败 receipt。"""
        self.store.validate_transaction_id(transaction_id)
        timestamp = recorded_at or self._clock()
        receipt = {
            "schema_version": "ui-test.run-finalization-receipt.v1",
            "transaction_id": transaction_id,
            "session_id": session_id,
            "run_id": run_id,
            "node_id": node_id,
            "status": "failed",
            "recovery_mode": recovery_mode,
            "error_code": error_code,
            "exception_class": exception_class,
            "message_digest": message_digest,
            "recorded_at": timestamp,
        }
        receipt = _with_hash(receipt, "receipt_hash")
        self._validate_standalone_failure_receipt(receipt)

        with self.store.locked():
            if self.store.read_commit() is not None:
                raise FinalizationTransactionError("E_FINALIZATION_FAILURE_AFTER_COMMIT")
            existing = self.store.read_receipt()
            if existing is not None:
                self._validate_standalone_failure_receipt(existing)
                identity_fields = (
                    "transaction_id",
                    "session_id",
                    "run_id",
                    "node_id",
                    "status",
                    "recovery_mode",
                    "error_code",
                    "exception_class",
                    "message_digest",
                )
                if any(existing.get(field) != receipt.get(field) for field in identity_fields):
                    raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_CONFLICT")
                return {"status": "duplicate", "receipt": existing}
            self.store.publish_receipt(receipt)
            return {"status": "failed", "receipt": receipt}

    def commit(
        self,
        *,
        transaction_id: str,
        run_id: str,
        node_id: str,
        run_result: Mapping[str, Any],
        evidence_index: Mapping[str, Any],
        recorded_at: str | None = None,
        fault_injector: FaultInjector | None = None,
    ) -> dict[str, Any]:
        """提交一个 finalization；重复相同输入返回同一不可变闭包。"""
        self.store.validate_transaction_id(transaction_id)
        if not isinstance(node_id, str) or not node_id:
            raise FinalizationTransactionError("E_FINALIZATION_IDENTITY_MISSING:node_id")
        prepared_run, prepared_evidence, run_descriptor, evidence_descriptor = self._prepare(
            transaction_id=transaction_id,
            run_id=run_id,
            node_id=node_id,
            run_result=run_result,
            evidence_index=evidence_index,
        )
        timestamp = recorded_at or self._clock()
        if not isinstance(timestamp, str) or not timestamp:
            raise FinalizationTransactionError("E_FINALIZATION_RECORDED_AT_INVALID")

        with self.store.locked():
            existing_manifest = self.store.read_commit()
            existing_receipt = self.store.read_receipt()
            if existing_manifest is None and existing_receipt is not None:
                raise FinalizationTransactionError("E_FINALIZATION_RECEIPT_WITHOUT_COMMIT")
            if existing_manifest is not None:
                if not self._manifest_matches(
                    existing_manifest,
                    transaction_id=transaction_id,
                    run_id=run_id,
                    node_id=node_id,
                    run_result=prepared_run,
                    run_descriptor=run_descriptor,
                    evidence_descriptor=evidence_descriptor,
                ):
                    raise FinalizationTransactionError("E_FINALIZATION_COMMIT_CONFLICT")
                if existing_receipt is not None:
                    self._validate_receipt(existing_receipt, existing_manifest)
                    state = "duplicate" if existing_receipt["status"] == "committed" else "recovery-blocked"
                    return {"status": state, "manifest": existing_manifest, "receipt": existing_receipt}
                # commit 后缺 receipt 已越过原进程边界，只能封存失败，不能补成通过。
                failed_receipt = self._build_post_run_failure_receipt(existing_manifest, recorded_at=timestamp)
                self._fault(fault_injector, "before_receipt")
                self.store.publish_receipt(failed_receipt)
                self._fault(fault_injector, "after_receipt")
                return {"status": "recovery-blocked", "manifest": existing_manifest, "receipt": failed_receipt}

            staged_run = self.store.stage_document(transaction_id, "run_result", prepared_run)
            self._fault(fault_injector, "after_stage_run_result")
            staged_evidence = self.store.stage_document(transaction_id, "evidence_index", prepared_evidence)
            self._fault(fault_injector, "after_stage_evidence_index")
            installed_run = self.store.install_staged(staged_run)
            self._fault(fault_injector, "after_install_run_result")
            installed_evidence = self.store.install_staged(staged_evidence)
            self._fault(fault_injector, "after_install_evidence_index")

            manifest = self._build_manifest(
                transaction_id=transaction_id,
                run_id=run_id,
                node_id=node_id,
                run_result=prepared_run,
                run_descriptor=installed_run,
                evidence_descriptor=installed_evidence,
                committed_at=timestamp,
            )
            self._fault(fault_injector, "before_commit")
            self.store.publish_commit(manifest)
            self._fault(fault_injector, "after_commit")

            receipt = self._build_committed_receipt(manifest, recorded_at=timestamp)
            self._fault(fault_injector, "before_receipt")
            self.store.publish_receipt(receipt)
            self._fault(fault_injector, "after_receipt")
            return {"status": "committed", "manifest": manifest, "receipt": receipt}

    def read_committed(self) -> dict[str, Any] | None:
        """只在 commit、成功 receipt 与两个 object 全部闭合时返回结果。"""
        with self.store.locked():
            manifest = self.store.read_commit()
            receipt = self.store.read_receipt()
            if manifest is None:
                if receipt is not None:
                    self._validate_standalone_failure_receipt(receipt)
                return None
            self._validate_manifest(manifest)
            if receipt is None:
                return None
            self._validate_receipt(receipt, manifest)
            if receipt["status"] != "committed":
                return None

            run_result = self.store.load_blob_ref(str(manifest["run_result_ref"]))
            evidence_index = self.store.load_blob_ref(str(manifest["evidence_index_ref"]))
            if run_result.get("run_result_hash") != manifest.get("run_result_hash"):
                raise FinalizationTransactionError("E_FINALIZATION_RUN_RESULT_HASH_MISMATCH")
            if canonical_hash(evidence_index) != manifest.get("evidence_index_hash"):
                raise FinalizationTransactionError("E_FINALIZATION_EVIDENCE_INDEX_HASH_MISMATCH")
            self._validate_candidate(run_result, evidence_index)
            expected_candidate = self._candidate_hash(
                transaction_id=manifest["transaction_id"],
                session_id=manifest["session_id"],
                run_id=manifest["run_id"],
                node_id=manifest["node_id"],
                pre_terminal_events_hash=manifest["pre_terminal_events_hash"],
                run_result_ref=manifest["run_result_ref"],
                run_result_hash=manifest["run_result_hash"],
                evidence_index_ref=manifest["evidence_index_ref"],
                evidence_index_hash=manifest["evidence_index_hash"],
            )
            if manifest["candidate_hash"] != expected_candidate:
                raise FinalizationTransactionError("E_FINALIZATION_CANDIDATE_HASH_MISMATCH")
            return {
                "status": "committed",
                "manifest": manifest,
                "receipt": receipt,
                "run_result": run_result,
                "evidence_index": evidence_index,
            }


def commit_finalization(
    *,
    run_root: str | Path,
    transaction_id: str,
    run_id: str,
    node_id: str,
    run_result: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    candidate_validator: CandidateValidator | None = None,
    recorded_at: str | None = None,
    fault_injector: FaultInjector | None = None,
) -> dict[str, Any]:
    """无状态调用方使用的便捷入口。"""
    return FinalizationTransaction(run_root, candidate_validator=candidate_validator).commit(
        transaction_id=transaction_id,
        run_id=run_id,
        node_id=node_id,
        run_result=run_result,
        evidence_index=evidence_index,
        recorded_at=recorded_at,
        fault_injector=fault_injector,
    )


def record_finalization_failure(
    *,
    run_root: str | Path,
    transaction_id: str,
    session_id: str,
    run_id: str,
    node_id: str,
    error_code: str,
    exception_class: str,
    message_digest: str,
    recovery_mode: str = "none",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """项目 finalizer 使用的无状态失败 receipt 入口。"""
    return FinalizationTransaction(run_root).record_failure(
        transaction_id=transaction_id,
        session_id=session_id,
        run_id=run_id,
        node_id=node_id,
        error_code=error_code,
        exception_class=exception_class,
        message_digest=message_digest,
        recovery_mode=recovery_mode,
        recorded_at=recorded_at,
    )
