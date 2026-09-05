"""解析正式 pytest 调用来源、运行身份与 PyCharm R2 候选授权。"""

from __future__ import annotations

import hashlib  # 生成不暴露本机路径和命令行的来源摘要。
import json  # 对来源证据执行稳定序列化。
import os  # 读取调用方显式传入或当前进程的环境标记。
import re  # 校验运行编号字符集。
import sys  # 读取 Python 原始入口和程序参数。
import uuid  # 生成并发安全的随机后缀。
from datetime import datetime  # 生成可读的本地时间片段。
from pathlib import Path  # 解析真实 JetBrains runner 路径。
from typing import Any, Mapping, Sequence  # 声明稳定的输入结构。


_CI_MARKERS = (  # CI 证据优先于任何 PyCharm 辅助标记。
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "BUILD_BUILDID",
    "JENKINS_URL",
    "TEAMCITY_VERSION",
)
_PYCHARM_POLICY = {  # v2.2 transaction-v1策略必须完整匹配，缺失值不得推断。
    "contract_version": 3,
    "origin_detection": "jetbrains-runner-path",
    "entry_scope": "stable-active-runners",
    "r2_authorization": "auto-test-only",
    "run_scope": "per-node",
    "r2_parallelism": "serial-project-environment",
    "finalization_contract": "transaction-v1",
    "run_result_contract": "v5",
    "session_result_contract": "v1",
    "acceptance_contract": "external-exit-v1",
}
_RISK_CODE = {  # Run ID 使用短风险码，但完整风险仍保存在上下文中。
    "r0-read-only": "R0",
    "r1-read-only-authenticated": "R1",
    "r2-ui-write-test": "R2",
    "r3-high-impact": "R3",
}


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()  # 返回带算法前缀的稳定摘要。


def _windows_process_argv() -> tuple[str, ...]:
    """读取Windows创建进程时的原始命令行；失败时返回空元组并继续fail closed。"""
    if os.name != "nt":
        return ()
    try:
        import ctypes  # 仅在Windows运行时加载标准库FFI。

        kernel32 = ctypes.windll.kernel32
        shell32 = ctypes.windll.shell32
        kernel32.GetCommandLineW.restype = ctypes.c_wchar_p
        raw = kernel32.GetCommandLineW()
        argc = ctypes.c_int()
        shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
        shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        pointer = shell32.CommandLineToArgvW(raw, ctypes.byref(argc))
        if not pointer:
            return ()
        try:
            return tuple(pointer[index] for index in range(argc.value))
        finally:
            kernel32.LocalFree(ctypes.cast(pointer, ctypes.c_void_p))
    except Exception:
        return ()  # OS证据不可读时不得猜测PyCharm来源。


def _runner_candidate(argv: Sequence[str], orig_argv: Sequence[str], main_file: str | None, process_argv: Sequence[str]) -> Path | None:
    candidates: list[str] = []  # 只检查真实程序入口，不扫描普通 pytest 参数。
    if argv:
        candidates.append(str(argv[0]))
    if len(orig_argv) > 1:
        candidates.append(str(orig_argv[1]))
    if main_file:
        candidates.append(str(main_file))  # PyCharm helper进入pytest后可能改写argv，但__main__.__file__仍绑定真实入口脚本。
    if len(process_argv) > 1:
        candidates.append(str(process_argv[1]))  # 只接受进程脚本入口位，禁止普通pytest参数伪造runner。
    for value in candidates:
        path = Path(value)
        if path.name.lower() != "_jb_pytest_runner.py":
            continue
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        suffix = tuple(part.lower() for part in resolved.parts[-3:])
        if suffix == ("helpers", "pycharm", "_jb_pytest_runner.py"):
            return resolved
    return None


def classify_execution_origin(
    *,
    argv: Sequence[str] | None = None,
    orig_argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
    declared_origin: str | None = None,
    main_file: str | None = None,
    process_argv: Sequence[str] | None = None,
) -> dict[str, Any]:
    """分类执行通道并返回不含绝对路径或环境值的摘要证据。"""

    environment = environ if environ is not None else os.environ  # 调用方可注入最小测试环境。
    program_argv = tuple(argv if argv is not None else sys.argv)  # 保留程序实际看到的入口。
    original_argv = tuple(orig_argv if orig_argv is not None else getattr(sys, "orig_argv", ()))  # Python 3.10+ 原始参数用于交叉核对。
    program_main_file = main_file if main_file is not None else getattr(sys.modules.get("__main__"), "__file__", None)  # 读取实际执行脚本，不依赖pytest改写后的参数位置。
    original_process_argv = tuple(process_argv) if process_argv is not None else _windows_process_argv()  # Windows启动命令行不受pytest内部argv改写影响。
    ci_marker = next((name for name in _CI_MARKERS if environment.get(name)), None)
    strong_ci_marker = next((name for name in _CI_MARKERS if name != "TEAMCITY_VERSION" and environment.get(name)), None)  # PyCharm helper会为本地测试协议设置TEAMCITY_VERSION。
    runner = _runner_candidate(program_argv, original_argv, program_main_file, original_process_argv)
    safe_argv0 = Path(str(program_argv[0])).name if program_argv else "unknown"  # 只保留basename，避免泄露本机绝对路径。

    if strong_ci_marker is not None:
        origin = "ci"
        source_type = "ci-env"
        invocation_marker = "ci-marker-present"
    elif runner is not None:
        origin = "pycharm"
        source_type = "jetbrains-runner-path"
        invocation_marker = "runner-path-and-file"
    elif ci_marker is not None:
        origin = "ci"  # 无精确JetBrains runner时，TEAMCITY_VERSION仍是有效CI证据。
        source_type = "ci-env"
        invocation_marker = "ci-marker-present"
    elif declared_origin == "codex-cli":
        origin = "codex-cli"
        source_type = "explicit-cli-arg"
        invocation_marker = "declared-codex-cli"
    elif program_argv:
        origin = "cli"
        source_type = "sys-argv"
        invocation_marker = "ordinary-cli"
    else:
        origin = "unknown"
        source_type = "unknown"
        invocation_marker = "no-entry-evidence"

    runner_path_hash = _sha256_text(str(runner).lower()) if runner is not None else None
    runner_content_hash = None
    if runner is not None:
        try:
            runner_content_hash = "sha256:" + hashlib.sha256(runner.read_bytes()).hexdigest()
        except OSError:
            runner_content_hash = None  # 路径只负责分类；内容无法读回时V3上下文门禁将拒绝执行。
    evidence_material = {
        "execution_origin": origin,
        "source_type": source_type,
        "argv0": safe_argv0,
        "invocation_marker": invocation_marker,
        "runner_path_hash": runner_path_hash,
        "runner_content_hash": runner_content_hash,
        "pycharm_hosted_hint": environment.get("PYCHARM_HOSTED") == "1",
    }
    evidence = {
        "source_type": source_type,
        "evidence_digest": _sha256_text(json.dumps(evidence_material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        "argv0": safe_argv0,
        "invocation_marker": invocation_marker,
    }
    if runner_path_hash is not None:
        evidence["runner_path_hash"] = runner_path_hash
    if runner_content_hash is not None:
        evidence["runner_content_hash"] = runner_content_hash
    return {"execution_origin": origin, "origin_evidence": evidence, "pycharm_hosted": origin == "pycharm"}


def _policy_enabled(config: Mapping[str, Any]) -> bool:
    if config.get("schema_version") != "2.2":
        return False
    policy = config.get("pycharm_manual_execution")
    if not isinstance(policy, Mapping):
        return False
    return all(policy.get(key) == value for key, value in _PYCHARM_POLICY.items())


def resolve_pycharm_run_context(
    *,
    config: Mapping[str, Any],
    case_id: str,
    branch_id: str,
    requested_run_id: str | None,
    explicitly_approved: bool,
    node_id: str | None = None,
    risk_level: str = "r2-ui-write-test",
    argv: Sequence[str] | None = None,
    orig_argv: Sequence[str] | None = None,
    declared_origin: str | None = None,
    environ: Mapping[str, str] | None = None,
    process_argv: Sequence[str] | None = None,
    now: datetime | None = None,
    unique_suffix: str | None = None,
) -> dict[str, Any]:
    """解析每个测试节点的来源、Run ID与候选批准，不消费R2写许可。"""

    origin = classify_execution_origin(  # 来源分类与授权计算保持分离。
        argv=argv,
        orig_argv=orig_argv,
        environ=environ,
        declared_origin=declared_origin,
        process_argv=process_argv,
    )
    policy = config.get("pycharm_manual_execution") if isinstance(config.get("pycharm_manual_execution"), Mapping) else {}
    project_environment = config.get("scope", {}).get("environment") if isinstance(config.get("scope"), Mapping) else None
    policy_enabled = _policy_enabled(config)
    pycharm_origin = origin["execution_origin"] == "pycharm"
    auto_run_id = pycharm_origin and policy_enabled and policy.get("auto_generate_run_id") is True
    auto_r2 = (
        pycharm_origin
        and policy_enabled
        and project_environment == "test"
        and risk_level == "r2-ui-write-test"
        and policy.get("auto_approve_r2_visible_ui") is True
    )
    effective_node_id = node_id or case_id  # 旧调用方暂以case作为节点；pytest插件接入后必须传正式nodeid。
    run_id = requested_run_id
    if run_id is None and auto_run_id:
        run_id = _new_run_id(effective_node_id, risk_level=risk_level, now=now, unique_suffix=unique_suffix)
    approved = bool(policy_enabled and (explicitly_approved or auto_r2))  # 旧配置即使携带显式标志也不能获得新执行批准。
    approval_source = "explicit-cli" if explicitly_approved and policy_enabled else "pycharm-project-policy" if auto_r2 else "not-approved"
    return {
        "execution_origin": origin["execution_origin"],
        "origin_evidence": origin["origin_evidence"],
        "run_id": run_id,
        "approved": approved,
        "approval_source": approval_source,
        "pycharm_hosted": origin["pycharm_hosted"],
        "node_id": effective_node_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "risk_level": risk_level,
        "environment": project_environment,
    }


def _new_run_id(node_id: str, *, risk_level: str, now: datetime | None, unique_suffix: str | None) -> str:
    current = now or datetime.now()  # 使用本机时间生成便于人工识别的运行编号。
    risk_code = _RISK_CODE.get(risk_level)
    if risk_code is None:
        raise ValueError("E_PYCHARM_RISK_LEVEL_INVALID")
    node_digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:8].upper()  # 用摘要绑定节点但不暴露长路径。
    random_suffix = (unique_suffix or uuid.uuid4().hex[:8]).upper()
    if not re.fullmatch(r"[A-F0-9]{8}", random_suffix):
        raise ValueError("E_PYCHARM_RUN_SUFFIX_INVALID")
    run_id = f"UIT-{current:%Y%m%dT%H%M%S}{current.microsecond // 1000:03d}-{risk_code}-{node_digest}-{random_suffix}"
    if len(run_id) > 80 or not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("E_PYCHARM_RUN_ID_INVALID")
    return run_id
