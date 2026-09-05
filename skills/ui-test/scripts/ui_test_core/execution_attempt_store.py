"""追加式ExecutionAttemptStore：早期diagnostics、独占创建attempt-start、追加事件与唯一terminal。

调用方显式提供受控evidence_root；diagnostics使用不含私有值的独立追加记录；
attempt按run/node稳定标识创建目录，attempt-start、每个事件、terminal均使用
独占创建或只追加文件，任何重复/冲突用稳定错误码fail closed。
所有持久化内容只允许摘要、稳定ID、错误码和相对引用。
"""

from __future__ import annotations

import hashlib  # 生成不暴露私有值的记录摘要。
import json  # 稳定序列化记录内容。
import os  # 检测文件存在性和独占创建。
import re  # 校验摘要格式。
import uuid  # 为并发diagnostics生成不冲突的独占记录名。
from datetime import datetime  # 可注入的时间函数。
from pathlib import Path  # 受控evidence_root下的目录操作。
from typing import Any, Callable, Mapping, Sequence

import rfc8785  # RFC 8785规范JSON序列化，确保摘要稳定。
from jsonschema import Draft202012Validator  # 投影返回前执行正式Schema校验。


# ---------------------------------------------------------------------------
# 错误码
# ---------------------------------------------------------------------------

class ExecutionAttemptStoreError(RuntimeError):
    """机器可读的存储失败；不包含私有值、绝对路径或异常文本。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# 敏感内容检测
# ---------------------------------------------------------------------------

# 禁止持久化的敏感模式；检测到即fail closed。
_SENSITIVE_PATTERNS = re.compile(
    r"(?i)(password|secret|token|cookie|authorization|api[_-]?key|bearer\s|sk-)"
)
# 绝对路径模式：盘符、POSIX根或反斜杠开头。
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _scan_sensitive(value: Any) -> str | None:
    """递归检测敏感内容；返回匹配模式或None。"""
    if isinstance(value, str):
        if _SENSITIVE_PATTERNS.search(value):
            return "sensitive-pattern-detected"
        if _ABSOLUTE_PATH_PATTERN.match(value):
            return "absolute-path-detected"
    elif isinstance(value, dict):
        for child in value.values():
            # 记录结构的键由受控Schema定义；只扫描值，避免把r2_authorization等合法字段名误报为凭据。
            found = _scan_sensitive(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _scan_sensitive(item)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# 摘要工具
# ---------------------------------------------------------------------------

def _sha256_dict(value: Mapping[str, Any]) -> str:
    """对dict进行RFC 8785规范序列化后SHA-256摘要。"""
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    """对bytes进行SHA-256摘要。"""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_text(value: str) -> str:
    """对UTF-8文本进行SHA-256摘要。"""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _relative_ref_is_safe(value: str) -> bool:
    """只接受正斜杠相对引用，拒绝盘符、根路径、反斜杠和父目录逃逸。"""
    if not isinstance(value, str) or not value or "\\" in value or _ABSOLUTE_PATH_PATTERN.match(value):
        return False
    return ".." not in Path(value).parts and not (len(value) > 1 and value[1] == ":")


def _utc_now() -> str:
    """返回当前UTC时间ISO格式字符串。"""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def derive_attempt_directory_name(*, run_id: str, node_id: str) -> str:
    """生成与ExecutionContext.attempt_ref和存储目录一致的稳定名称。"""
    if not isinstance(run_id, str) or not run_id or not isinstance(node_id, str) or not node_id:
        raise ExecutionAttemptStoreError("E_ATTEMPT_IDENTITY_REQUIRED")
    run_digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    node_digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:16]
    return f"{run_digest}-{node_digest}"


def _sanitize_for_persistence(
    *,
    code: str,
    detail: str = "",
    phase: str = "",
    evidence_ref: str = "",
) -> dict[str, Any]:
    """清洗要持久化的内容：只允许稳定错误码、摘要、相对引用。"""
    record: dict[str, Any] = {"code": code}
    if detail:
        # detail只保留摘要，不持久化原始文本。
        record["detail_digest"] = _sha256_text(detail)
    if phase:
        record["phase"] = phase
    if evidence_ref:
        if not _relative_ref_is_safe(evidence_ref):
            raise ExecutionAttemptStoreError("E_EVIDENCE_REF_ABSOLUTE_FORBIDDEN")
        record["evidence_ref"] = evidence_ref
    return record


# ---------------------------------------------------------------------------
# ExecutionAttemptStore
# ---------------------------------------------------------------------------

class ExecutionAttemptStore:
    """追加式执行尝试存储：独占创建attempt-start，追加事件，唯一terminal。

    调用方显式提供受控evidence_root目录。所有记录使用独占创建(O_CREAT|O_EXCL)
    或追加模式。任何重复创建或冲突用稳定错误码fail closed。
    持久化内容只允许摘要、稳定ID、错误码和相对引用。
    """

    __slots__ = (
        "_evidence_root",
        "_now_func",
        "_pid_func",
        "_host_func",
    )

    def __init__(
        self,
        *,
        evidence_root: str | Path,
        now_func: Callable[[], str] | None = None,
        pid_func: Callable[[], int] | None = None,
        host_func: Callable[[], str] | None = None,
    ) -> None:
        """初始化存储；调用方提供受控evidence_root和可注入的时间/PID/host函数。"""
        root = Path(evidence_root)
        try:
            root.mkdir(parents=True, exist_ok=True)  # hookspec已限定受控根，首次正式运行可安全创建。
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_EVIDENCE_ROOT_CREATE_FAILED") from exc
        if not root.is_dir():
            raise ExecutionAttemptStoreError("E_EVIDENCE_ROOT_NOT_DIRECTORY")
        self._evidence_root = root
        # 可注入函数用于确定性测试。
        self._now_func = now_func or _utc_now
        self._pid_func = pid_func or (lambda: os.getpid())
        self._host_func = host_func or (lambda: os.environ.get("COMPUTERNAME", "unknown"))

    # -------------------------------------------------------------------
    # 目录结构
    # -------------------------------------------------------------------

    def _attempt_dir(self, *, run_id: str, node_id: str) -> Path:
        """按run/node稳定标识创建目录路径。"""
        # node_id可能包含斜杠或特殊字符，用摘要绑定节点但不暴露长路径。
        return self._evidence_root / "attempts" / derive_attempt_directory_name(run_id=run_id, node_id=node_id)

    def _attempt_dir_by_name(self, attempt_dir_name: str) -> Path:
        """只接受内部SHA派生目录名，供不持有原始标识的恢复扫描使用。"""
        if not isinstance(attempt_dir_name, str) or not re.fullmatch(r"[0-9a-f]{16}-[0-9a-f]{16}", attempt_dir_name):
            raise ExecutionAttemptStoreError("E_ATTEMPT_DIRECTORY_NAME_INVALID")
        return self._evidence_root / "attempts" / attempt_dir_name

    def _diagnostics_dir(self) -> Path:
        """diagnostics使用独立目录。"""
        return self._evidence_root / "diagnostics"

    # -------------------------------------------------------------------
    # Diagnostics（早期拒绝，不创建attempt）
    # -------------------------------------------------------------------

    def append_diagnostics(
        self,
        *,
        run_id: str,
        node_id: str,
        code: str,
        detail: str = "",
    ) -> str:
        """追加diagnostics记录；不创建attempt目录。

        早期身份/配置/门禁失败仅写入diagnostics，不创建正式attempt。
        所有内容只保留摘要、稳定ID和错误码。
        """
        if not run_id or not isinstance(run_id, str):
            raise ExecutionAttemptStoreError("E_DIAGNOSTICS_RUN_ID_REQUIRED")
        if not node_id or not isinstance(node_id, str):
            raise ExecutionAttemptStoreError("E_DIAGNOSTICS_NODE_ID_REQUIRED")
        if not code or not isinstance(code, str):
            raise ExecutionAttemptStoreError("E_DIAGNOSTICS_CODE_REQUIRED")

        raw_input = {"run_id": run_id, "node_id": node_id, "code": code, "detail": detail}
        if _scan_sensitive(raw_input) is not None:
            raise ExecutionAttemptStoreError("E_DIAGNOSTICS_SENSITIVE_INPUT_FORBIDDEN")

        diag_dir = self._diagnostics_dir()
        diag_dir.mkdir(parents=True, exist_ok=True)

        # 稳定摘要，不持久化原始node_id或detail文本。
        node_digest = _sha256_text(node_id)
        run_digest = _sha256_text(run_id)
        timestamp = self._now_func()

        record: dict[str, Any] = {
            "schema_version": "ui-test.diagnostics.v1",
            "run_id_digest": run_digest,
            "node_id_digest": node_digest,
            "code": code,
            "recorded_at": timestamp,
        }
        if detail:
            # detail只保留摘要，不持久化原始文本。
            record["detail_digest"] = _sha256_text(detail)

        # 敏感检测：fail closed。
        found = _scan_sensitive(record)
        if found is not None:
            raise ExecutionAttemptStoreError(f"E_DIAGNOSTICS_{found.upper()}")

        # 每条diagnostic独占创建，避免多个PyCharm进程并发追加同一JSONL造成交错。
        diag_file = diag_dir / f"{uuid.uuid4().hex}.json"
        try:
            fd = os.open(str(diag_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            finally:
                os.close(fd)
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_DIAGNOSTICS_APPEND_FAILED") from exc
        return f"diagnostics/{diag_file.name}"

    # -------------------------------------------------------------------
    # Attempt-start（独占创建）
    # -------------------------------------------------------------------

    def create_attempt_start(
        self,
        *,
        run_id: str,
        node_id: str,
        case_id: str,
        branch_id: str,
        risk_level: str,
        execution_origin: str,
        approval_source: str,
        stable_runner_digest: str,
        project_config_digest: str,
        schema_version: str = "ui-test.execution-attempt.v1",
        session_id: str = "",
        finalization_mode: str = "legacy-v1",
        legacy_fixture: bool = False,
    ) -> str:
        """独占创建attempt-start文件；已存在则fail closed。

        R2锁成功后或R0/R1 setup开始时创建。attempt-start文件使用O_CREAT|O_EXCL
        确保独占创建，任何重复用稳定错误码拒绝。
        """
        if not run_id or not node_id or not case_id or not branch_id:
            raise ExecutionAttemptStoreError("E_ATTEMPT_IDENTITY_REQUIRED")
        if schema_version not in {"ui-test.execution-attempt.v1", "ui-test.execution-attempt.v2"}:
            raise ExecutionAttemptStoreError("E_ATTEMPT_SCHEMA_VERSION_INVALID")
        if schema_version == "ui-test.execution-attempt.v1" and legacy_fixture is not True:
            raise ExecutionAttemptStoreError("E_ATTEMPT_V1_HISTORICAL_READ_ONLY")
        if schema_version == "ui-test.execution-attempt.v2" and (
            not session_id
            or finalization_mode not in {"transaction-v1", "not_applicable_qualification", "not_applicable_read_only"}
        ):
            raise ExecutionAttemptStoreError("E_ATTEMPT_V2_FINALIZATION_IDENTITY_REQUIRED")
        if session_id and (len(session_id) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", session_id)):
            raise ExecutionAttemptStoreError("E_ATTEMPT_SESSION_ID_INVALID")
        raw_identity = {
            "run_id": run_id,
            "node_id": node_id,
            "case_id": case_id,
            "branch_id": branch_id,
            "risk_level": risk_level,
            "execution_origin": execution_origin,
            "approval_source": approval_source,
        }
        if _scan_sensitive(raw_identity) is not None:
            raise ExecutionAttemptStoreError("E_ATTEMPT_SENSITIVE_IDENTITY_FORBIDDEN")

        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        start_file = attempt_dir / "attempt-start.json"

        # 独占创建：如果文件已存在则fail closed。
        try:
            fd = os.open(str(start_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise ExecutionAttemptStoreError("E_ATTEMPT_START_ALREADY_EXISTS")
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_ATTEMPT_START_CREATE_FAILED") from exc

        timestamp = self._now_func()
        record: dict[str, Any] = {
            "schema_version": schema_version,
            "attempt_id": _sha256_text(f"{run_id}:{node_id}"),
            "run_id_digest": _sha256_text(run_id),
            "node_id_digest": _sha256_text(node_id),
            "case_id_digest": _sha256_text(case_id),
            "branch_id_digest": _sha256_text(branch_id),
            "risk_level": risk_level,
            "execution_origin": execution_origin,
            "approval_source": approval_source,
            "stable_runner_digest": stable_runner_digest,
            "project_config_digest": project_config_digest,
            "recorded_at": timestamp,
        }
        if schema_version == "ui-test.execution-attempt.v2":
            # V2把session与finalization能力固定在attempt-start，后续不得由结果文件反推。
            record["session_id"] = session_id
            record["session_id_digest"] = _sha256_text(session_id)
            record["finalization_mode"] = finalization_mode

        # 敏感检测：fail closed。
        found = _scan_sensitive(record)
        if found is not None:
            os.close(fd)
            os.unlink(start_file)  # 回滚空文件。
            raise ExecutionAttemptStoreError(f"E_ATTEMPT_START_{found.upper()}")

        content = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)

        return f"attempts/{attempt_dir.name}/attempt-start.json"

    # -------------------------------------------------------------------
    # 事件追加
    # -------------------------------------------------------------------

    def append_event(
        self,
        *,
        run_id: str,
        node_id: str,
        event_type: str,
        phase: str = "",
        code: str = "",
        detail: str = "",
        evidence_ref: str = "",
        exception_class: str = "",
        message_digest: str = "",
        transaction_id: str = "",
        recorded_at: str = "",
    ) -> str:
        """追加事件记录到events.jsonl；不覆盖历史。

        setup/call/teardown阶段事件均追加到同一文件。
        所有内容只保留摘要、稳定ID和错误码。
        """
        valid_types = {
            "detected", "admitted", "executing", "interrupted", "unresolved", "unfinished",
            "finalization_started", "finalization_committed", "finalization_failed", "session_finished",
        }
        if event_type not in valid_types:
            raise ExecutionAttemptStoreError("E_EVENT_TYPE_INVALID")

        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        start_file = attempt_dir / "attempt-start.json"
        if not start_file.exists():
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")

        timestamp = recorded_at or self._now_func()
        if not isinstance(timestamp, str) or not timestamp:
            raise ExecutionAttemptStoreError("E_EVENT_RECORDED_AT_INVALID")
        record: dict[str, Any] = {
            "event_type": event_type,
            "recorded_at": timestamp,
        }
        if phase:
            record["phase"] = phase
        if code:
            record["code"] = code
        if detail:
            record["detail_digest"] = _sha256_text(detail)
        if evidence_ref:
            if not _relative_ref_is_safe(evidence_ref):
                raise ExecutionAttemptStoreError("E_EVENT_EVIDENCE_REF_ABSOLUTE_FORBIDDEN")
            record["evidence_ref"] = evidence_ref
        if exception_class:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", exception_class):
                raise ExecutionAttemptStoreError("E_EVENT_EXCEPTION_CLASS_INVALID")
            record["exception_class"] = exception_class
        if message_digest:
            if not _SHA256.fullmatch(message_digest):
                raise ExecutionAttemptStoreError("E_EVENT_MESSAGE_DIGEST_INVALID")
            record["message_digest"] = message_digest
        if transaction_id:
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", transaction_id):
                raise ExecutionAttemptStoreError("E_EVENT_TRANSACTION_ID_INVALID")
            record["transaction_id"] = transaction_id

        # 敏感检测：fail closed。
        found = _scan_sensitive(record)
        if found is not None:
            raise ExecutionAttemptStoreError(f"E_EVENT_{found.upper()}")

        events_file = attempt_dir / "events.jsonl"
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return f"attempts/{attempt_dir.name}/events.jsonl"

    # -------------------------------------------------------------------
    # Terminal（独占创建，唯一终态）
    # -------------------------------------------------------------------

    def create_terminal(
        self,
        *,
        run_id: str,
        node_id: str,
        status: str,
        code: str = "",
        detail: str = "",
        commit_manifest_ref: str = "",
        commit_manifest_hash: str = "",
        receipt_ref: str = "",
        receipt_hash: str = "",
        pre_terminal_events_hash: str = "",
        recovery_mode: str = "none",
        finalization_run_root: str | Path | None = None,
    ) -> str:
        """独占创建terminal文件；已存在则fail closed，确保唯一终态。

        正常setup/call/teardown路径只允许一个terminal。
        恢复器不得调用此方法写passed/failed terminal。
        """
        valid_statuses = {
            "passed", "failed", "error", "cancelled", "timed_out", "interrupted", "unresolved", "write_outcome_unknown"
        }
        if status not in valid_statuses:
            raise ExecutionAttemptStoreError("E_TERMINAL_STATUS_INVALID")

        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        terminal_file = attempt_dir / "terminal.json"

        start = self.read_attempt_start(run_id=run_id, node_id=node_id)
        if start is None:
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        is_transactional_pass = (
            start.get("schema_version") == "ui-test.execution-attempt.v2"
            and start.get("finalization_mode") == "transaction-v1"
            and status == "passed"
        )
        if is_transactional_pass:
            # V2 normal run只有commit、receipt与对应事件均齐全时才允许passed terminal。
            if not all((commit_manifest_ref, commit_manifest_hash, receipt_ref, receipt_hash)):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_CLOSURE_REQUIRED")
            if not _SHA256.fullmatch(commit_manifest_hash) or not _SHA256.fullmatch(receipt_hash):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_HASH_INVALID")
            if not _SHA256.fullmatch(pre_terminal_events_hash):
                raise ExecutionAttemptStoreError("E_TERMINAL_PRE_TERMINAL_HASH_REQUIRED")
            if any(not _relative_ref_is_safe(ref) for ref in (commit_manifest_ref, receipt_ref)):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_REF_INVALID")
            if not any(event.get("event_type") == "finalization_committed" for event in self.read_events(run_id=run_id, node_id=node_id)):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_EVENT_REQUIRED")
            if finalization_run_root is None:
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_READBACK_REQUIRED")
            try:
                from .finalization_transaction import FinalizationTransaction  # 延迟导入避免模块初始化耦合。

                closure = FinalizationTransaction(finalization_run_root).read_committed()
            except Exception as exc:
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_READBACK_FAILED") from exc
            if closure is None or closure.get("status") != "committed":
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_NOT_COMMITTED")
            manifest = closure["manifest"]
            receipt = closure["receipt"]
            expected_commit_ref = f"runs/{run_id}/finalization/finalization-commit.json"
            expected_receipt_ref = f"runs/{run_id}/finalization/finalization-receipt.json"
            if commit_manifest_ref != expected_commit_ref or receipt_ref != expected_receipt_ref:
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_REF_MISMATCH")
            if commit_manifest_hash != _sha256_dict(manifest) or receipt_hash != _sha256_dict(receipt):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_CONTENT_HASH_MISMATCH")
            if (
                manifest.get("run_id") != run_id
                or manifest.get("node_id") != node_id
                or manifest.get("pre_terminal_events_hash") != pre_terminal_events_hash
                or closure["run_result"].get("pre_terminal_events_hash") != pre_terminal_events_hash
            ):
                raise ExecutionAttemptStoreError("E_TERMINAL_FINALIZATION_IDENTITY_MISMATCH")

        # 独占创建：如果文件已存在则fail closed。
        try:
            fd = os.open(str(terminal_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise ExecutionAttemptStoreError("E_TERMINAL_ALREADY_EXISTS")
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_TERMINAL_CREATE_FAILED") from exc

        timestamp = self._now_func()
        record: dict[str, Any] = {
            "status": status,
            "is_unique_terminal": True,
            "recorded_at": timestamp,
        }
        if code:
            record["code"] = code
        if detail:
            record["detail_digest"] = _sha256_text(detail)
        if commit_manifest_ref:
            record["commit_manifest_ref"] = commit_manifest_ref
            record["commit_manifest_hash"] = commit_manifest_hash
        if receipt_ref:
            record["receipt_ref"] = receipt_ref
            record["receipt_hash"] = receipt_hash
        if pre_terminal_events_hash:
            if not _SHA256.fullmatch(pre_terminal_events_hash):
                raise ExecutionAttemptStoreError("E_TERMINAL_PRE_TERMINAL_HASH_INVALID")
            record["pre_terminal_events_hash"] = pre_terminal_events_hash
        if recovery_mode:
            record["recovery_mode"] = recovery_mode

        # 敏感检测：fail closed。
        found = _scan_sensitive(record)
        if found is not None:
            os.close(fd)
            os.unlink(terminal_file)
            raise ExecutionAttemptStoreError(f"E_TERMINAL_{found.upper()}")

        content = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)

        return f"attempts/{attempt_dir.name}/terminal.json"

    # -------------------------------------------------------------------
    # 恢复事件追加（只追加interrupted/unresolved，不创建terminal）
    # -------------------------------------------------------------------

    def append_recovery_event(
        self,
        *,
        run_id: str,
        node_id: str,
        recovery_type: str,
        code: str = "",
        detail: str = "",
    ) -> str:
        """追加恢复事件；只允许interrupted或unresolved，不写terminal。

        宿主/进程能确认已消失时追加interrupted；不能确认时追加unresolved。
        不得写passed/failed terminal，不阻断当前新run。
        """
        valid_types = {"interrupted", "unresolved"}
        if recovery_type not in valid_types:
            raise ExecutionAttemptStoreError("E_RECOVERY_TYPE_INVALID")

        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        start_file = attempt_dir / "attempt-start.json"
        if not start_file.exists():
            raise ExecutionAttemptStoreError("E_RECOVERY_ATTEMPT_NOT_FOUND")

        terminal_file = attempt_dir / "terminal.json"
        if terminal_file.exists():
            # 已有terminal的attempt不需要恢复。
            raise ExecutionAttemptStoreError("E_RECOVERY_ATTEMPT_HAS_TERMINAL")

        timestamp = self._now_func()
        record: dict[str, Any] = {
            "event_type": recovery_type,
            "is_recovery": True,
            "recorded_at": timestamp,
        }
        if code:
            record["code"] = code
        if detail:
            record["detail_digest"] = _sha256_text(detail)

        # 敏感检测：fail closed。
        found = _scan_sensitive(record)
        if found is not None:
            raise ExecutionAttemptStoreError(f"E_RECOVERY_{found.upper()}")

        recovery_file = attempt_dir / "recovery.jsonl"
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with open(recovery_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return f"attempts/{attempt_dir.name}/recovery.jsonl"

    def append_recovery_event_by_attempt_dir(
        self,
        *,
        attempt_dir_name: str,
        recovery_type: str,
        code: str = "",
        detail: str = "",
        recovered_from: str = "unfinished",
    ) -> str:
        """按扫描得到的内部目录追加恢复事件，避免对摘要再次哈希。"""
        if recovery_type not in {"interrupted", "unresolved"}:
            raise ExecutionAttemptStoreError("E_RECOVERY_TYPE_INVALID")
        if recovered_from not in {
            "unfinished", "finalizing", "commit_without_receipt", "receipt_without_terminal", "interrupted", "unresolved"
        }:
            raise ExecutionAttemptStoreError("E_RECOVERY_SOURCE_INVALID")
        attempt_dir = self._attempt_dir_by_name(attempt_dir_name)
        if not (attempt_dir / "attempt-start.json").is_file():
            raise ExecutionAttemptStoreError("E_RECOVERY_ATTEMPT_NOT_FOUND")
        if (attempt_dir / "terminal.json").exists():
            raise ExecutionAttemptStoreError("E_RECOVERY_ATTEMPT_HAS_TERMINAL")
        if (attempt_dir / "recovery.jsonl").exists():
            raise ExecutionAttemptStoreError("E_RECOVERY_ALREADY_RECORDED")
        record: dict[str, Any] = {
            "event_type": recovery_type,
            "is_recovery": True,
            "recorded_at": self._now_func(),
            "recovered_from": recovered_from,
        }
        if code:
            record["code"] = code
        if detail:
            record["detail_digest"] = _sha256_text(detail)
        if _scan_sensitive(record) is not None:
            raise ExecutionAttemptStoreError("E_RECOVERY_SENSITIVE_INPUT_FORBIDDEN")
        recovery_file = attempt_dir / "recovery.jsonl"
        try:
            fd = os.open(str(recovery_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            finally:
                os.close(fd)
        except FileExistsError as exc:
            raise ExecutionAttemptStoreError("E_RECOVERY_ALREADY_RECORDED") from exc
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_RECOVERY_APPEND_FAILED") from exc
        return f"attempts/{attempt_dir.name}/recovery.jsonl"

    # -------------------------------------------------------------------
    # 读取与投影接口
    # -------------------------------------------------------------------

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        """读取JSON文件。"""
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_jsonl_file(self, path: Path) -> list[dict[str, Any]]:
        """读取JSONL文件，返回每行解析后的dict列表。"""
        records: list[dict[str, Any]] = []
        text = path.read_text(encoding="utf-8")
        for line in text.strip().split("\n"):
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    def write_execution_context(
        self,
        *,
        run_id: str,
        node_id: str,
        context_document: Mapping[str, Any],
        legacy_fixture: bool = False,
    ) -> str:
        """独占写execution-context.json，保存Schema-valid ExecutionContextV2/V3并提供ref/hash读取。

        plugin在attempt-start之后写context；任何失败使pytest失败。
        context_document必须通过Schema校验和敏感检测。
        """
        if not run_id or not node_id:
            raise ExecutionAttemptStoreError("E_ATTEMPT_IDENTITY_REQUIRED")
        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        start_file = attempt_dir / "attempt-start.json"
        if not start_file.exists():
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        # 敏感检测：fail closed。
        if _scan_sensitive(dict(context_document)) is not None:
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_SENSITIVE_INPUT_FORBIDDEN")
        context_version = context_document.get("schema_version")
        if context_version == "ui-test.execution-context.v2" and legacy_fixture is not True:
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_V2_HISTORICAL_READ_ONLY")
        context_schema_name = {
            "ui-test.execution-context.v2": "execution-context-v2.schema.json",
            "ui-test.execution-context.v3": "execution-context-v3.schema.json",
        }.get(context_version)
        if context_schema_name is None:
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_VERSION_INVALID")
        context_schema = json.loads(
            (Path(__file__).resolve().parents[2] / "schemas" / context_schema_name).read_text(encoding="utf-8")
        )
        if list(Draft202012Validator(context_schema).iter_errors(dict(context_document))):
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_SCHEMA_INVALID")
        context_file = attempt_dir / "execution-context.json"
        # 独占创建：如果文件已存在则fail closed。
        try:
            fd = os.open(str(context_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_ALREADY_EXISTS")
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_EXECUTION_CONTEXT_CREATE_FAILED") from exc
        content = json.dumps(dict(context_document), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        return f"attempts/{attempt_dir.name}/execution-context.json"

    def read_execution_context(self, *, run_id: str, node_id: str) -> dict[str, Any] | None:
        """ST-008：读取execution-context.json；不存在返回None。"""
        context_file = self._attempt_dir(run_id=run_id, node_id=node_id) / "execution-context.json"
        if not context_file.exists():
            return None
        return self._read_json_file(context_file)

    def read_execution_context_ref_and_hash(self, *, run_id: str, node_id: str) -> tuple[str, str] | None:
        """ST-008：读取execution-context.json的相对ref和hash。"""
        context = self.read_execution_context(run_id=run_id, node_id=node_id)
        if context is None:
            return None
        attempt_dir_name = derive_attempt_directory_name(run_id=run_id, node_id=node_id)
        ref = f"attempts/{attempt_dir_name}/execution-context.json"
        context_hash = _sha256_dict(context)
        return (ref, context_hash)

    def write_finalization_failure_receipt(
        self,
        *,
        run_id: str,
        node_id: str,
        session_id: str,
        transaction_id: str,
        error_code: str,
        exception_class: str,
        message_digest: str,
    ) -> tuple[str, dict[str, Any]]:
        """当项目target不可用时，在attempt内原子封存Schema有效的脱敏失败receipt。"""
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", session_id or ""):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_SESSION_ID_INVALID")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,160}", transaction_id or ""):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_TRANSACTION_ID_INVALID")
        if not re.fullmatch(r"E_[A-Z0-9_]+", error_code or ""):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_ERROR_CODE_INVALID")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", exception_class or ""):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_EXCEPTION_CLASS_INVALID")
        if not _SHA256.fullmatch(message_digest or ""):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_MESSAGE_DIGEST_INVALID")
        attempt_dir = self._attempt_dir(run_id=run_id, node_id=node_id)
        if not (attempt_dir / "attempt-start.json").is_file():
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        receipt: dict[str, Any] = {
            "schema_version": "ui-test.run-finalization-receipt.v1",
            "transaction_id": transaction_id,
            "session_id": session_id,
            "run_id": run_id,
            "node_id": node_id,
            "status": "failed",
            "recovery_mode": "none",
            "error_code": error_code,
            "exception_class": exception_class,
            "message_digest": message_digest,
            "recorded_at": self._now_func(),
        }
        receipt["receipt_hash"] = _sha256_dict(receipt)
        schema = json.loads(
            (Path(__file__).resolve().parents[2] / "schemas" / "run-finalization-receipt-v1.schema.json").read_text(encoding="utf-8")
        )
        if list(Draft202012Validator(schema).iter_errors(receipt)):
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_SCHEMA_INVALID")
        target = attempt_dir / "finalization-failure-receipt.json"
        content = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            existing = self._read_json_file(target)
            comparable = ("transaction_id", "session_id", "run_id", "node_id", "status", "error_code", "exception_class", "message_digest")
            if any(existing.get(field) != receipt.get(field) for field in comparable):
                raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_CONFLICT")
            return f"attempts/{attempt_dir.name}/finalization-failure-receipt.json", existing
        except OSError as exc:
            raise ExecutionAttemptStoreError("E_FAILURE_RECEIPT_CREATE_FAILED") from exc
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        return f"attempts/{attempt_dir.name}/finalization-failure-receipt.json", receipt

    def read_attempt_start(self, *, run_id: str, node_id: str) -> dict[str, Any] | None:
        """读取attempt-start记录；不存在返回None。"""
        start_file = self._attempt_dir(run_id=run_id, node_id=node_id) / "attempt-start.json"
        if not start_file.exists():
            return None
        return self._read_json_file(start_file)

    def read_events(self, *, run_id: str, node_id: str) -> list[dict[str, Any]]:
        """读取事件列表；不存在返回空列表。"""
        events_file = self._attempt_dir(run_id=run_id, node_id=node_id) / "events.jsonl"
        if not events_file.exists():
            return []
        return self._read_jsonl_file(events_file)

    def read_terminal(self, *, run_id: str, node_id: str) -> dict[str, Any] | None:
        """读取terminal记录；不存在返回None（表示unfinished）。"""
        terminal_file = self._attempt_dir(run_id=run_id, node_id=node_id) / "terminal.json"
        if not terminal_file.exists():
            return None
        return self._read_json_file(terminal_file)

    def read_recovery_events(self, *, run_id: str, node_id: str) -> list[dict[str, Any]]:
        """读取恢复事件列表；不存在返回空列表。"""
        recovery_file = self._attempt_dir(run_id=run_id, node_id=node_id) / "recovery.jsonl"
        if not recovery_file.exists():
            return []
        return self._read_jsonl_file(recovery_file)

    def compute_attempt_hash(self, *, run_id: str, node_id: str) -> str:
        """计算当前attempt所有不可变记录的稳定摘要。"""
        start = self.read_attempt_start(run_id=run_id, node_id=node_id)
        if start is None:
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        events = self.read_events(run_id=run_id, node_id=node_id)
        terminal = self.read_terminal(run_id=run_id, node_id=node_id)
        recovery = self.read_recovery_events(run_id=run_id, node_id=node_id)

        material = {
            "attempt_start": start,
            "events": events,
            "terminal": terminal,
            "recovery": recovery,
        }
        return _sha256_dict(material)

    def compute_pre_terminal_hash(
        self,
        *,
        run_id: str,
        node_id: str,
        additional_events: Sequence[Mapping[str, Any]] | None = None,
    ) -> str:
        """计算完整pre-terminal闭包；允许预绑定commit后将追加的确定事件。"""
        start = self.read_attempt_start(run_id=run_id, node_id=node_id)
        if start is None:
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        material = {
            "attempt_start": start,
            "execution_context": self.read_execution_context(run_id=run_id, node_id=node_id),
            "events": self.read_events(run_id=run_id, node_id=node_id)
            + [dict(event) for event in (additional_events or [])],
            "recovery": self.read_recovery_events(run_id=run_id, node_id=node_id),
        }
        return _sha256_dict(material)

    # -------------------------------------------------------------------
    # 投影为Schema对象（读取接口）
    # -------------------------------------------------------------------

    def project_attempt(
        self,
        *,
        run_id: str,
        node_id: str,
        case_id: str,
        branch_id: str,
    ) -> dict[str, Any]:
        """从不可变记录投影execution-attempt-v1/v2 Schema对象。

        没有terminal的合法attempt投影为unfinished。
        已存在terminal仍必须符合唯一终态。
        """
        start = self.read_attempt_start(run_id=run_id, node_id=node_id)
        if start is None:
            raise ExecutionAttemptStoreError("E_ATTEMPT_NOT_STARTED")
        is_v2 = start.get("schema_version") == "ui-test.execution-attempt.v2"
        expected_digests = {
            "run_id_digest": _sha256_text(run_id),
            "node_id_digest": _sha256_text(node_id),
            "case_id_digest": _sha256_text(case_id),
            "branch_id_digest": _sha256_text(branch_id),
        }
        if any(start.get(key) != digest for key, digest in expected_digests.items()):
            raise ExecutionAttemptStoreError("E_ATTEMPT_PROJECTION_IDENTITY_MISMATCH")

        events = self.read_events(run_id=run_id, node_id=node_id)
        terminal = self.read_terminal(run_id=run_id, node_id=node_id)
        recovery_events = self.read_recovery_events(run_id=run_id, node_id=node_id)

        # 构建diagnostics_admission投影。
        diagnostics_admission: dict[str, Any] = {
            "admitted": True,  # attempt-start存在即表示已准入。
            "admission_digest": start.get("stable_runner_digest", ""),
        }

        # 构建events投影。
        projected_events: list[dict[str, Any]] = []
        for event in events:
            projected: dict[str, Any] = {
                "event_type": event["event_type"],
                "recorded_at": event["recorded_at"],
                "event_digest": _sha256_dict(event),
            }
            if "phase" in event:
                projected["phase"] = event["phase"]
            if "code" in event:
                if is_v2:
                    projected["code"] = event["code"]
                else:
                    projected["detail"] = event["code"]  # V1只保留错误码到detail。
            if is_v2 and "detail_digest" in event:
                projected["detail_digest"] = event["detail_digest"]
            if is_v2 and "exception_class" in event:
                projected["exception_class"] = event["exception_class"]
            if is_v2 and "message_digest" in event:
                projected["message_digest"] = event["message_digest"]
            if is_v2 and "transaction_id" in event:
                projected["transaction_id"] = event["transaction_id"]
            if "evidence_ref" in event:
                projected["evidence_ref"] = event["evidence_ref"]
            projected_events.append(projected)

        # 如果没有terminal且没有recovery，仅读取时派生unfinished事件；绝不伪造terminal。
        if terminal is None and not recovery_events:
            projected_events.append({
                "event_type": "unfinished",
                "recorded_at": start["recorded_at"],
                "event_digest": _sha256_dict({"projected": "unfinished", "attempt_id": start["attempt_id"]}),
            })
        elif terminal is not None:
            terminal_event = {
                "event_type": "terminal",
                "recorded_at": terminal["recorded_at"],
                "event_digest": _sha256_dict(terminal),
            }
            if is_v2:
                terminal_event["code"] = terminal.get("code", "PYTEST_TERMINAL")
            else:
                terminal_event["detail"] = terminal.get("code", "PYTEST_TERMINAL")
            projected_events.append(terminal_event)
        else:
            # 恢复事件是append-only事实，作为事件与recovery对象投影；仍不生成terminal。
            for recovery_event in recovery_events:
                recovery_projection = {
                    "event_type": recovery_event["event_type"],
                    "recorded_at": recovery_event["recorded_at"],
                    "event_digest": _sha256_dict(recovery_event),
                }
                if is_v2:
                    recovery_projection["code"] = recovery_event.get("code", "RECOVERY")
                else:
                    recovery_projection["detail"] = recovery_event.get("code", "RECOVERY")
                projected_events.append(recovery_projection)

        terminal_projection = None
        if terminal is not None:
            terminal_projection = {
                "status": terminal["status"],
                "recorded_at": terminal["recorded_at"],
                "terminal_digest": _sha256_dict(terminal),
                "is_unique_terminal": True,
            }
            if is_v2 and terminal.get("code"):
                terminal_projection["code"] = terminal["code"]

        projection: dict[str, Any] = {
            "schema_version": "ui-test.execution-attempt.v2" if is_v2 else "ui-test.execution-attempt.v1",
            "attempt_id": start.get("attempt_id", _sha256_text(f"{run_id}:{node_id}")),
            "run_id": run_id,
            "node_id": node_id,
            "case_id": case_id,
            "branch_id": branch_id,
            "diagnostics_admission": diagnostics_admission,
            "events": projected_events,
        }
        if terminal_projection is not None:
            projection["terminal"] = terminal_projection

        if is_v2:
            projection["session_id"] = start["session_id"]
            projection["finalization_mode"] = start["finalization_mode"]
            projection["pre_terminal_events_hash"] = (
                terminal.get("pre_terminal_events_hash")
                if terminal is not None and terminal.get("pre_terminal_events_hash")
                else self.compute_pre_terminal_hash(run_id=run_id, node_id=node_id)
            )
            if terminal is not None:
                ref_fields = {
                    "commit_manifest_ref": "finalization_commit_ref",
                    "commit_manifest_hash": "finalization_commit_hash",
                    "receipt_ref": "finalization_receipt_ref",
                    "receipt_hash": "finalization_receipt_hash",
                }
                for source, target in ref_fields.items():
                    if terminal.get(source):
                        projection[target] = terminal[source]

        # 如果有恢复事件，添加recovery投影。
        if recovery_events:
            last_recovery = recovery_events[-1]
            raw_events = {event.get("event_type") for event in events}
            recovered_from = last_recovery.get("recovered_from") or (
                "commit_without_receipt" if "finalization_committed" in raw_events
                else "finalizing" if "finalization_started" in raw_events
                else "unfinished"
            )
            recovery_projection = {
                "recovered_from": recovered_from,
                "recovery_event": {
                    "event_type": last_recovery["event_type"],
                    "recorded_at": last_recovery["recorded_at"],
                    "event_digest": _sha256_dict(last_recovery),
                },
                "recovery_digest": _sha256_dict({"recovery": recovery_events}),
            }
            if is_v2:
                recovery_projection["recovery_event"]["code"] = last_recovery.get("code", "RECOVERY")
                recovery_projection["recovery_mode"] = "post-run"
            projection["recovery"] = recovery_projection

        schema_name = "execution-attempt-v2.schema.json" if is_v2 else "execution-attempt-v1.schema.json"
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(projection), key=lambda error: list(error.absolute_path))
        if errors:
            raise ExecutionAttemptStoreError("E_ATTEMPT_PROJECTION_SCHEMA_INVALID")
        return projection

    # -------------------------------------------------------------------
    # 扫描无terminal attempt
    # -------------------------------------------------------------------

    def scan_unfinished_attempts(self) -> list[dict[str, Any]]:
        """扫描所有无terminal的attempt目录。"""
        attempts_root = self._evidence_root / "attempts"
        if not attempts_root.exists():
            return []

        unfinished: list[dict[str, Any]] = []
        for attempt_dir in attempts_root.iterdir():
            if not attempt_dir.is_dir():
                continue
            start_file = attempt_dir / "attempt-start.json"
            terminal_file = attempt_dir / "terminal.json"
            if start_file.exists() and not terminal_file.exists() and not (attempt_dir / "recovery.jsonl").exists():
                try:
                    start = self._read_json_file(start_file)
                    context_file = attempt_dir / "execution-context.json"
                    context = self._read_json_file(context_file) if context_file.is_file() else {}
                    events = self._read_jsonl_file(attempt_dir / "events.jsonl") if (attempt_dir / "events.jsonl").is_file() else []
                    finalization_state = "not_started"
                    if any(event.get("event_type") == "finalization_committed" for event in events):
                        finalization_state = "committed_without_terminal"
                    elif any(event.get("event_type") == "finalization_failed" for event in events):
                        finalization_state = "failed_without_terminal"
                    elif any(event.get("event_type") == "finalization_started" for event in events):
                        finalization_state = "started_without_commit"
                    unfinished.append({
                        "attempt_dir": attempt_dir.name,
                        "attempt_id": start.get("attempt_id", ""),
                        "run_id_digest": start.get("run_id_digest", ""),
                        "node_id_digest": start.get("node_id_digest", ""),
                        "recorded_at": start.get("recorded_at", ""),
                        "finalization_state": finalization_state,
                        "run_id": context.get("run_id", ""),
                        "node_id": context.get("node_id", ""),
                    })
                except Exception:
                    pass  # 损坏目录不得阻断扫描。
        return unfinished

    # -------------------------------------------------------------------
    # 历史摘要不变性验证
    # -------------------------------------------------------------------

    def verify_history_unchanged(
        self,
        *,
        run_id: str,
        node_id: str,
        expected_hash: str,
    ) -> bool:
        """验证历史记录摘要是否未被修改。"""
        current_hash = self.compute_attempt_hash(run_id=run_id, node_id=node_id)
        return current_hash == expected_hash
