"""Midscene-first adapter contract; execution is injected and page-scoped."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable


class MidsceneAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterContract:
    midscene_version: str = "1.10.2"
    step_timeout_ms: int = 45_000
    total_timeout_ms: int = 180_000
    supports_existing_page: bool = True
    supports_cancel: bool = True
    supports_progress: bool = True
    supports_report: bool = True


class MidsceneAdapter:
    def __init__(self, contract: AdapterContract | None = None):
        self.contract = contract or AdapterContract()
        self._calls = 0

    @property
    def calls(self) -> int:
        return self._calls

    def preflight(self, installed_version: str, page_verified: bool, context: dict[str, Any]) -> dict[str, Any]:
        missing = []
        if installed_version != self.contract.midscene_version:
            missing.append("version-drift")
        if not page_verified:
            missing.append("unverified-page")
        if not context or context.get("handoff_status") != "ready":
            missing.append("module-ready-context")
        if not all((self.contract.supports_existing_page, self.contract.supports_cancel, self.contract.supports_progress, self.contract.supports_report)):
            missing.append("adapter-capability")
        return {"ok": not missing, "code": "OK" if not missing else "E_PREFLIGHT_FAILED", "failed_checks": missing}

    def explore(self, *, page: Any, context: dict[str, Any], intent: str, executor: Callable[..., dict[str, Any]], progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        if not context or context.get("handoff_status") != "ready":
            raise MidsceneAdapterError("E_HANDOFF_FAILED")
        self._calls += 1
        started = time.monotonic()
        if progress:
            progress({"event": "started", "attempt": self._calls, "intent_digest": hashlib.sha256(intent.encode()).hexdigest()[:16]})
        result = executor(page=page, intent=intent, timeout_ms=self.contract.step_timeout_ms, cancel_supported=self.contract.supports_cancel)
        elapsed = int((time.monotonic() - started) * 1000)
        result = dict(result or {})
        result.update({"executor": "midscene", "duration_ms": elapsed, "attempt": self._calls, "prompt_digest": hashlib.sha256(intent.encode()).hexdigest()})
        if progress:
            progress({"event": "finished", "status": result.get("status", "unknown"), "duration_ms": elapsed})
        return result
