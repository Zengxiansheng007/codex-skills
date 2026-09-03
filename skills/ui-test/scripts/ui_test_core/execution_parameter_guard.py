"""Record parameter drift as an unfinished product-level repair while blocking execution."""

from __future__ import annotations

from typing import Any

from .execution_data_session import ExecutionDataError, ExecutionDataSession
from .failure_repair_store import FailureRepairEventStore, make_event


class ExecutionParameterGuard:
    """Connect the frozen session to the unified failure/repair interface."""

    def __init__(self, session: ExecutionDataSession, store: FailureRepairEventStore, *, source_file_ref: str) -> None:
        self.session = session
        self.store = store
        self.source_file_ref = source_file_ref
        self._recorded_codes: set[str] = set()

    def _record(self, code: str) -> None:
        if code in self._recorded_codes:
            return
        self._recorded_codes.add(code)
        event = make_event(
            event_type="sync-required",
            idempotency_key=f"{self.session.run_id}:{code}",
            product_id=self.store.product_id,
            case_id=self.session.parameter_manifest["case_id"],
            branch_id=self.session.parameter_manifest["branch_id"],
            category="parameter-drift",
            summary=code,
            source_files=[self.source_file_ref],
        )
        # 日志失败同样必须阻断，不允许吞掉诊断写入异常后继续业务流程。
        self.store.append(event)

    def _invoke(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return operation(*args, **kwargs)
        except ExecutionDataError as exc:
            code = str(exc).split(":", 1)[0]
            self._record(code)
            raise

    def start(self) -> None:
        self._invoke(self.session.start)

    def consume(self, parameter_id: str) -> Any:
        return self._invoke(self.session.consume, parameter_id)

    def record_derived(self, parameter_id: str, value: Any, *, derived_from: list[str]) -> None:
        self._invoke(self.session.record_derived, parameter_id, value, derived_from=derived_from)

    def seal_snapshot(self, path: str) -> dict[str, Any]:
        return self._invoke(self.session.seal_snapshot, path)

    def authorize_business_write(self):
        return self._invoke(self.session.authorize_business_write)
