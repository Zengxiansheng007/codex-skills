"""Finalization 事务使用的内容寻址 JSON 存储。

本模块只负责不可变文件、相对引用和原子发布，不解释 RunResult 的业务语义。
"""

from __future__ import annotations

import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

from .case_contracts import canonical_bytes, canonical_hash
from .file_lock import exclusive_file_lock
from .path_utils import io_path
from .strict_json import loads_strict


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
_CONTENT_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


class FinalizationStoreError(RuntimeError):
    """仅暴露稳定错误码，不回显候选内容或绝对路径。"""


class FinalizationStore:
    """在一个 run 根目录中管理 finalization 的不可变文件。"""

    def __init__(self, run_root: str | Path) -> None:
        self.run_root = io_path(run_root)
        self.root = self.run_root / "finalization"
        self.staging_root = self.root / "staging"
        self.blob_root = self.root / "objects"
        self.commit_path = self.root / "finalization-commit.json"
        self.receipt_path = self.root / "finalization-receipt.json"
        self.lock_path = self.root / ".locks" / "transaction.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        """串行化同一 run 的 commit 与 receipt 发布。"""
        with exclusive_file_lock(self.lock_path):
            yield

    @staticmethod
    def _safe_identifier(value: str, *, error_code: str) -> str:
        if not isinstance(value, str) or not _SAFE_IDENTIFIER.fullmatch(value):
            raise FinalizationStoreError(error_code)
        return value

    def validate_transaction_id(self, value: str) -> str:
        """在任何读写前校验会进入 staging 路径的事务标识。"""
        return self._safe_identifier(value, error_code="E_FINALIZATION_TRANSACTION_ID_INVALID")

    def _resolve_ref(self, ref: str) -> Path:
        if not isinstance(ref, str) or not ref or "\\" in ref:
            raise FinalizationStoreError("E_FINALIZATION_REF_ESCAPE")
        pure = PurePosixPath(ref)
        if pure.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in pure.parts):
            raise FinalizationStoreError("E_FINALIZATION_REF_ESCAPE")
        candidate = self.root.joinpath(*pure.parts)
        try:
            candidate.resolve().relative_to(self.root.resolve())
        except ValueError as exc:
            raise FinalizationStoreError("E_FINALIZATION_REF_ESCAPE") from exc
        return candidate

    def _relative_ref(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError as exc:
            raise FinalizationStoreError("E_FINALIZATION_REF_ESCAPE") from exc

    @staticmethod
    def _document_bytes(document: Mapping[str, Any]) -> bytes:
        if not isinstance(document, Mapping):
            raise FinalizationStoreError("E_FINALIZATION_DOCUMENT_NOT_OBJECT")
        try:
            return canonical_bytes(dict(document))
        except (TypeError, ValueError) as exc:
            raise FinalizationStoreError("E_FINALIZATION_DOCUMENT_INVALID") from exc

    @staticmethod
    def _verify_existing(path: Path, payload: bytes, *, conflict_code: str) -> bool:
        if not path.exists():
            return False
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise FinalizationStoreError("E_FINALIZATION_FILE_UNREADABLE") from exc
        if existing != payload:
            raise FinalizationStoreError(conflict_code)
        return True

    @classmethod
    def _publish_immutable(cls, path: Path, payload: bytes, *, conflict_code: str) -> str:
        """通过同目录临时文件和 os.replace 发布完整文件。

        调用方必须持有 run 事务锁；目标已存在时只接受逐字节相同的幂等重放。
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if cls._verify_existing(path, payload, conflict_code=conflict_code):
            return "existing"
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if cls._verify_existing(path, payload, conflict_code=conflict_code):
                return "existing"
            os.replace(temporary, path)
            if path.read_bytes() != payload:
                raise FinalizationStoreError("E_FINALIZATION_PUBLISH_READBACK_MISMATCH")
            return "created"
        except FinalizationStoreError:
            raise
        except OSError as exc:
            raise FinalizationStoreError("E_FINALIZATION_PUBLISH_FAILED") from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def describe_document(self, document: Mapping[str, Any]) -> dict[str, Any]:
        """计算最终 blob 引用，不执行写入。"""
        payload = self._document_bytes(document)
        digest = canonical_hash(dict(document))
        return {
            "ref": f"objects/{digest.removeprefix('sha256:')}.json",
            "content_hash": digest,
            "size": len(payload),
        }

    def stage_document(self, transaction_id: str, role: str, document: Mapping[str, Any]) -> dict[str, Any]:
        """将候选写入事务 staging；同内容重放不改写已有文件。"""
        transaction = self.validate_transaction_id(transaction_id)
        safe_role = self._safe_identifier(role, error_code="E_FINALIZATION_ROLE_INVALID")
        payload = self._document_bytes(document)
        descriptor = self.describe_document(document)
        stage_path = self.staging_root / transaction / f"{safe_role}-{descriptor['content_hash'][7:]}.json"
        self._publish_immutable(stage_path, payload, conflict_code="E_FINALIZATION_STAGING_CONFLICT")
        return {**descriptor, "staging_ref": self._relative_ref(stage_path), "role": safe_role}

    def install_staged(self, descriptor: Mapping[str, Any]) -> dict[str, Any]:
        """校验 staging 后安装内容寻址 blob。"""
        expected_hash = descriptor.get("content_hash")
        if not isinstance(expected_hash, str) or not _CONTENT_HASH.fullmatch(expected_hash):
            raise FinalizationStoreError("E_FINALIZATION_CONTENT_HASH_INVALID")
        staging_ref = descriptor.get("staging_ref")
        final_ref = descriptor.get("ref")
        if not isinstance(staging_ref, str) or not isinstance(final_ref, str):
            raise FinalizationStoreError("E_FINALIZATION_DESCRIPTOR_INVALID")
        staging_path = self._resolve_ref(staging_ref)
        final_path = self._resolve_ref(final_ref)
        try:
            payload = staging_path.read_bytes()
            document = loads_strict(payload.decode("utf-8", errors="strict"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise FinalizationStoreError("E_FINALIZATION_STAGING_UNREADABLE") from exc
        if canonical_hash(document) != expected_hash or canonical_bytes(document) != payload:
            raise FinalizationStoreError("E_FINALIZATION_STAGING_HASH_MISMATCH")
        if len(payload) != descriptor.get("size"):
            raise FinalizationStoreError("E_FINALIZATION_STAGING_SIZE_MISMATCH")
        self._publish_immutable(final_path, payload, conflict_code="E_FINALIZATION_BLOB_CONFLICT")
        return {"ref": final_ref, "content_hash": expected_hash, "size": len(payload)}

    def publish_commit(self, document: Mapping[str, Any]) -> str:
        return self._publish_immutable(
            self.commit_path,
            self._document_bytes(document),
            conflict_code="E_FINALIZATION_COMMIT_CONFLICT",
        )

    def publish_receipt(self, document: Mapping[str, Any]) -> str:
        return self._publish_immutable(
            self.receipt_path,
            self._document_bytes(document),
            conflict_code="E_FINALIZATION_RECEIPT_CONFLICT",
        )

    @staticmethod
    def _read_document(path: Path, *, error_code: str) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
            document = loads_strict(raw.decode("utf-8", errors="strict"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise FinalizationStoreError(error_code) from exc
        if not isinstance(document, dict) or canonical_bytes(document) != raw:
            raise FinalizationStoreError(error_code)
        return document

    def read_commit(self) -> dict[str, Any] | None:
        return self._read_document(self.commit_path, error_code="E_FINALIZATION_COMMIT_INVALID")

    def read_receipt(self) -> dict[str, Any] | None:
        return self._read_document(self.receipt_path, error_code="E_FINALIZATION_RECEIPT_INVALID")

    def load_blob(self, descriptor: Mapping[str, Any]) -> dict[str, Any]:
        """读取并验证 manifest 指向的一个内容寻址 blob。"""
        ref = descriptor.get("ref")
        expected_hash = descriptor.get("content_hash")
        expected_size = descriptor.get("size")
        if not isinstance(ref, str) or not isinstance(expected_hash, str) or not _CONTENT_HASH.fullmatch(expected_hash):
            raise FinalizationStoreError("E_FINALIZATION_DESCRIPTOR_INVALID")
        expected_ref = f"objects/{expected_hash[7:]}.json"
        if ref != expected_ref:
            raise FinalizationStoreError("E_FINALIZATION_BLOB_REF_MISMATCH")
        path = self._resolve_ref(ref)
        try:
            raw = path.read_bytes()
            document = loads_strict(raw.decode("utf-8", errors="strict"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise FinalizationStoreError("E_FINALIZATION_BLOB_UNREADABLE") from exc
        if canonical_hash(document) != expected_hash or canonical_bytes(document) != raw:
            raise FinalizationStoreError("E_FINALIZATION_BLOB_HASH_MISMATCH")
        if not isinstance(expected_size, int) or expected_size != len(raw):
            raise FinalizationStoreError("E_FINALIZATION_BLOB_SIZE_MISMATCH")
        if not isinstance(document, dict):
            raise FinalizationStoreError("E_FINALIZATION_DOCUMENT_NOT_OBJECT")
        return document

    def load_blob_ref(self, ref: str) -> dict[str, Any]:
        """按 object ref 自带的摘要读取 blob，供扁平 commit manifest 使用。"""
        pure = PurePosixPath(ref) if isinstance(ref, str) else PurePosixPath("")
        if len(pure.parts) != 2 or pure.parts[0] != "objects" or not pure.parts[1].endswith(".json"):
            raise FinalizationStoreError("E_FINALIZATION_BLOB_REF_MISMATCH")
        digest = pure.parts[1][:-5]
        expected_hash = f"sha256:{digest}"
        if not _CONTENT_HASH.fullmatch(expected_hash):
            raise FinalizationStoreError("E_FINALIZATION_BLOB_REF_MISMATCH")
        path = self._resolve_ref(ref)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise FinalizationStoreError("E_FINALIZATION_BLOB_UNREADABLE") from exc
        return self.load_blob({"ref": ref, "content_hash": expected_hash, "size": size})
