"""通用 pytest 执行上下文插件：注册参数、分类来源、绑定 node、生成 ExecutionContextV2。

本插件是执行上下文的唯一控制层。项目 runtime 通过 ``ui_test_execution_context`` fixture
消费已验证上下文，不得自行识别 PyCharm 来源、生成 Run ID 或授予 R2 批准。
ST-005：为R2 item在fixture前获取跨进程非阻塞串行锁，在teardown/finalizer释放；
R0/R1不获取锁；R3报E_R3_BLOCKED；xdist并行在锁前报E_R2_PARALLEL_FORBIDDEN。
ST-006：collection阶段身份/配置门禁错误写diagnostics且不创建attempt；
R2锁成功后、R0/R1 setup开始时创建attempt-start；
记录setup/call/teardown阶段事件并在正常pytest生命周期末生成唯一terminal。
新增execution evidence root hookspec。
"""

from __future__ import annotations

import hashlib  # 生成不暴露本机路径的来源与配置摘要。
import json  # 读取ExecutionContextV2 Schema。
import re  # 校验Run ID和摘要格式。
import uuid  # 为每个pytest宿主进程生成唯一session identity。
from dataclasses import asdict, dataclass  # 构建并验证只读上下文对象。
from datetime import UTC, datetime  # 生成SessionResult时间戳。
from pathlib import Path  # 读取项目配置文件。
from typing import Any, Callable, Mapping  # 声明稳定的输入结构。

import pytest  # pytest 插件入口与 hookspec 依赖。
from jsonschema import Draft202012Validator  # 在上下文进入fixture前执行正式Schema校验。

from .attempt_recovery import AttemptRecovery
from .case_contracts import canonical_hash, validate_document
from .execution_attempt_store import (
    ExecutionAttemptStore,
    ExecutionAttemptStoreError,
    derive_attempt_directory_name,
)
from .pycharm_runtime import resolve_pycharm_run_context
from .finalization_transaction import FinalizationTransaction, FinalizationTransactionError
from .project_config import ProjectConfigError, load_project_config
from .path_utils import io_path
from .r2_project_lock import (
    R2ProjectLock,
    R2ProjectLockError,
    create_r2_project_lock,
    detect_xdist_parallel,
)


SKILL_ROOT = Path(__file__).resolve().parents[2]  # Schema从当前候选Skill读取，不接受调用方任意根目录。
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# 上下文对象
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ExecutionContextV3:
    """ExecutionContextV3 的不可变运行时表示。"""

    schema_version: str  # 固定为 ui-test.execution-context.v3
    session_id: str  # 当前pytest宿主进程唯一会话ID
    execution_origin: str  # pycharm | codex-cli | cli | ci | unknown
    origin_evidence: dict[str, Any]  # 来源证据摘要，不含绝对路径
    run_id: str  # 所有正式节点必须在BrowserContext前获得唯一Run ID
    node_id: str  # pytest nodeid
    case_id: str  # 稳定 Source Case ID
    branch_id: str  # 稳定 Source Case branch ID
    risk_level: str  # r0|r1|r2|r3
    environment: str  # 已通过v2.1校验的项目环境
    approved: bool  # 当前节点是否获得候选批准
    approval_source: str  # explicit-cli | pycharm-project-policy | not-approved
    stable_runner_digest: str  # 当前stable test item的内容摘要
    active_build_fingerprint: str  # 项目resolver返回的active build摘要
    active_attachment_digest: str  # 必须与stable runner内容摘要一致
    project_config_digest: str  # 正式loader计算的配置摘要
    finalization_policy_digest: str  # 事务契约策略摘要
    attempt_ref: str  # 与append-only attempt目录一致的相对引用
    finalization_contract: str  # transaction-v1
    run_result_contract: str  # v5
    session_result_contract: str  # v1
    acceptance_contract: str  # external-exit-v1
    config_summary: dict[str, Any]  # 已验证v2.1策略快照


#: 每个 item 存放其 ExecutionContextV2 的 stash key。
EXECUTION_CONTEXT_KEY: pytest.StashKey[_ExecutionContextV3] = pytest.StashKey()

#: marker 校验失败时存放错误码的 stash key，供 pytest_runtest_setup 使用。
_MARKER_ERROR_KEY: pytest.StashKey[str] = pytest.StashKey()

#: R2锁对象存放的 stash key；None表示非R2 item或锁未获取。
_R2_LOCK_KEY: pytest.StashKey[R2ProjectLock | None] = pytest.StashKey()

#: ST-006：每个 item 的 ExecutionAttemptStore 存放的 stash key。
_ATTEMPT_STORE_KEY: pytest.StashKey[Any] = pytest.StashKey()

#: ST-006：每个 item 的 attempt 已创建标志。
_ATTEMPT_STARTED_KEY: pytest.StashKey[bool] = pytest.StashKey()

#: ST-006：保存setup/call/teardown三阶段TestReport，用于唯一terminal判定。
_PHASE_REPORTS_KEY: pytest.StashKey[dict[str, pytest.TestReport]] = pytest.StashKey()

#: pytest进程级session与节点终态投影；仅用于sessionfinish写入只读结果。
_SESSION_ID_KEY: pytest.StashKey[str] = pytest.StashKey()
_SESSION_NODE_RESULTS_KEY: pytest.StashKey[list[dict[str, Any]]] = pytest.StashKey()
_SESSION_EVIDENCE_ROOT_KEY: pytest.StashKey[str] = pytest.StashKey()


# ---------------------------------------------------------------------------
# 受控 hookspec：根 conftest 提供项目配置与身份 resolver
# ---------------------------------------------------------------------------


def pytest_addhooks(pluginmanager: pytest.PytestPluginManager) -> None:
    """注册本插件提供的 hookspec，让根 conftest 实现 project_config 与 identity resolver。"""
    pluginmanager.add_hookspecs(_UiTestExecutionHooks)


class _UiTestExecutionHooks:
    """受控接口：根 conftest 通过实现这些 hook 提供项目配置与身份 resolver。"""

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_project_config_path(self) -> str | None:
        """返回当前项目的 v2.1 配置路径；未提供时插件不构建 config_summary。"""
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_stable_runner_root(self) -> str | None:
        """返回当前项目的regression-runners根目录。"""
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_active_identity_resolver(
        self,
    ) -> Callable[[Mapping[str, Any]], dict[str, Any]] | None:
        """返回 active build/attachment 摘要 resolver。

        resolver 签名：resolver(context_seed: Mapping) -> {"active_build_fingerprint": str, "active_attachment_digest": str}
        resolver必须把当前stable runner摘要与active attachment绑定，插件负责比较。
        """
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_execution_evidence_root(self) -> str | None:
        """返回execution evidence根目录；ST-006用于创建attempt文件。

        未提供时插件不创建attempt文件，仅收集diagnostics。
        """
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_finalize_run_result_v4(
        self,
        run_id: str,
        node_id: str,
        attempt_store: Any,
    ) -> dict[str, Any] | None:
        """ST-008：terminal后项目finalizer hookspec。

        只有create_terminal和attempt最终hash成功后才调用；
        finalizer失败必须使teardown失败。
        项目finalizer验证context/attempt/approval/pending/build/node一致，
        读取activation readiness，生成不可变run-result.json和evidence-index.json。
        """
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_finalization_target_v1(
        self,
        run_id: str,
        node_id: str,
        attempt_store: Any,
    ) -> dict[str, Any] | None:
        """返回受控run_root与逻辑引用；不得在此构建或发布结果。"""
        return None

    @pytest.hookspec(firstresult=True)
    def pytest_ui_test_build_finalization_candidate_v1(
        self,
        run_id: str,
        node_id: str,
        transaction_id: str,
        pre_terminal_events_hash: str,
        pytest_phase_status: Mapping[str, str],
        attempt_store: Any,
    ) -> dict[str, Any] | None:
        """项目适配器只返回RunResultV5/evidence-index候选，不得自行提交文件。"""
        return None


# ---------------------------------------------------------------------------
# CLI 参数注册
# ---------------------------------------------------------------------------

_OPTION_RUN_ID = "--ui-run-id"
_OPTION_R2_APPROVED = "--ui-r2-approved"
_OPTION_EXECUTION_ORIGIN = "--ui-execution-origin"


def pytest_addoption(parser: pytest.Parser) -> None:
    """注册 ui-run-id、ui-r2-approved 和 ui-execution-origin 三个 CLI 参数。

    与现有项目参数保持兼容：重复注册必须可诊断（pytest 自身处理 OptionGroup 冲突），
    本插件使用唯一前缀 ``--ui-`` 避免与项目私有参数碰撞。
    """
    group = parser.getgroup("ui-test-execution", "UI-Test Execution Context")
    group.addoption(
        _OPTION_RUN_ID,
        action="store",
        default=None,
        help="显式 Run ID；CLI/CI/Codex 必须提供，PyCharm 可自动生成。",
    )
    group.addoption(
        _OPTION_R2_APPROVED,
        action="store_true",
        default=False,
        help="显式 R2 批准标志；非 PyCharm 入口必须显式提供。",
    )
    group.addoption(
        _OPTION_EXECUTION_ORIGIN,
        action="store",
        default=None,
        choices=["codex-cli"],
        help="仅供Codex受控入口声明来源；PyCharm必须由真实runner路径识别。",
    )


def pytest_configure(config: pytest.Config) -> None:
    """注册正式marker，避免项目依赖外部pytest.ini才能解释测试身份。"""

    config.stash[_SESSION_ID_KEY] = "SESSION-" + uuid.uuid4().hex.upper()
    config.stash[_SESSION_NODE_RESULTS_KEY] = []

    markers = {
        "ui_test": "正式UI-Test节点",
        "case_id(value)": "稳定Source Case标识",
        "branch_id(value)": "稳定branch标识",
        "r0": "只读公开风险",
        "r1": "只读认证风险",
        "r2": "测试环境可见UI单写风险",
        "r3": "禁止执行的高风险",
    }
    for marker, description in markers.items():
        config.addinivalue_line("markers", f"{marker}: {description}")  # 插件加载即建立同源marker契约。


# ---------------------------------------------------------------------------
# Marker 解析与校验
# ---------------------------------------------------------------------------

_RISK_MARKERS = ("r0", "r1", "r2", "r3")  # 风险等级 marker，每个 ui_test item 必须有且仅有一个。
_RISK_LEVELS = {
    "r0": "r0-read-only",
    "r1": "r1-read-only-authenticated",
    "r2": "r2-ui-write-test",
    "r3": "r3-high-impact",
}


class _MarkerError(Exception):
    """ui_test marker 校验失败，在 BrowserContext 前失败。"""

    def __init__(self, node_id: str, code: str) -> None:
        self.node_id = node_id
        self.code = code
        super().__init__(f"{code}:{node_id}")


def _parse_ui_test_markers(item: pytest.Item) -> dict[str, Any]:
    """从 item 的 marker 中提取 case_id、branch_id 和 risk_level。

    要求唯一风险与身份；缺失/冲突在 BrowserContext 前失败。
    """
    node_id = item.nodeid
    marker = item.get_closest_marker("ui_test")
    if marker is None:
        # 非 ui_test item 不被影响，返回空标识。
        return {"is_ui_test": False}

    # case_id 必须存在且唯一。
    case_markers = list(item.iter_markers("case_id"))
    if len(case_markers) == 0:
        raise _MarkerError(node_id, "E_UI_TEST_CASE_ID_MISSING")
    if len(case_markers) > 1:
        raise _MarkerError(node_id, "E_UI_TEST_CASE_ID_DUPLICATE")
    case_id = case_markers[0].args[0]
    if not isinstance(case_id, str) or not case_id:
        raise _MarkerError(node_id, "E_UI_TEST_CASE_ID_INVALID")

    # branch_id 必须存在且唯一。
    branch_markers = list(item.iter_markers("branch_id"))
    if len(branch_markers) == 0:
        raise _MarkerError(node_id, "E_UI_TEST_BRANCH_ID_MISSING")
    if len(branch_markers) > 1:
        raise _MarkerError(node_id, "E_UI_TEST_BRANCH_ID_DUPLICATE")
    branch_id = branch_markers[0].args[0]
    if not isinstance(branch_id, str) or not branch_id:
        raise _MarkerError(node_id, "E_UI_TEST_BRANCH_ID_INVALID")

    # 风险 marker 必须有且仅有一个。
    found_risks = [name for name in _RISK_MARKERS if list(item.iter_markers(name))]
    if len(found_risks) == 0:
        raise _MarkerError(node_id, "E_UI_TEST_RISK_MARKER_MISSING")
    if len(found_risks) > 1:
        raise _MarkerError(node_id, "E_UI_TEST_RISK_MARKER_CONFLICT")
    risk_level = _RISK_LEVELS[found_risks[0]]

    return {
        "is_ui_test": True,
        "case_id": case_id,
        "branch_id": branch_id,
        "risk_level": risk_level,
    }


# ---------------------------------------------------------------------------
# 上下文构建辅助
# ---------------------------------------------------------------------------

def _sha256_text(value: str) -> str:
    """返回带算法前缀的稳定摘要。"""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _build_config_summary(config: Mapping[str, Any]) -> dict[str, Any]:
    """从 v2.2 项目配置提取 ExecutionContextV3 的契约快照。"""
    policy = config.get("pycharm_manual_execution") if isinstance(config.get("pycharm_manual_execution"), Mapping) else {}
    return {
        "schema_version": config["schema_version"],
        "contract_version": policy["contract_version"],
        "origin_detection": policy["origin_detection"],
        "entry_scope": policy["entry_scope"],
        "r2_authorization": policy["r2_authorization"],
        "run_scope": policy["run_scope"],
        "r2_parallelism": policy["r2_parallelism"],
        "finalization_contract": policy["finalization_contract"],
        "run_result_contract": policy["run_result_contract"],
        "session_result_contract": policy["session_result_contract"],
        "acceptance_contract": policy["acceptance_contract"],
    }


def _build_execution_context(
    *,
    item: pytest.Item,
    marker_info: dict[str, Any],
    config: pytest.Config,
    hooks: Any,  # 实际为 _HookRelay，类型由 pytest 内部管理
    pycharm_config: Mapping[str, Any] | None,
) -> _ExecutionContextV3:
    """为单个 ui_test item 构建 ExecutionContextV3 并存入 item.stash。

    调用 ST-002 resolver 计算来源与 Run ID，调用项目提供的 active identity
    resolver 补齐 active 摘要。本 Story 不获取 R2 锁、不创建 attempt 文件。
    """
    node_id = item.nodeid
    case_id = marker_info["case_id"]
    branch_id = marker_info["branch_id"]
    risk_level = marker_info["risk_level"]

    # CLI 参数
    requested_run_id = config.getoption(_OPTION_RUN_ID, None) or None
    explicitly_approved = bool(config.getoption(_OPTION_R2_APPROVED, False))
    declared_origin = config.getoption(_OPTION_EXECUTION_ORIGIN, None) or None

    if pycharm_config is None:
        raise _MarkerError(node_id, "E_UI_TEST_PROJECT_CONFIG_REQUIRED")
    config_summary = _build_config_summary(pycharm_config)  # 正式loader已完成v2.1与敏感字段校验。
    project_config_digest = pycharm_config.get("config_fingerprint")
    if not isinstance(project_config_digest, str) or not _SHA256.fullmatch(project_config_digest):
        raise _MarkerError(node_id, "E_UI_TEST_PROJECT_CONFIG_DIGEST_INVALID")

    # 调用 ST-002 resolver 计算来源、Run ID 和候选批准。
    resolver_result = resolve_pycharm_run_context(
        config=pycharm_config or {},
        case_id=case_id,
        branch_id=branch_id,
        node_id=node_id,
        risk_level=risk_level,
        requested_run_id=requested_run_id,
        explicitly_approved=explicitly_approved,
        declared_origin=declared_origin,
    )

    if not isinstance(resolver_result.get("run_id"), str) or not resolver_result["run_id"]:
        raise _MarkerError(node_id, "E_FORMAL_RUN_ID_REQUIRED")  # 正式上下文不得携带Schema不允许的空Run ID。

    # stable runner是当前test item本身，必须位于项目声明的regression-runners根目录。
    stable_runner_root = hooks.pytest_ui_test_stable_runner_root()
    if not isinstance(stable_runner_root, str) or not stable_runner_root:
        raise _MarkerError(node_id, "E_UI_TEST_STABLE_RUNNER_ROOT_REQUIRED")
    try:
        runner_root = Path(stable_runner_root).resolve(strict=True)
        runner_path = Path(str(item.path)).resolve(strict=True)
        relative_runner = runner_path.relative_to(runner_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise _MarkerError(node_id, "E_PYCHARM_ENTRY_NOT_STABLE_ACTIVE") from exc
    if len(relative_runner.parts) != 1 or runner_path.suffix.lower() != ".py":
        raise _MarkerError(node_id, "E_PYCHARM_ENTRY_NOT_STABLE_ACTIVE")
    stable_runner_digest = _sha256_bytes(runner_path.read_bytes())

    # active identity 摘要：由项目提供的 resolver 补齐。
    active_resolver = hooks.pytest_ui_test_active_identity_resolver()
    if active_resolver is None:
        raise _MarkerError(node_id, "E_UI_TEST_ACTIVE_IDENTITY_RESOLVER_REQUIRED")
    seed = {
        "case_id": case_id,
        "branch_id": branch_id,
        "risk_level": risk_level,
        "environment": resolver_result.get("environment"),
        "node_id": node_id,
        "stable_runner_digest": stable_runner_digest,
        # ST-008：seed加入只读qualification_mode和candidate_build（若项目参数不存在则安全为空）。
        "qualification_mode": bool(config.getoption("--ui-pre-submit-only", False)),
        "candidate_build": config.getoption("--ui-candidate-build", None),
    }
    try:
        active_result = active_resolver(seed)
    except Exception as exc:
        raise _MarkerError(node_id, "E_UI_TEST_ACTIVE_IDENTITY_RESOLUTION_FAILED") from exc
    active_build_fingerprint = active_result.get("active_build_fingerprint") if isinstance(active_result, Mapping) else None
    active_attachment_digest = active_result.get("active_attachment_digest") if isinstance(active_result, Mapping) else None
    if not isinstance(active_build_fingerprint, str) or not _SHA256.fullmatch(active_build_fingerprint):
        raise _MarkerError(node_id, "E_UI_TEST_ACTIVE_IDENTITY_INVALID")
    if active_attachment_digest != stable_runner_digest:
        raise _MarkerError(node_id, "E_PYCHARM_ENTRY_NOT_STABLE_ACTIVE")

    session_id = config.stash.get(_SESSION_ID_KEY, "")
    contract_material = {
        key: config_summary[key]
        for key in (
            "schema_version", "contract_version", "finalization_contract",
            "run_result_contract", "session_result_contract", "acceptance_contract",
        )
    }
    context = _ExecutionContextV3(
        schema_version="ui-test.execution-context.v3",
        session_id=session_id,
        execution_origin=resolver_result["execution_origin"],
        origin_evidence=resolver_result["origin_evidence"],
        run_id=resolver_result["run_id"],
        node_id=node_id,
        case_id=case_id,
        branch_id=branch_id,
        risk_level=risk_level,
        environment=resolver_result.get("environment"),
        approved=resolver_result["approved"],
        approval_source=resolver_result["approval_source"],
        stable_runner_digest=stable_runner_digest,
        active_build_fingerprint=active_build_fingerprint,
        active_attachment_digest=active_attachment_digest,
        project_config_digest=project_config_digest,
        finalization_policy_digest=_sha256_text(
            json.dumps(contract_material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ),
        attempt_ref="attempts/" + derive_attempt_directory_name(
            run_id=resolver_result["run_id"], node_id=node_id
        ),  # 上下文引用必须与实际attempt目录完全一致。
        finalization_contract=config_summary["finalization_contract"],
        run_result_contract=config_summary["run_result_contract"],
        session_result_contract=config_summary["session_result_contract"],
        acceptance_contract=config_summary["acceptance_contract"],
        config_summary=config_summary,
    )
    context_schema = json.loads((SKILL_ROOT / "schemas" / "execution-context-v3.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(context_schema).iter_errors(asdict(context)), key=lambda error: list(error.absolute_path))
    if errors:
        raise _MarkerError(node_id, "E_UI_TEST_EXECUTION_CONTEXT_SCHEMA_INVALID")
    item.stash[EXECUTION_CONTEXT_KEY] = context
    return context


# ---------------------------------------------------------------------------
# pytest hooks
# ---------------------------------------------------------------------------


def _record_gate_diagnostic(
    *, store: ExecutionAttemptStore | None, item: pytest.Item, code: str, detail: str
) -> str:
    """记录早期拒绝；存储不可用时返回更强的fail-closed错误码。"""
    if store is None:
        return "E_UI_TEST_EVIDENCE_STORE_REQUIRED"
    try:
        store.append_diagnostics(run_id="unknown", node_id=item.nodeid, code=code, detail=detail)
    except ExecutionAttemptStoreError:
        return "E_UI_TEST_DIAGNOSTICS_WRITE_FAILED"
    return code


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """对每个 ui_test item 解析 marker 并构建 ExecutionContextV2 存入 item.stash。

    非 ui_test 普通 pytest 用例不受影响。marker 缺失/冲突不在此处 fail，
    而是存入 _MARKER_ERROR_KEY，由 pytest_runtest_setup 在 item 执行前失败。

    ST-005：R3 item 存入 E_R3_BLOCKED 错误码；xdist并行检测在锁前执行。
    ST-006：collection阶段身份/配置/门禁错误写diagnostics且不创建attempt。
    """
    hookrelay = session.config.hook
    project_config_path = hookrelay.pytest_ui_test_project_config_path()
    pycharm_config: Mapping[str, Any] | None = None
    config_error: str | None = None
    if isinstance(project_config_path, str) and project_config_path:
        try:
            pycharm_config = load_project_config(project_config_path, purpose="execute")  # 正式执行必须通过v2.1 loader。
        except ProjectConfigError as exc:
            config_error = str(exc).split(":", 1)[0]
    else:
        config_error = "E_UI_TEST_PROJECT_CONFIG_REQUIRED"

    # ST-005：检测xdist并行环境；R2并行在锁前报E_R2_PARALLEL_FORBIDDEN。
    _xdist_parallel = detect_xdist_parallel(config=config)

    # ST-006：获取execution evidence root，用于写入diagnostics。
    evidence_root = hookrelay.pytest_ui_test_execution_evidence_root()
    attempt_store: ExecutionAttemptStore | None = None
    if isinstance(evidence_root, str) and evidence_root:
        config.stash[_SESSION_EVIDENCE_ROOT_KEY] = evidence_root
        try:
            attempt_store = ExecutionAttemptStore(evidence_root=evidence_root)
            def _probe_finalization(attempt_info: Mapping[str, Any]) -> str | None:
                run_id = attempt_info.get("run_id")
                node_id = attempt_info.get("node_id")
                if not isinstance(run_id, str) or not run_id or not isinstance(node_id, str) or not node_id:
                    return None
                target = hookrelay.pytest_ui_test_finalization_target_v1(
                    run_id=run_id, node_id=node_id, attempt_store=attempt_store
                )
                if not isinstance(target, Mapping) or not isinstance(target.get("run_root"), str):
                    return None
                transaction = FinalizationTransaction(target["run_root"])
                commit = transaction.store.read_commit()
                receipt = transaction.store.read_receipt()
                if commit is not None and receipt is not None:
                    return "receipt_without_terminal"
                if commit is not None:
                    return "commit_without_receipt"
                if receipt is not None:
                    return "finalizing"
                return None

            AttemptRecovery(store=attempt_store).scan_and_recover(
                finalization_probe=_probe_finalization
            )  # 读取真实commit/receipt分类，但绝不追认passed。
        except ExecutionAttemptStoreError:
            attempt_store = None  # ui_test item稍后以稳定错误码fail closed。

    for item in items:
        try:
            marker_info = _parse_ui_test_markers(item)
        except _MarkerError as exc:
            # marker 缺失/冲突：存入错误码，由 runtest_setup 在 BrowserContext 前失败。
            item.stash[_MARKER_ERROR_KEY] = _record_gate_diagnostic(
                store=attempt_store, item=item, code=exc.code, detail="marker-gate"
            )
            continue
        if not marker_info.get("is_ui_test"):
            continue  # 非 ui_test item 不被影响。
        if attempt_store is None:
            item.stash[_MARKER_ERROR_KEY] = "E_UI_TEST_EVIDENCE_STORE_REQUIRED"
            continue  # 正式节点没有两级留痕根时不得静默执行。
        # ST-005：R3 item 在BrowserContext前报E_R3_BLOCKED。
        if marker_info["risk_level"] == "r3-high-impact":
            item.stash[_MARKER_ERROR_KEY] = _record_gate_diagnostic(
                store=attempt_store, item=item, code="E_R3_BLOCKED", detail="r3-gate"
            )
            continue
        # ST-005：R2并行在锁前报E_R2_PARALLEL_FORBIDDEN。
        if marker_info["risk_level"] == "r2-ui-write-test" and _xdist_parallel:
            item.stash[_MARKER_ERROR_KEY] = _record_gate_diagnostic(
                store=attempt_store, item=item, code="E_R2_PARALLEL_FORBIDDEN", detail="xdist-gate"
            )
            continue
        if config_error is not None:
            item.stash[_MARKER_ERROR_KEY] = _record_gate_diagnostic(
                store=attempt_store, item=item, code=config_error, detail="config-gate"
            )
            continue
        try:
            context = _build_execution_context(
                item=item,
                marker_info=marker_info,
                config=config,
                hooks=hookrelay,
                pycharm_config=pycharm_config,
            )
            # ST-006：存入attempt_store供setup使用。
            if attempt_store is not None:
                item.stash[_ATTEMPT_STORE_KEY] = attempt_store
        except _MarkerError as exc:
            item.stash[_MARKER_ERROR_KEY] = _record_gate_diagnostic(
                store=attempt_store, item=item, code=exc.code, detail="context-gate"
            )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """在 item 执行前检查 marker 错误码，确保在 BrowserContext 前失败。

    ST-005：R2 item 在fixture前获取跨进程非阻塞串行锁并存入 item stash。
    R0/R1不获取锁；R3/xdist错误码已由 collection 阶段存入。
    ST-006：R2锁成功后、R0/R1 setup开始时创建attempt-start；
    记录setup阶段事件。
    """
    error_code = item.stash.get(_MARKER_ERROR_KEY, None)
    if error_code is not None:
        pytest.fail(error_code, pytrace=False)

    # ST-005：R2 item 在fixture前获取跨进程非阻塞串行锁。
    context = item.stash.get(EXECUTION_CONTEXT_KEY, None)
    if context is not None and context.risk_level == "r2-ui-write-test":
        # 锁scope从已验证项目配置读取，不接受测试文件或CLI提供任意锁名。
        hookrelay = item.config.hook
        project_config_path = hookrelay.pytest_ui_test_project_config_path()
        if isinstance(project_config_path, str) and project_config_path:
            try:
                pycharm_config = load_project_config(project_config_path, purpose="execute")
            except ProjectConfigError:
                pytest.fail("E_R2_LOCK_CONFIG_REQUIRED", pytrace=False)
        else:
            pytest.fail("E_R2_LOCK_CONFIG_REQUIRED", pytrace=False)
        try:
            lock = create_r2_project_lock(config=pycharm_config)
            lock.acquire()  # 非阻塞获取；冲突立即失败。
            item.stash[_R2_LOCK_KEY] = lock
        except R2ProjectLockError as exc:
            pytest.fail(exc.code, pytrace=False)

    # ST-006：R2锁成功后、R0/R1 setup开始时创建attempt-start。
    attempt_store = item.stash.get(_ATTEMPT_STORE_KEY, None)
    if attempt_store is not None and context is not None:
        try:
            attempt_store.create_attempt_start(
                run_id=context.run_id,
                node_id=context.node_id,
                case_id=context.case_id,
                branch_id=context.branch_id,
                risk_level=context.risk_level,
                execution_origin=context.execution_origin,
                approval_source=context.approval_source,
                stable_runner_digest=context.stable_runner_digest,
                project_config_digest=context.project_config_digest,
                schema_version="ui-test.execution-attempt.v2",
                session_id=context.session_id,
                finalization_mode=(
                    "not_applicable_qualification"
                    if bool(item.config.getoption("--ui-pre-submit-only", False))
                    else "transaction-v1"
                    if context.risk_level == "r2-ui-write-test"
                    else "not_applicable_read_only"
                ),
            )
            item.stash[_ATTEMPT_STARTED_KEY] = True
            # ST-008：plugin在attempt-start之后写context，任何失败使pytest失败。
            attempt_store.write_execution_context(
                run_id=context.run_id,
                node_id=context.node_id,
                context_document=asdict(context),
            )
            # 记录setup阶段admitted事件。
            attempt_store.append_event(
                run_id=context.run_id,
                node_id=context.node_id,
                event_type="admitted",
                phase="setup",
                code="ADMITTED",
            )
        except Exception as exc:
            # attempt-start创建失败不得伪造成功；存入错误码供后续处理。
            code = getattr(exc, "code", "E_ATTEMPT_START_FAILED")
            item.stash[_MARKER_ERROR_KEY] = code
            pytest.fail(code, pytrace=False)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """只包裹真实fixture teardown；R2锁延迟到finalization结束后释放。"""
    yield


def _terminal_status_from_reports(reports: Mapping[str, pytest.TestReport]) -> str:
    """从pytest真实三阶段报告推导attempt终态，不读取或持久化原始异常。"""
    failed = [report for report in reports.values() if report.failed]
    if failed:
        failure_text = " ".join(str(report.longrepr).lower() for report in failed)
        if "timeout" in failure_text or "timed out" in failure_text:
            return "timed_out"
        if "keyboardinterrupt" in failure_text or "cancelled" in failure_text:
            return "cancelled"
        return "failed"
    if any(report.skipped for report in reports.values()):
        return "cancelled"
    if all(phase in reports for phase in ("setup", "call", "teardown")):
        return "passed"
    return "write_outcome_unknown"


def _stable_exception(exc: BaseException) -> tuple[str, str, str]:
    """把异常压缩成稳定错误码、异常类和消息摘要，不持久化原始消息。"""
    raw_code = getattr(exc, "code", None)
    if not isinstance(raw_code, str):
        raw_code = str(exc).split(":", 1)[0].strip()
    code = raw_code if re.fullmatch(r"E_[A-Z0-9_]+", raw_code or "") else "E_FINALIZER_FAILED"
    return code, type(exc).__name__, _sha256_text(str(exc))


def _release_r2_lock(item: pytest.Item) -> None:
    """finalization完成后释放锁；失败由调用方投影为治理错误。"""
    lock = item.stash.get(_R2_LOCK_KEY, None)
    if lock is None:
        return
    lock.release()
    item.stash[_R2_LOCK_KEY] = None


def _record_session_node(
    *,
    item: pytest.Item,
    context: _ExecutionContextV3,
    attempt_store: ExecutionAttemptStore,
    finalization_status: str,
    receipt_ref: str | None = None,
    receipt_hash: str | None = None,
) -> None:
    terminal = attempt_store.read_terminal(run_id=context.run_id, node_id=context.node_id)
    if terminal is None:
        return
    node = {
        "run_id": context.run_id,
        "node_id": context.node_id,
        "terminal_ref": context.attempt_ref + "/terminal.json",
        "terminal_hash": canonical_hash(terminal),
        "finalization_status": finalization_status,
        "_execution_origin": context.execution_origin,
        "_origin_evidence_digest": context.origin_evidence["evidence_digest"],
    }
    if receipt_ref and receipt_hash:
        node["receipt_ref"] = receipt_ref
        node["receipt_hash"] = receipt_hash
    nodes = item.config.stash.get(_SESSION_NODE_RESULTS_KEY, [])
    nodes.append(node)
    item.config.stash[_SESSION_NODE_RESULTS_KEY] = nodes


def _fail_teardown_report(report: pytest.TestReport, *, code: str, exception_class: str, message_digest: str) -> None:
    """让原pytest/TeamCity进程看到稳定且非空的finalization longrepr。"""
    detail = f"{code} [{exception_class}; message_digest={message_digest}]"
    report.sections.append(("ui-test-governance", detail))
    report.longrepr = detail
    report.outcome = "failed"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    """在其他makereport wrapper完成后执行事务，再决定唯一terminal。"""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    context = item.stash.get(EXECUTION_CONTEXT_KEY, None)
    attempt_store = item.stash.get(_ATTEMPT_STORE_KEY, None)
    if context is None:
        return
    if attempt_store is None or not item.stash.get(_ATTEMPT_STARTED_KEY, False):
        if report.when == "teardown":
            try:
                _release_r2_lock(item)
            except Exception as exc:
                code, exception_class, message_digest = _stable_exception(exc)
                _fail_teardown_report(
                    report, code=code, exception_class=exception_class, message_digest=message_digest
                )
        return

    reports = item.stash.get(_PHASE_REPORTS_KEY, {})
    reports[report.when] = report
    item.stash[_PHASE_REPORTS_KEY] = reports
    try:
        attempt_store.append_event(
            run_id=context.run_id,
            node_id=context.node_id,
            event_type="executing",
            phase=report.when,
            code=f"PYTEST_{report.when.upper()}_{report.outcome.upper()}",
        )
    except ExecutionAttemptStoreError as exc:
        _fail_teardown_report(
            report,
            code=exc.code,
            exception_class=type(exc).__name__,
            message_digest=_sha256_text(str(exc)),
        )
        reports[report.when] = report

    if report.when != "teardown":
        return

    terminal_status = _terminal_status_from_reports(reports)
    if terminal_status != "passed":
        try:
            _release_r2_lock(item)
        except Exception as exc:
            code, exception_class, message_digest = _stable_exception(exc)
            terminal_status = "error"
            _fail_teardown_report(
                report, code=code, exception_class=exception_class, message_digest=message_digest
            )
        attempt_store.create_terminal(
            run_id=context.run_id,
            node_id=context.node_id,
            status=terminal_status,
            code=f"PYTEST_{terminal_status.upper()}",
        )
        _record_session_node(
            item=item,
            context=context,
            attempt_store=attempt_store,
            finalization_status="missing",
        )
        return

    qualification_mode = bool(item.config.getoption("--ui-pre-submit-only", False))
    read_only_mode = context.risk_level != "r2-ui-write-test"
    if qualification_mode or read_only_mode:
        try:
            _release_r2_lock(item)
            attempt_store.create_terminal(
                run_id=context.run_id,
                node_id=context.node_id,
                status="passed",
                code="PYTEST_PASSED",
            )
            _record_session_node(
                item=item,
                context=context,
                attempt_store=attempt_store,
                finalization_status=(
                    "not_applicable_qualification" if qualification_mode else "not_applicable_read_only"
                ),
            )
        except Exception as exc:
            code, exception_class, message_digest = _stable_exception(exc)
            _fail_teardown_report(
                report, code=code, exception_class=exception_class, message_digest=message_digest
            )
        return

    transaction_id = "FIN-" + hashlib.sha256(
        f"{context.session_id}:{context.run_id}:{context.node_id}".encode("utf-8")
    ).hexdigest()[:24]
    transaction: FinalizationTransaction | None = None
    receipt_ref: str | None = None
    receipt_hash: str | None = None
    try:
        target = item.config.hook.pytest_ui_test_finalization_target_v1(
            run_id=context.run_id,
            node_id=context.node_id,
            attempt_store=attempt_store,
        )
        if not isinstance(target, Mapping) or not isinstance(target.get("run_root"), str):
            raise FinalizationTransactionError("E_FINALIZATION_TARGET_REQUIRED")
        transaction = FinalizationTransaction(target["run_root"])
        attempt_store.append_event(
            run_id=context.run_id,
            node_id=context.node_id,
            event_type="finalization_started",
            phase="finalization",
            code="FINALIZATION_STARTED",
            transaction_id=transaction_id,
        )
        committed_event_time = _utc_now()
        planned_committed_event = {
            "event_type": "finalization_committed",
            "recorded_at": committed_event_time,
            "phase": "finalization",
            "code": "FINALIZATION_COMMITTED",
            "transaction_id": transaction_id,
        }
        pre_terminal_events_hash = attempt_store.compute_pre_terminal_hash(
            run_id=context.run_id,
            node_id=context.node_id,
            additional_events=[planned_committed_event],
        )
        phase_status = {
            phase: reports[phase].outcome if phase in reports else "unknown"
            for phase in ("setup", "call", "teardown")
        }
        candidate = item.config.hook.pytest_ui_test_build_finalization_candidate_v1(
            run_id=context.run_id,
            node_id=context.node_id,
            transaction_id=transaction_id,
            pre_terminal_events_hash=pre_terminal_events_hash,
            pytest_phase_status=phase_status,
            attempt_store=attempt_store,
        )
        if not isinstance(candidate, Mapping):
            raise FinalizationTransactionError("E_FINALIZATION_CANDIDATE_REQUIRED")
        committed = transaction.commit(
            transaction_id=transaction_id,
            run_id=context.run_id,
            node_id=context.node_id,
            run_result=candidate.get("run_result", {}),
            evidence_index=candidate.get("evidence_index", {}),
        )
        if committed.get("status") != "committed":
            raise FinalizationTransactionError("E_FINALIZATION_NOT_CURRENT_PROCESS_COMMITTED")
        manifest = committed["manifest"]
        receipt = committed["receipt"]
        attempt_store.append_event(
            run_id=context.run_id,
            node_id=context.node_id,
            event_type="finalization_committed",
            phase="finalization",
            code="FINALIZATION_COMMITTED",
            transaction_id=transaction_id,
            recorded_at=committed_event_time,
        )
        if attempt_store.compute_pre_terminal_hash(
            run_id=context.run_id, node_id=context.node_id
        ) != pre_terminal_events_hash:
            raise FinalizationTransactionError("E_FINALIZATION_PRE_TERMINAL_CLOSURE_MISMATCH")
        # 锁覆盖UI写与commit/receipt；在passed terminal前释放，使释放失败也不能留下passed终态。
        _release_r2_lock(item)
        commit_ref = f"runs/{context.run_id}/finalization/finalization-commit.json"
        receipt_ref = f"runs/{context.run_id}/finalization/finalization-receipt.json"
        commit_hash = canonical_hash(manifest)
        receipt_hash = canonical_hash(receipt)
        attempt_store.create_terminal(
            run_id=context.run_id,
            node_id=context.node_id,
            status="passed",
            code="PYTEST_PASSED",
            commit_manifest_ref=commit_ref,
            commit_manifest_hash=commit_hash,
            receipt_ref=receipt_ref,
            receipt_hash=receipt_hash,
            pre_terminal_events_hash=pre_terminal_events_hash,
            finalization_run_root=target["run_root"],
        )
        _record_session_node(
            item=item,
            context=context,
            attempt_store=attempt_store,
            finalization_status="committed",
            receipt_ref=receipt_ref,
            receipt_hash=receipt_hash,
        )
        return
    except Exception as exc:
        code, exception_class, message_digest = _stable_exception(exc)
        _fail_teardown_report(
            report, code=code, exception_class=exception_class, message_digest=message_digest
        )  # 先保证原helper可见，后续任何证据写失败都不能吞掉longrepr。
        if transaction is not None:
            try:
                failed = transaction.record_failure(
                    transaction_id=transaction_id,
                    session_id=context.session_id,
                    run_id=context.run_id,
                    node_id=context.node_id,
                    error_code=code,
                    exception_class=exception_class,
                    message_digest=message_digest,
                )
                receipt = failed["receipt"]
                receipt_ref = f"runs/{context.run_id}/finalization/finalization-receipt.json"
                receipt_hash = canonical_hash(receipt)
            except Exception:
                receipt_ref = None
                receipt_hash = None
        if receipt_ref is None or receipt_hash is None:
            try:
                receipt_ref, fallback_receipt = attempt_store.write_finalization_failure_receipt(
                    run_id=context.run_id,
                    node_id=context.node_id,
                    session_id=context.session_id,
                    transaction_id=transaction_id,
                    error_code=code,
                    exception_class=exception_class,
                    message_digest=message_digest,
                )
                receipt_hash = canonical_hash(fallback_receipt)
            except Exception as receipt_exc:
                report.sections.append((
                    "ui-test-governance",
                    "E_FINALIZATION_FAILURE_RECEIPT_WRITE_FAILED:" + _sha256_text(str(receipt_exc)),
                ))
        try:
            attempt_store.append_event(
                run_id=context.run_id,
                node_id=context.node_id,
                event_type="finalization_failed",
                phase="finalization",
                code=code,
                exception_class=exception_class,
                message_digest=message_digest,
                transaction_id=transaction_id,
            )
        except Exception as event_exc:
            report.sections.append((
                "ui-test-governance",
                "E_FINALIZATION_FAILURE_EVENT_WRITE_FAILED:" + _sha256_text(str(event_exc)),
            ))
        try:
            _release_r2_lock(item)
        except Exception as lock_exc:
            report.sections.append((
                "ui-test-governance",
                "E_R2_LOCK_RELEASE_FAILED:" + _sha256_text(str(lock_exc)),
            ))
        try:
            attempt_store.create_terminal(
                run_id=context.run_id,
                node_id=context.node_id,
                status="error",
                code=code,
                receipt_ref=receipt_ref or "",
                receipt_hash=receipt_hash or "",
            )
        except Exception as terminal_exc:
            report.sections.append((
                "ui-test-governance",
                "E_FINALIZATION_ERROR_TERMINAL_WRITE_FAILED:" + _sha256_text(str(terminal_exc)),
            ))
            return
        try:
            _record_session_node(
                item=item,
                context=context,
                attempt_store=attempt_store,
                finalization_status="failed" if receipt_ref and receipt_hash else "missing",
                receipt_ref=receipt_ref,
                receipt_hash=receipt_hash,
            )
        except Exception as session_exc:
            report.sections.append((
                "ui-test-governance",
                "E_FINALIZATION_SESSION_NODE_WRITE_FAILED:" + _sha256_text(str(session_exc)),
            ))


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """写PytestSessionResultV1；只投影最终exit，不补写任何passed terminal。"""
    nodes = session.config.stash.get(_SESSION_NODE_RESULTS_KEY, [])
    evidence_root = session.config.stash.get(_SESSION_EVIDENCE_ROOT_KEY, "")
    if not nodes or not evidence_root:
        return
    try:
        origins = {node["_execution_origin"] for node in nodes}
        origin = next(iter(origins)) if len(origins) == 1 else "unknown"
        origin_digests = sorted({node["_origin_evidence_digest"] for node in nodes})
        public_nodes = [
            {key: value for key, value in node.items() if not key.startswith("_")}
            for node in nodes
        ]
        all_committed = all(
            node["finalization_status"] in {
                "committed", "not_applicable_qualification", "not_applicable_read_only"
            }
            for node in public_nodes
        )
        session_status = "passed" if int(exitstatus) == 0 and all_committed else "failed"
        document: dict[str, Any] = {
            "schema_version": "ui-test.pytest-session-result.v1",
            "session_id": session.config.stash[_SESSION_ID_KEY],
            "execution_origin": origin,
            "origin_evidence_digest": (
                origin_digests[0]
                if len(origin_digests) == 1
                else canonical_hash({"origin_evidence_digests": origin_digests})
            ),
            "nodes": public_nodes,
            "pytest_exitstatus": int(exitstatus),
            "all_required_nodes_committed": all_committed,
            "session_status": session_status,
            "recorded_at": _utc_now(),
        }
        document["session_result_hash"] = canonical_hash(document)
        if validate_document(document, "pytest-session-result-v1.schema.json"):
            raise RuntimeError("E_PYTEST_SESSION_RESULT_SCHEMA_INVALID")
        target = io_path(Path(evidence_root) / "sessions" / f"{document['session_id']}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        # SessionResult缺失必须反映到原helper退出码；恢复器也不得事后补成passed。
        session.exitstatus = pytest.ExitCode.INTERNAL_ERROR


@pytest.fixture
def ui_test_execution_context(request: pytest.FixtureRequest) -> _ExecutionContextV3:
    """function-scope fixture：项目 runtime 通过此 fixture 消费已验证上下文。

    不允许重新计算来源或批准。如果 item 没有 ui_test marker，fixture 报错。
    """
    context = request.node.stash.get(EXECUTION_CONTEXT_KEY, None)
    if context is None:
        pytest.fail("E_UI_TEST_CONTEXT_NOT_AVAILABLE: fixture requires ui_test marker", pytrace=False)
    return context
