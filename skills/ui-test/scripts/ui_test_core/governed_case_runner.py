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
        prepared = driver.prepare(page, guard.consume)
        for item in prepared.get("resolved_parameters", []):
            guard.record_derived(item["parameter_id"], item["value"], derived_from=item["derived_from"])
        snapshot = guard.seal_snapshot(str(snapshot_path))
        permit = guard.authorize_business_write()
        permit.consume()  # 在调用项目提交方法前消耗唯一许可，第二次调用必定失败。
        submitted = driver.submit_once(page, guard.consume)
        return {"prepared": prepared, "submitted": submitted, "snapshot_hash": snapshot["snapshot_hash"], "business_write_count": 1}
    finally:
        context.close()
