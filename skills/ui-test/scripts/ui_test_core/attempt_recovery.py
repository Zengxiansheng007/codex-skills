"""执行恢复器：扫描无terminal attempt，追加interrupted或unresolved恢复事件。

宿主/进程能确认已消失时只追加interrupted恢复事件；
不能确认时追加unresolved；不得写passed/failed terminal，不阻断当前新run。
追加previous-attempt-unknown告警。提供可注入PID/host/time函数以便确定性测试。
"""

from __future__ import annotations

import os  # 检测进程存在性。
import platform  # 获取主机名摘要。
from datetime import datetime  # 可注入的时间函数。
from pathlib import Path  # 读取attempt目录。
from typing import Any, Callable, Mapping

from .execution_attempt_store import ExecutionAttemptStore, ExecutionAttemptStoreError


# ---------------------------------------------------------------------------
# 错误码
# ---------------------------------------------------------------------------

class AttemptRecoveryError(RuntimeError):
    """机器可读的恢复失败；不包含私有值。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# 恢复器
# ---------------------------------------------------------------------------

class AttemptRecovery:
    """扫描无terminal attempt并追加恢复事件。

    宿主/进程能确认已消失时只追加interrupted恢复事件；
    不能确认时追加unresolved。
    不得写passed/failed terminal，不阻断当前新run。
    """

    __slots__ = ("_store", "_now_func", "_pid_func", "_host_func", "_is_alive_func")

    def __init__(
        self,
        *,
        store: ExecutionAttemptStore,
        now_func: Callable[[], str] | None = None,
        pid_func: Callable[[], int] | None = None,
        host_func: Callable[[], str] | None = None,
        is_alive_func: Callable[[int, str], bool | None] | None = None,
    ) -> None:
        """初始化恢复器；接受可注入的PID/host/time函数以便确定性测试。"""
        self._store = store
        self._now_func = now_func or (lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
        self._pid_func = pid_func or (lambda: os.getpid())
        self._host_func = host_func or (lambda: platform.node())
        # 可注入的进程存活检测函数：接受pid和host，返回是否存活。
        self._is_alive_func = is_alive_func or _default_is_alive

    # -------------------------------------------------------------------
    # 扫描并恢复
    # -------------------------------------------------------------------

    def scan_and_recover(
        self,
        *,
        finalization_probe: Callable[[Mapping[str, Any]], str | None] | None = None,
    ) -> dict[str, Any]:
        """扫描所有无terminal attempt，追加恢复事件。

        返回包含recovered_attempts、unresolved_attempts和warnings的摘要。
        不阻断当前新run；追加previous-attempt-unknown告警。
        """
        unfinished = self._store.scan_unfinished_attempts()
        recovered: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        warnings: list[str] = []

        for attempt_info in unfinished:
            attempt_dir_name = attempt_info.get("attempt_dir", "")
            recorded_at = attempt_info.get("recorded_at", "")
            finalization_state = attempt_info.get("finalization_state", "not_started")
            if finalization_probe is not None:
                try:
                    probed = finalization_probe(attempt_info)
                    if probed in {
                        "unfinished", "finalizing", "commit_without_receipt", "receipt_without_terminal"
                    }:
                        finalization_state = probed
                except Exception:
                    finalization_state = "unresolved"
            recovered_from = {
                "not_started": "unfinished",
                "started_without_commit": "finalizing",
                "committed_without_terminal": "receipt_without_terminal",
            }.get(finalization_state, finalization_state)

            # start记录不持久化原PID/host，自动扫描只能诚实标为unresolved。
            try:
                self._store.append_recovery_event_by_attempt_dir(
                    attempt_dir_name=attempt_dir_name,
                    recovery_type="unresolved",
                    code=(
                        "E_PREVIOUS_FINALIZATION_UNRESOLVED"
                        if recovered_from != "unfinished"
                        else "E_PREVIOUS_ATTEMPT_UNRESOLVED"
                    ),
                    detail=f"unfinished attempt at {recorded_at}; finalization={recovered_from}",
                    recovered_from=recovered_from if recovered_from != "unresolved" else "unresolved",
                )
                unresolved.append({
                    "attempt_dir": attempt_dir_name,
                    "recovery_type": "unresolved",
                    "recorded_at": recorded_at,
                    "finalization_state": recovered_from,
                })
                warnings.append(f"previous-attempt-unknown:{attempt_dir_name}")
            except ExecutionAttemptStoreError:
                # 恢复失败不得阻断当前新run。
                warnings.append(f"recovery-failed:{attempt_dir_name}")

        return {
            "recovered_attempts": recovered,
            "unresolved_attempts": unresolved,
            "warnings": warnings,
            "total_scanned": len(unfinished),
        }

    # -------------------------------------------------------------------
    # 带PID确认的恢复（可选）
    # -------------------------------------------------------------------

    def recover_with_pid_check(
        self,
        *,
        run_id: str,
        node_id: str,
        recorded_pid: int,
        recorded_host: str,
    ) -> dict[str, Any]:
        """对特定attempt进行PID确认恢复。

        如果调用方能提供原attempt的PID和host，可以尝试确认进程是否已消失。
        宿主/进程能确认已消失时追加interrupted；否则追加unresolved。
        """
        if recorded_host != self._host_func():
            is_alive: bool | None = None  # 跨宿主PID没有可比性，必须保持unknown。
        else:
            is_alive = self._is_alive_func(recorded_pid, recorded_host)
        recovery_type = "interrupted" if is_alive is False else "unresolved"
        code = "E_PREVIOUS_ATTEMPT_INTERRUPTED" if recovery_type == "interrupted" else "E_PREVIOUS_ATTEMPT_UNRESOLVED"

        try:
            self._store.append_recovery_event(
                run_id=run_id,
                node_id=node_id,
                recovery_type=recovery_type,
                code=code,
                detail=f"pid:{recorded_pid} host:{recorded_host} alive:{is_alive}",
            )
        except ExecutionAttemptStoreError as exc:
            return {
                "run_id": run_id,
                "node_id": node_id,
                "recovery_type": "failed",
                "error_code": exc.code,
                "warning": f"recovery-failed:{exc.code}",
            }

        return {
            "run_id": run_id,
            "node_id": node_id,
            "recovery_type": recovery_type,
            "is_alive": is_alive,
            "warning": f"previous-attempt-{recovery_type}",
        }


# ---------------------------------------------------------------------------
# 默认进程存活检测
# ---------------------------------------------------------------------------

def _default_is_alive(pid: int, host: str) -> bool | None:
    """检测进程状态：True存在、False确认不存在、None表示无法确认。"""
    if pid <= 0:
        return None  # 无效PID不能证明旧进程已消失。

    if os.name == "nt":  # Windows平台。
        try:
            import ctypes
            from ctypes import wintypes
            # SYNCHRONIZE=0x00100000，用于检测进程是否存在。
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            handle = kernel32.OpenProcess(0x100000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True  # 进程存在。
            error_code = ctypes.get_last_error()
            if error_code == 87:  # ERROR_INVALID_PARAMETER：PID不存在。
                return False
            if error_code == 5:  # ERROR_ACCESS_DENIED：进程存在但不可访问。
                return True
            return None
        except Exception:
            return None  # API失败视为不可确认，追加unresolved。
    else:  # POSIX平台。
        try:
            os.kill(pid, 0)  # 发送信号0检测进程是否存在。
            return True
        except ProcessLookupError:
            return False  # 进程不存在。
        except PermissionError:
            return True  # 进程存在但无权限。
        except Exception:
            return None  # 未知错误视为不可确认。
