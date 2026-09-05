"""跨进程非阻塞串行锁：保证同项目产品环境的R2节点在BrowserContext前串行。

使用Windows命名Mutex实现跨进程互斥；锁名称仅由project_group、product、environment
规范化后SHA-256派生，不包含私有值。非Windows平台或API失败fail closed。
锁冲突立即失败不排队；异常进程结束后操作系统自动释放Mutex，锁可恢复。
"""

from __future__ import annotations

import hashlib  # 派生不暴露私有值的锁名称。
import os  # 检测平台和读取环境变量用于xdist检测。
import sys  # 确认平台。
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 错误码
# ---------------------------------------------------------------------------

class R2ProjectLockError(RuntimeError):
    """机器可读的锁失败；不包含私有值或路径。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# Windows命名Mutex底层绑定
# ---------------------------------------------------------------------------

_IS_WINDOWS = sys.platform == "win32" or os.name == "nt"

if _IS_WINDOWS:  # 仅在Windows平台绑定原生API；其他平台fail closed。
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # 加载kernel32用于Mutex API。

    # CreateMutexW签名：LPSECURITY_ATTRIBUTES(可None), BOOL(初始属主), LPCWSTR(名称)。
    _kernel32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
    _kernel32.CreateMutexW.restype = wintypes.HANDLE

    # WaitForSingleObject签名：HANDLE, DWORD(毫秒)。
    _kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel32.WaitForSingleObject.restype = wintypes.DWORD

    # ReleaseMutex签名：HANDLE。
    _kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    _kernel32.ReleaseMutex.restype = wintypes.BOOL

    # CloseHandle签名：HANDLE。
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL

    _WAIT_TIMEOUT = 0x102  # WAIT_TIMEOUT常量：未获锁。
    _WAIT_ABANDONED = 0x80  # WAIT_ABANDONED：前持有进程异常退出，锁已恢复。
    _WAIT_OBJECT_0 = 0x0  # WAIT_OBJECT_0：成功获取。
    _ERROR_ALREADY_EXISTS = 183  # ERROR_ALREADY_EXISTS：Mutex已由其他进程创建。
else:
    _kernel32 = None  # 非Windows平台无原生绑定。


# ---------------------------------------------------------------------------
# 锁名称派生
# ---------------------------------------------------------------------------

_LOCK_PREFIX = "Local\\UIT-R2-"  # PyCharm进程位于同一登录会话；避免扩大到其他用户会话的可预测全局对象。


def _derive_lock_name(*, project_group: str, product: str, environment: str) -> str:
    """从项目配置scope派生不暴露私有值的锁名称。

    仅使用project_group、product、environment三个已验证配置字段，
    规范化后SHA-256派生。不接受调用方提供的任意锁名。
    """
    if not project_group or not isinstance(project_group, str):
        raise R2ProjectLockError("E_R2_LOCK_SCOPE_INVALID")
    if not product or not isinstance(product, str):
        raise R2ProjectLockError("E_R2_LOCK_SCOPE_INVALID")
    if not environment or not isinstance(environment, str):
        raise R2ProjectLockError("E_R2_LOCK_SCOPE_INVALID")
    # 规范化：小写并去除首尾空白，确保不同大小写或空白写法映射到同一锁。
    normalized = "|".join((
        project_group.strip().lower(),
        product.strip().lower(),
        environment.strip().lower(),
    ))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{_LOCK_PREFIX}{digest}"


# ---------------------------------------------------------------------------
# 锁对象
# ---------------------------------------------------------------------------


class R2ProjectLock:
    """跨进程非阻塞串行锁，封装Windows命名Mutex生命周期。

    非阻塞acquire：锁已持有立即失败（E_R2_PROJECT_LOCK_HELD）。
    非Windows平台或API失败fail closed。
    重复release安全拒绝（返回False，不伪造成功）。
    异常进程退出后操作系统自动释放Mutex，下次acquire可恢复。
    """

    __slots__ = ("_lock_name", "_handle", "_held")

    def __init__(self, *, project_group: str, product: str, environment: str) -> None:
        """从已验证项目配置scope创建锁；不接受任意锁名。"""
        self._lock_name: str = _derive_lock_name(
            project_group=project_group,
            product=product,
            environment=environment,
        )
        self._handle: Any = None  # Windows HANDLE，None表示未持有。
        self._held: bool = False

    @property
    def lock_name(self) -> str:
        """返回锁名称摘要（仅SHA-256派生，不含私有值）。"""
        return self._lock_name

    @property
    def is_held(self) -> bool:
        """当前进程是否持有锁。"""
        return self._held

    def acquire(self) -> None:
        """非阻塞获取锁；已持有报E_R2_PROJECT_LOCK_HELD，冲突立即失败。"""
        if self._held:
            raise R2ProjectLockError("E_R2_PROJECT_LOCK_HELD")
        if not _IS_WINDOWS or _kernel32 is None:
            # 非Windows平台fail closed：不允许任何R2并行。
            raise R2ProjectLockError("E_R2_LOCK_PLATFORM_UNSUPPORTED")
        handle = _kernel32.CreateMutexW(None, False, self._lock_name)
        if not handle:
            # API调用失败：fail closed，不猜测成功。
            error_code = ctypes.get_last_error()  # type: ignore[union-attr]
            raise R2ProjectLockError(f"E_R2_LOCK_CREATE_FAILED:{error_code}")
        try:
            result = _kernel32.WaitForSingleObject(handle, 0)  # 0毫秒超时=非阻塞。
        except Exception:
            _kernel32.CloseHandle(handle)
            raise R2ProjectLockError("E_R2_LOCK_WAIT_FAILED")
        if result == _WAIT_TIMEOUT:
            # 锁已由其他进程持有：立即失败不排队。
            _kernel32.CloseHandle(handle)
            raise R2ProjectLockError("E_R2_PROJECT_LOCK_HELD")
        # WAIT_OBJECT_0(0x0)或WAIT_ABANDONED(0x80)都表示当前进程获取了锁；
        # WAIT_ABANDONED表示前持有进程异常退出，操作系统已恢复锁，当前进程可安全获取。
        if result not in (_WAIT_OBJECT_0, _WAIT_ABANDONED):
            _kernel32.CloseHandle(handle)
            raise R2ProjectLockError(f"E_R2_LOCK_WAIT_UNKNOWN:{result}")
        self._handle = handle
        self._held = True

    def release(self) -> bool:
        """释放锁并返回是否实际释放；Win32失败必须显式上报。"""
        if not self._held or self._handle is None:
            return False  # 未持有时明确拒绝，调用方可区分真实释放与重复调用。
        if not _IS_WINDOWS or _kernel32 is None:
            raise R2ProjectLockError("E_R2_LOCK_PLATFORM_UNSUPPORTED")
        try:
            released = bool(_kernel32.ReleaseMutex(self._handle))
        except Exception as exc:
            raise R2ProjectLockError("E_R2_LOCK_RELEASE_FAILED") from exc
        if not released:
            error_code = ctypes.get_last_error()  # type: ignore[union-attr]
            raise R2ProjectLockError(f"E_R2_LOCK_RELEASE_FAILED:{error_code}")
        try:
            closed = bool(_kernel32.CloseHandle(self._handle))
        except Exception as exc:
            self._held = False  # Mutex已释放，但句柄关闭失败必须显式暴露。
            raise R2ProjectLockError("E_R2_LOCK_CLOSE_FAILED") from exc
        if not closed:
            error_code = ctypes.get_last_error()  # type: ignore[union-attr]
            self._held = False
            raise R2ProjectLockError(f"E_R2_LOCK_CLOSE_FAILED:{error_code}")
        self._handle = None
        self._held = False
        return True

    def __enter__(self) -> "R2ProjectLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.release()

    def __del__(self) -> None:
        """析构时安全释放；防止异常路径泄漏Mutex句柄。"""
        try:
            self.release()
        except Exception:
            pass  # 析构异常不得传播；正式teardown仍会显式报告释放失败。


# ---------------------------------------------------------------------------
# 工厂函数：从已验证项目配置创建锁
# ---------------------------------------------------------------------------


def create_r2_project_lock(*, config: Mapping[str, Any]) -> R2ProjectLock:
    """从已验证v2.1项目配置创建R2锁。

    锁scope从配置的scope字段读取（project_group、product、environment），
    不接受测试文件或CLI提供的任意锁名。
    """
    scope = config.get("scope") if isinstance(config.get("scope"), Mapping) else None
    if scope is None:
        raise R2ProjectLockError("E_R2_LOCK_SCOPE_REQUIRED")
    project_group = scope.get("project_group")
    product = scope.get("product")
    environment = scope.get("environment")
    if not all(isinstance(v, str) and v for v in (project_group, product, environment)):
        raise R2ProjectLockError("E_R2_LOCK_SCOPE_INVALID")
    return R2ProjectLock(
        project_group=project_group,
        product=product,
        environment=environment,
    )


# ---------------------------------------------------------------------------
# xdist并行检测
# ---------------------------------------------------------------------------


def detect_xdist_parallel(*, config: Any = None, environ: Mapping[str, str] | None = None) -> bool:
    """检测pytest-xdist并行执行环境。

    检测PYTEST_XDIST_WORKER、PYTEST_XDIST_WORKER_COUNT环境变量
    以及pytest numprocesses选项。R2并行在锁前报E_R2_PARALLEL_FORBIDDEN。
    """
    env = environ if environ is not None else os.environ
    # 环境变量检测：xdist worker存在时一定并行。
    if env.get("PYTEST_XDIST_WORKER") or env.get("PYTEST_XDIST_WORKER_COUNT"):
        return True
    # pytest配置检测：numprocesses > 0表示xdist启用。
    if config is not None:
        try:
            numprocesses = config.getoption("--numprocesses", default=None)
            if isinstance(numprocesses, str):
                normalized = numprocesses.strip().lower()
                if normalized not in ("", "0", "none", "false"):
                    return True  # auto/logical等xdist模式也必须fail closed。
            elif numprocesses and int(numprocesses) > 0:
                return True
        except Exception:
            pass  # 选项不存在或不可读时不阻塞；环境变量已覆盖主要检测路径。
    return False
