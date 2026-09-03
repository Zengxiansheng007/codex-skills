"""解析 PyCharm 人工执行的 UI-Test 运行身份与 R2 授权。"""

from __future__ import annotations

import os  # 读取 PyCharm 进程标记。
import re  # 校验运行编号字符集。
import sys  # 识别 PyCharm 的官方 pytest runner 命令行。
import uuid  # 生成并发安全的随机后缀。
from datetime import datetime  # 生成可读的本地时间片段。
from typing import Any, Mapping  # 声明配置和环境的结构类型。


def resolve_pycharm_run_context(
    *,
    config: Mapping[str, Any],
    case_id: str,
    branch_id: str,
    requested_run_id: str | None,
    explicitly_approved: bool,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
    unique_suffix: str | None = None,
) -> dict[str, Any]:
    environment = environ if environ is not None else os.environ  # 使用调用方环境判断是否由 PyCharm 人工启动。
    policy = config.get("pycharm_manual_execution", {})  # 从项目配置读取显式的 PyCharm 执行策略。
    hosted = environment.get("PYCHARM_HOSTED") == "1" or any("_jb_pytest_runner.py" in argument.lower() for argument in sys.argv)  # 同时兼容 PyCharm 未注入 PYCHARM_HOSTED 的官方 runner。
    test_environment = config.get("scope", {}).get("environment") == "test"  # 自动授权仅允许测试环境。
    auto_run_id = hosted and test_environment and policy.get("auto_generate_run_id") is True  # 三项条件必须同时满足。
    auto_r2 = hosted and test_environment and policy.get("auto_approve_r2_visible_ui") is True  # 仅放行可见 UI 的单次 R2 提交。
    run_id = requested_run_id or (_new_run_id(case_id, now=now, unique_suffix=unique_suffix) if auto_run_id else "manual-run")  # 优先保留人工显式传入的运行编号。
    approved = bool(explicitly_approved or auto_r2)  # 显式命令行授权仍可用于非 PyCharm 的受控执行。
    approval_source = "explicit-cli" if explicitly_approved else "pycharm-manual-run" if auto_r2 else "not-approved"  # 记录授权来源便于审计。
    return {"run_id": run_id, "approved": approved, "approval_source": approval_source, "pycharm_hosted": hosted, "branch_id": branch_id}  # 不返回任何账号、密码或私有 URL。


def _new_run_id(case_id: str, *, now: datetime | None, unique_suffix: str | None) -> str:
    current = now or datetime.now()  # 使用本机时间生成便于人工识别的运行编号。
    branch_suffix = case_id.rsplit("-", 1)[-1].upper()  # 优先复用稳定用例编号末段的 A/B 标识。
    if not re.fullmatch(r"[A-Z0-9]{1,8}", branch_suffix):
        branch_suffix = "CASE"  # 非标准用例编号使用固定安全占位符。
    random_suffix = (unique_suffix or uuid.uuid4().hex[:8]).upper()  # 随机后缀避免同秒并发执行发生冲突。
    if not re.fullmatch(r"[A-F0-9]{8}", random_suffix):
        raise ValueError("E_PYCHARM_RUN_SUFFIX_INVALID")  # 拒绝不符合安全字符集的测试注入值。
    return f"RVI-{current:%Y%m%d}-R2-{branch_suffix}-{current:%H%M%S}-{random_suffix}"  # 结果符合现有 Run ID 字符与长度约束。
