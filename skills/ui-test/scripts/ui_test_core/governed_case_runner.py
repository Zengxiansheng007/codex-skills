"""Order BrowserContext creation and the first business write behind parameter gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from .execution_parameter_guard import ExecutionParameterGuard


class GovernedScenarioDriver(Protocol):
    def prepare(self, page: Any, consume: Callable[[str], Any]) -> dict[str, Any]: ...

    def submit_once(self, page: Any, consume: Callable[[str], Any]) -> dict[str, Any]: ...


def execute_governed_case(
    *,
    guard: ExecutionParameterGuard,
    context_factory: Callable[[], Any],
    driver: GovernedScenarioDriver,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    """Run the fixed gate order without granting R2 or weakening project assertions."""
    guard.start()  # 启动哈希门禁必须发生在 BrowserContext 之前。
    context = context_factory()
    try:
        page = context.new_page()
        try:
            prepared = driver.prepare(page, guard.consume)
            for item in prepared.get("resolved_parameters", []):
                guard.record_derived(item["parameter_id"], item["value"], derived_from=item["derived_from"])
            snapshot = guard.seal_snapshot(str(snapshot_path))
            permit = guard.authorize_business_write()
            permit.consume()  # 在调用项目提交方法前消耗唯一许可，第二次调用必定失败。
            submitted = driver.submit_once(page, guard.consume)
            return {"prepared": prepared, "submitted": submitted, "snapshot_hash": snapshot["snapshot_hash"], "business_write_count": 1}
        except Exception:
            capture = getattr(driver, "capture_failure", None)
            if callable(capture):
                try:
                    capture(page)  # 失败截图是只读证据；截图异常不得覆盖原始失败。
                except Exception:
                    pass
            raise
    finally:
        context.close()


def execute_pre_submit_case(
    *,
    guard: ExecutionParameterGuard,
    context_factory: Callable[[], Any],
    driver: GovernedScenarioDriver,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    """执行到提交前并封存证据，不申请或消费任何业务写许可。"""
    guard.start()  # 提交前验证仍需在 BrowserContext 创建前通过参数哈希门禁。
    context = context_factory()
    try:
        page = context.new_page()
        try:
            prepared = driver.prepare(page, guard.consume)
            for item in prepared.get("resolved_parameters", []):
                guard.record_derived(item["parameter_id"], item["value"], derived_from=item["derived_from"])
            snapshot = guard.seal_snapshot(str(snapshot_path))
            return {
                "prepared": prepared,
                "snapshot_hash": snapshot["snapshot_hash"],
                "submit_count": 0,
                "write_state": "not_attempted",
                "sequence_allocated": False,
            }
        except Exception:
            capture = getattr(driver, "capture_failure", None)
            if callable(capture):
                try:
                    capture(page)  # 在关闭 fresh context 前保存失败现场。
                except Exception:
                    pass
            raise
    finally:
        context.close()
