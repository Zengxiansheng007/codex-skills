import hashlib
from datetime import datetime
from pathlib import Path

from scripts.ui_test_core.pycharm_runtime import classify_execution_origin, resolve_pycharm_run_context


def _config(*, enabled: bool = True, environment: str = "test", schema_version: str = "2.2") -> dict:
    return {
        "schema_version": schema_version,
        "scope": {"environment": environment},
        "pycharm_manual_execution": {
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
            "auto_generate_run_id": enabled,
            "auto_approve_r2_visible_ui": enabled,
        },
    }  # 构造不包含项目私有值的最小v2.2执行配置。


def _runner(tmp_path: Path, content: str = "# runner\n") -> Path:
    path = tmp_path / "plugins" / "python-ce" / "helpers" / "pycharm" / "_jb_pytest_runner.py"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")  # 创建仅用于来源分类的本地测试入口。
    return path


def test_pycharm_r2_generates_per_node_identity_and_candidate_approval(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    node_id = "test_bops_announcement_p0_a.py::test_system[chromium]"
    result = resolve_pycharm_run_context(
        config=_config(),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        node_id=node_id,
        risk_level="r2-ui-write-test",
        requested_run_id=None,
        explicitly_approved=False,
        argv=[str(runner), "--path", "case.py"],
        orig_argv=["python.exe", str(runner), "--path", "case.py"],
        environ={},
        now=datetime(2026, 8, 28, 13, 5, 9),
        unique_suffix="A1B2C3D4",
    )  # 模拟测试工程师从PyCharm直接运行一个R2节点。
    node_digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:8].upper()
    assert result["run_id"] == f"UIT-20260828T130509000-R2-{node_digest}-A1B2C3D4"
    assert result["execution_origin"] == "pycharm"
    assert result["approved"] is True
    assert result["approval_source"] == "pycharm-project-policy"
    assert Path(result["origin_evidence"]["argv0"]).name == "_jb_pytest_runner.py"
    assert ":\\" not in result["origin_evidence"]["argv0"]  # 证据不得返回本机绝对路径。


def test_environment_hint_alone_does_not_create_pycharm_origin() -> None:
    result = classify_execution_origin(argv=["pytest.exe"], orig_argv=[], environ={"PYCHARM_HOSTED": "1"})
    assert result["execution_origin"] == "cli"
    assert result["pycharm_hosted"] is False


def test_original_argv_can_identify_real_runner(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(
        argv=["pytest"],
        orig_argv=["python.exe", str(runner), "--path", "case.py"],
        environ={},
    )
    assert result["execution_origin"] == "pycharm"
    assert result["origin_evidence"]["source_type"] == "jetbrains-runner-path"


def test_main_module_file_identifies_runner_after_pytest_rewrites_argv(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(
        argv=["pytest", "case.py::test_case"],
        orig_argv=["python.exe", "-m", "pytest", "case.py::test_case"],
        environ={"PYCHARM_HOSTED": "1"},
        main_file=str(runner),
    )
    assert result["execution_origin"] == "pycharm"
    assert result["origin_evidence"]["source_type"] == "jetbrains-runner-path"


def test_main_module_file_must_be_exact_existing_jetbrains_runner(tmp_path: Path) -> None:
    ordinary = tmp_path / "_jb_pytest_runner.py"
    ordinary.write_text("# not under helpers/pycharm\n", encoding="utf-8")
    result = classify_execution_origin(
        argv=["pytest"], orig_argv=["python.exe", "-m", "pytest"], environ={"PYCHARM_HOSTED": "1"}, main_file=str(ordinary)
    )
    assert result["execution_origin"] == "cli"


def test_windows_process_entry_identifies_runner_after_all_python_argv_are_rewritten(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(
        argv=["pytest", "case.py"],
        orig_argv=["python.exe", "-m", "pytest"],
        environ={"PYCHARM_HOSTED": "1"},
        main_file="pytest",
        process_argv=["python.exe", str(runner), "--path", "case.py"],
    )
    assert result["execution_origin"] == "pycharm"
    assert result["origin_evidence"]["runner_path_hash"].startswith("sha256:")
    assert result["origin_evidence"]["runner_content_hash"].startswith("sha256:")


def test_windows_process_later_argument_cannot_spoof_runner(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(
        argv=["pytest"],
        orig_argv=["python.exe", "-m", "pytest"],
        environ={"PYCHARM_HOSTED": "1"},
        main_file="pytest",
        process_argv=["python.exe", "-m", "pytest", str(runner)],
    )
    assert result["execution_origin"] == "cli"


def test_ci_origin_precedes_real_pycharm_runner(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(argv=[str(runner)], orig_argv=[], environ={"CI": "1"})
    assert result["execution_origin"] == "ci"
    assert result["pycharm_hosted"] is False


def test_pycharm_teamcity_transport_marker_does_not_override_exact_runner(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    result = classify_execution_origin(
        argv=["pytest"], orig_argv=["python.exe", str(runner)], environ={"TEAMCITY_VERSION": "LOCAL"}, main_file="pytest", process_argv=["python.exe", str(runner), "--path", "case.py"]
    )
    assert result["execution_origin"] == "pycharm"
    assert result["origin_evidence"]["source_type"] == "jetbrains-runner-path"


def test_teamcity_marker_without_exact_runner_remains_ci() -> None:
    result = classify_execution_origin(
        argv=["pytest"], orig_argv=["python.exe", "-m", "pytest"], environ={"TEAMCITY_VERSION": "SERVER"}, main_file="pytest", process_argv=["python.exe", "-m", "pytest"]
    )
    assert result["execution_origin"] == "ci"


def test_declared_codex_cli_is_separate_from_ordinary_cli() -> None:
    codex = classify_execution_origin(argv=["pytest.exe"], orig_argv=[], environ={}, declared_origin="codex-cli")
    ordinary = classify_execution_origin(argv=["pytest.exe"], orig_argv=[], environ={})
    assert codex["execution_origin"] == "codex-cli"
    assert ordinary["execution_origin"] == "cli"


def test_non_pycharm_without_run_id_remains_missing() -> None:
    result = resolve_pycharm_run_context(
        config=_config(),
        case_id="BOPS-ANNOUNCEMENT-P0-B",
        branch_id="popup-announcement",
        requested_run_id=None,
        explicitly_approved=False,
        argv=["pytest.exe"],
        orig_argv=[],
        environ={},
    )
    assert result["run_id"] is None  # 禁止恢复固定manual-run回退。
    assert result["approved"] is False
    assert result["approval_source"] == "not-approved"


def test_explicit_approval_does_not_invent_missing_run_id() -> None:
    result = resolve_pycharm_run_context(
        config=_config(),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        requested_run_id=None,
        explicitly_approved=True,
        argv=["pytest.exe"],
        orig_argv=[],
        environ={},
    )
    assert result["run_id"] is None
    assert result["approved"] is True
    assert result["approval_source"] == "explicit-cli"


def test_explicit_cli_values_are_preserved() -> None:
    result = resolve_pycharm_run_context(
        config=_config(enabled=False),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        requested_run_id="RVI-EXPLICIT-001",
        explicitly_approved=True,
        argv=["pytest.exe"],
        orig_argv=[],
        environ={},
    )
    assert result["run_id"] == "RVI-EXPLICIT-001"
    assert result["approved"] is True
    assert result["execution_origin"] == "cli"


def test_old_versions_and_incomplete_policy_never_enable_pycharm(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    for config in (
        _config(schema_version="2.0"),
        _config(schema_version="2.1"),
        {"schema_version": "2.2", "scope": {"environment": "test"}},
    ):
        result = resolve_pycharm_run_context(
            config=config,
            case_id="BOPS-ANNOUNCEMENT-P0-A",
            branch_id="system-announcement",
            requested_run_id=None,
            explicitly_approved=False,
            argv=[str(runner)],
            orig_argv=[],
            environ={},
        )
        assert result["run_id"] is None
        assert result["approved"] is False


def test_v2_1_explicit_flag_cannot_restore_new_execution_approval() -> None:
    # 旧配置上的显式标志不得绕过transaction-v1迁移门禁。
    result = resolve_pycharm_run_context(
        config=_config(schema_version="2.1"),
        case_id="BOPS-ANNOUNCEMENT-P0-A",
        branch_id="system-announcement",
        requested_run_id="RVI-OLD-CONFIG-001",
        explicitly_approved=True,
        argv=["pytest.exe"],
        orig_argv=[],
        environ={},
    )
    assert result["run_id"] == "RVI-OLD-CONFIG-001"  # 标识保留用于诊断，但不产生批准。
    assert result["approved"] is False
    assert result["approval_source"] == "not-approved"


def test_non_test_environment_and_non_r2_risk_never_auto_approve(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    for config, risk in ((_config(environment="production"), "r2-ui-write-test"), (_config(), "r1-read-only-authenticated")):
        result = resolve_pycharm_run_context(
            config=config,
            case_id="BOPS-ANNOUNCEMENT-P0-A",
            branch_id="system-announcement",
            node_id="case.py::test_case",
            risk_level=risk,
            requested_run_id=None,
            explicitly_approved=False,
            argv=[str(runner)],
            orig_argv=[],
            environ={},
            unique_suffix="A1B2C3D4",
        )
        assert result["run_id"] is not None  # 合法PyCharm节点仍获得可追踪身份。
        assert result["approved"] is False


def test_runner_content_change_is_recorded_but_does_not_block_origin(tmp_path: Path) -> None:
    runner = _runner(tmp_path, "# first\n")
    first = classify_execution_origin(argv=[str(runner)], orig_argv=[], environ={})
    runner.write_text("# second\n", encoding="utf-8")
    second = classify_execution_origin(argv=[str(runner)], orig_argv=[], environ={})
    assert first["execution_origin"] == second["execution_origin"] == "pycharm"
    assert first["origin_evidence"]["runner_path_hash"] == second["origin_evidence"]["runner_path_hash"]
    assert first["origin_evidence"]["evidence_digest"] != second["origin_evidence"]["evidence_digest"]


def test_per_node_run_ids_remain_unique(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    common = {
        "config": _config(),
        "case_id": "BOPS-ANNOUNCEMENT-P0-A",
        "branch_id": "system-announcement",
        "node_id": "case.py::test_case",
        "requested_run_id": None,
        "explicitly_approved": False,
        "argv": [str(runner)],
        "orig_argv": [],
        "environ": {},
        "now": datetime(2026, 8, 28, 13, 5, 9),
    }
    first = resolve_pycharm_run_context(**common, unique_suffix="A1B2C3D4")
    second = resolve_pycharm_run_context(**common, unique_suffix="B1C2D3E4")
    assert first["run_id"] != second["run_id"]
