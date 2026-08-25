from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RISK_ALLOWLIST_V1 = {"R0", "R1"}
READONLY_ACTIONS = {
    "read",
    "navigate",
    "open_page_only",
    "open_panel_only",
    "open_modal_only",
    "open_drawer_only",
    "query",
    "filter",
    "view_detail",
}
WRITE_ACTIONS = {"submit", "save", "delete", "approve", "publish", "pay", "deploy", "create", "update", "remove"}
FAILURE_LAYERS = {
    "auth-expired",
    "auth-missing",
    "requirement-ambiguity",
    "registry",
    "schema",
    "safety-policy",
    "test-asset",
    "runtime",
}
FAILURE_TYPES = {
    "auth_ref_expired",
    "auth_ref_missing",
    "blocked_write_action",
    "checkpoint_stale",
    "assertion_mismatch",
    "invalid_schema",
    "missing_button",
    "missing_checkpoint",
    "network_error",
    "risk_not_allowed",
    "unknown",
}


class CheckpointRuntimeError(Exception):
    """Base runtime exception with a stable failure attribution layer."""

    def __init__(self, message: str, layer: str = "runtime"):
        super().__init__(message)
        self.layer = layer


@dataclass(frozen=True)
class RuntimeTarget:
    system_id: str
    module_id: str
    function_button_id: str | None = None
    environment_alias: str | None = None
    project_group: str = "public-pilot"
    product: str = "public-ui"
    function: str = "module-entry"
    checkpoint: str = "CP3-module-entry"
    risk_level: str = "R0"


@dataclass(frozen=True)
class RegistryPaths:
    root: Path
    registry_index: Path


@dataclass
class StepResult:
    checkpoint_id: str
    stage: str
    status: str
    evidence: list[str] = field(default_factory=list)
    failure_attribution: dict[str, Any] | None = None


@dataclass
class RuntimePlan:
    target: RuntimeTarget
    chain: list[dict[str, Any]]
    run_id: str
    correlation_id: str
    blocked: bool = False
    block_reason: str | None = None
    failure_attribution: dict[str, Any] | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
