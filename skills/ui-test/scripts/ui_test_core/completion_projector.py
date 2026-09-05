"""六层Completion投影：unit、collection、release_verification、qualification、
pycharm_integration、human_r2必须全部passed且无P0/P1/unknown才能completed。

功能通过但治理证据不全投影为functional-accepted / repair-needed，
不得整体passed/completed。人工A/B R2未通过不得completed。
"""

from __future__ import annotations

from typing import Any, Mapping

from .pycharm_acceptance import validate_pycharm_acceptance_chain


# ---------------------------------------------------------------------------
# 错误码
# ---------------------------------------------------------------------------

class CompletionProjectionError(RuntimeError):
    """机器可读的投影失败；不包含私有值。"""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# 六个独立层级
# ---------------------------------------------------------------------------

REQUIRED_LAYERS = (
    "unit",
    "collection",
    "release_verification",
    "qualification",
    "pycharm_integration",
    "human_r2",
)

# 允许的层级状态值。
LAYER_STATUSES = ("passed", "failed", "blocked", "not_applicable", "unknown")

# 阻断completed的严重等级。
BLOCKING_SEVERITIES = ("P0", "P1", "unknown")
ALLOWED_SEVERITIES = ("P0", "P1", "P2", "P3", "clear", "unknown")


# ---------------------------------------------------------------------------
# CompletionProjector
# ---------------------------------------------------------------------------

class CompletionProjector:
    """分层Completion投影器：只接受六个独立层级。

    返回completed=false，直到六个层级均为passed且无P0/P1/unknown。
    功能通过但治理证据不全投影为functional-accepted / repair-needed，
    不得整体passed/completed。
    """

    __slots__ = ("_layers", "_findings", "_severity", "_run_result", "_acceptance_result", "_acceptance_chain")

    def __init__(
        self,
        *,
        layers: Mapping[str, str] | None = None,
        findings: list[Mapping[str, Any]] | None = None,
        severity: str = "unknown",
        run_result: Mapping[str, Any] | None = None,
        acceptance_result: Mapping[str, Any] | None = None,
        acceptance_chain: Mapping[str, Any] | None = None,
    ) -> None:
        """初始化投影器；接受六个独立层级状态。"""
        self._layers: dict[str, str] = {}
        if layers is not None:
            self._validate_layers(layers)
            self._layers = dict(layers)
        self._findings = findings or []
        self._run_result = dict(run_result or {})
        self._acceptance_result = dict(acceptance_result or {})
        self._acceptance_chain = dict(acceptance_chain or {})
        if severity not in ALLOWED_SEVERITIES:
            raise CompletionProjectionError("E_INVALID_COMPLETION_SEVERITY")
        self._severity = severity

        # 补全未提供的层级为unknown。
        for layer in REQUIRED_LAYERS:
            if layer not in self._layers:
                self._layers[layer] = "unknown"

    def _validate_layers(self, layers: Mapping[str, str]) -> None:
        """验证层级名称和状态值。"""
        for key, value in layers.items():
            if key not in REQUIRED_LAYERS:
                raise CompletionProjectionError(f"E_UNKNOWN_LAYER:{key}")
            if value not in LAYER_STATUSES:
                raise CompletionProjectionError(f"E_INVALID_LAYER_STATUS:{key}:{value}")

    def set_layer(self, layer: str, status: str) -> None:
        """设置单个层级状态。"""
        if layer not in REQUIRED_LAYERS:
            raise CompletionProjectionError(f"E_UNKNOWN_LAYER:{layer}")
        if status not in LAYER_STATUSES:
            raise CompletionProjectionError(f"E_INVALID_LAYER_STATUS:{layer}:{status}")
        self._layers[layer] = status

    def set_severity(self, severity: str) -> None:
        """设置当前严重等级。"""
        if severity not in ALLOWED_SEVERITIES:
            raise CompletionProjectionError("E_INVALID_COMPLETION_SEVERITY")
        self._severity = severity

    def add_finding(self, finding: Mapping[str, Any]) -> None:
        """添加一个发现项。"""
        self._findings.append(finding)

    # -------------------------------------------------------------------
    # 投影计算
    # -------------------------------------------------------------------

    def project(self) -> dict[str, Any]:
        """计算分层Completion投影。

        返回包含overall_status、layered_status和投影类型的对象。
        completed=false直到所有六个层级均为passed且无P0/P1/unknown。
        """
        layered = dict(self._layers)

        if self._run_result.get("schema_version") == "ui-test.run-result.v5":
            required_chain = {
                "run_result", "finalization_commit", "finalization_receipt", "pytest_session_result",
                "acceptance_result", "approval_record", "execution_context", "terminal", "process_evidence",
            }
            acceptance_ok = (
                self._acceptance_result.get("schema_version") == "ui-test.pycharm-acceptance-result.v1"
                and self._acceptance_result.get("overall_status", self._acceptance_result.get("verdict")) == "passed"
                and self._acceptance_result.get("observed_process_exit_code") == 0
                and self._acceptance_result.get("post_run_recovery") is False
                and set(self._acceptance_chain) == required_chain
                and self._acceptance_chain.get("run_result") == self._run_result
                and self._acceptance_chain.get("acceptance_result") == self._acceptance_result
                and not validate_pycharm_acceptance_chain(**self._acceptance_chain)
            )
            if not acceptance_ok:
                # V5禁止由业务passed自证PyCharm与human R2层，缺少外部exit验收时强制阻断。
                layered["pycharm_integration"] = "blocked"
                layered["human_r2"] = "blocked"

        # 检查是否有阻断性严重等级。
        has_blocking_severity = self._severity in BLOCKING_SEVERITIES

        # 检查是否有P0/P1/unknown发现。
        has_blocking_finding = any(
            not isinstance(finding, Mapping)
            or finding.get("severity", "unknown") not in ALLOWED_SEVERITIES
            or finding.get("severity", "unknown") in BLOCKING_SEVERITIES
            for finding in self._findings
        )

        # 所有六个层级是否全部passed。
        all_passed = all(layered[layer] == "passed" for layer in REQUIRED_LAYERS)

        # 是否有失败层级。
        any_failed = any(layered[layer] == "failed" for layer in REQUIRED_LAYERS)

        # 是否有阻断层级。
        any_blocked = any(layered[layer] == "blocked" for layer in REQUIRED_LAYERS)

        # 是否有unknown层级。
        any_unknown = any(layered[layer] == "unknown" for layer in REQUIRED_LAYERS)

        # 是否有not_applicable层级（功能可通过但治理证据不全）。
        any_not_applicable = any(layered[layer] == "not_applicable" for layer in REQUIRED_LAYERS)

        # 至少具备核心执行链证据才可称为functional-accepted；全unknown不得夸大。
        functional_evidence_passed = all(
            layered[layer] == "passed" for layer in ("unit", "collection", "pycharm_integration")
        )

        # 计算overall_status和投影类型。
        if all_passed and not has_blocking_severity and not has_blocking_finding:
            # 六层全部passed且无P0/P1/unknown：completed。
            overall_status = "passed"
            projection_type = "completed"
        elif any_failed:
            # 有failed层级：failed。
            overall_status = "failed"
            projection_type = "failed"
        elif any_blocked:
            # 有blocked层级：blocked。
            overall_status = "blocked"
            projection_type = "blocked"
        elif all_passed and (has_blocking_severity or has_blocking_finding):
            # 功能全部passed但有阻断性发现：repair-needed。
            overall_status = "degraded"
            projection_type = "repair-needed"
        elif (any_unknown or any_not_applicable) and functional_evidence_passed:
            # 有unknown或not_applicable层级：functional-accepted / repair-needed。
            # 功能可能通过但治理证据不全。
            overall_status = "degraded"
            projection_type = "functional-accepted"
        else:
            # 其他情况：degraded / repair-needed。
            overall_status = "degraded"
            projection_type = "repair-needed"

        return {
            "overall_status": overall_status,
            "layered_status": layered,
            "projection_type": projection_type,
            "completed": overall_status == "passed",
            "delivery_status": (
                "completed / 已完成"
                if overall_status == "passed"
                else "functional-accepted / repair-needed"
                if projection_type == "functional-accepted"
                else "repair-needed"
            ),
            "has_blocking_severity": has_blocking_severity,
            "has_blocking_finding": has_blocking_finding,
            "all_layers_passed": all_passed,
            "findings_count": len(self._findings),
        }

    # -------------------------------------------------------------------
    # 便捷方法
    # -------------------------------------------------------------------

    @property
    def is_completed(self) -> bool:
        """是否已completed。"""
        return self.project()["completed"]

    @property
    def projection_type(self) -> str:
        """当前投影类型。"""
        return self.project()["projection_type"]

    @property
    def overall_status(self) -> str:
        """当前overall_status。"""
        return self.project()["overall_status"]
