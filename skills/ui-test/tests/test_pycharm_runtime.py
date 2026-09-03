from datetime import datetime
from unittest.mock import patch

from scripts.ui_test_core.pycharm_runtime import resolve_pycharm_run_context


def _config(*, enabled: bool = True, environment: str = "test") -> dict:
    return {
        "scope": {"environment": environment},
        "pycharm_manual_execution": {
            "auto_generate_run_id": enabled,
            "auto_approve_r2_visible_ui": enabled,
        },
    }  # 构造不包含任何私有值的最小项目配置。


def test_pycharm_manual_run_generates_identity_and_r2_approval() -> None:
    result = resolve_pycharm_run_context(
        config=_config(),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        requested_run_id=None,
        explicitly_approved=False,
        environ={"PYCHARM_HOSTED": "1"},
        now=datetime(2026, 8, 28, 13, 5, 9),
        unique_suffix="A1B2C3D4",
    )  # 模拟测试工程师从 PyCharm 直接运行用例。
    assert result["run_id"] == "RVI-20260828-R2-A-130509-A1B2C3D4"  # 每次运行自动获得可追溯唯一身份。
    assert result["approved"] is True  # 人工点击运行在项目显式策略下形成一次 R2 授权。
    assert result["approval_source"] == "pycharm-manual-run"  # 审计记录能够区分自动与命令行授权。


def test_non_pycharm_run_remains_fail_closed_without_explicit_approval() -> None:
    result = resolve_pycharm_run_context(
        config=_config(),
        case_id="BOPS-ANNOUNCEMENT-P0-B",
        branch_id="popup-announcement",
        requested_run_id=None,
        explicitly_approved=False,
        environ={},
    )  # 模拟命令行或 CI 未携带任何授权参数。
    assert result["run_id"] == "manual-run"  # 保留原有兼容运行编号。
    assert result["approved"] is False  # 非 PyCharm 调用不得自动获得写权限。
    assert result["approval_source"] == "not-approved"  # 未授权状态必须显式可见。


def test_production_and_disabled_policy_never_auto_approve() -> None:
    for config in (_config(enabled=False), _config(environment="production")):
        result = resolve_pycharm_run_context(
            config=config,
            case_id="BOPS-ANNOUNCEMENT-P0-A",
            branch_id="system-announcement",
            requested_run_id=None,
            explicitly_approved=False,
            environ={"PYCHARM_HOSTED": "1"},
        )  # 验证配置关闭和非测试环境两个阻断条件。
        assert result["approved"] is False  # 任一门禁不满足都必须拒绝自动授权。


def test_explicit_values_take_precedence_outside_pycharm() -> None:
    result = resolve_pycharm_run_context(
        config=_config(enabled=False),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        requested_run_id="RVI-EXPLICIT-001",
        explicitly_approved=True,
        environ={},
    )  # 保留现有受控命令行执行能力。
    assert result["run_id"] == "RVI-EXPLICIT-001"  # 显式运行编号不得被自动值覆盖。
    assert result["approved"] is True  # 显式批准继续有效。
    assert result["approval_source"] == "explicit-cli"  # 审计来源保持准确。


def test_pycharm_runner_command_line_is_detected_without_environment_marker() -> None:
    with patch("scripts.ui_test_core.pycharm_runtime.sys.argv", ["_jb_pytest_runner.py", "--path", "case.py"]):
        result = resolve_pycharm_run_context(
            config=_config(),
            case_id="BOPS-ANNOUNCEMENT-P0-B",
            branch_id="popup-announcement",
            requested_run_id=None,
            explicitly_approved=False,
            environ={},
            now=datetime(2026, 8, 28, 15, 38, 9),
            unique_suffix="B1C2D3E4",
        )  # 模拟 PyCharm runner 未提供 PYCHARM_HOSTED 的真实启动方式。
    assert result["run_id"] == "RVI-20260828-R2-B-153809-B1C2D3E4"  # 仍然自动生成唯一运行身份。
    assert result["approved"] is True  # 测试环境可见 UI 的项目策略继续生效。
    assert result["approval_source"] == "pycharm-manual-run"  # 记录为人工 PyCharm 运行而非伪造命令行批准。
