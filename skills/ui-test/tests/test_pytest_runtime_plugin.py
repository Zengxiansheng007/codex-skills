"""pytest_runtime_plugin 的 pytester/fake item 测试。

覆盖：插件显式加载、普通测试无影响、每 node 独立上下文、marker 缺失/冲突、
v2.0 阻断、active mismatch（预留）、CLI 无 ID 和 PyCharm 来源。验证 --trace-config 能看到插件。
中文注释；不运行测试或输出敏感形状。
"""

import textwrap
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]  # 启用pytest官方pytester fixture验证真实插件发现流程。


@pytest.fixture(autouse=True)
def _force_pytester_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONUTF8", "1")  # Windows子进程统一使用UTF-8输出，避免本机代码页造成解码漂移。
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")

# ---------------------------------------------------------------------------
# 共用：构造 pytester conftest 和最小项目配置的辅助
# ---------------------------------------------------------------------------

_SKILL_ROOT = Path(__file__).resolve().parents[1]  # pytester子进程需要显式导入当前候选Skill。

_PLUGIN_CONTEST = textwrap.dedent(f"""\
    # 根 conftest：显式加载通用 pytest_runtime_plugin
    import sys
    sys.path.insert(0, r"{_SKILL_ROOT}")
    pytest_plugins = ("scripts.ui_test_core.pytest_runtime_plugin",)

    import pathlib

    def pytest_ui_test_stable_runner_root():
        return str(pathlib.Path(__file__).parent)

    def pytest_ui_test_active_identity_resolver():
        def resolver(seed):
            return {{
                "active_build_fingerprint": "sha256:" + "a" * 64,
                "active_attachment_digest": seed["stable_runner_digest"],
            }}
        return resolver

    def pytest_ui_test_execution_evidence_root():
        return str(pathlib.Path(__file__).parent / "evidence")
""")

_V21_CONFIG_YAML = textwrap.dedent("""\
    schema_version: "2.2"
    scope:
      project_group: tianjin
      project_group_name: 天津
      product: bops-announcement
      product_name: 公告管理
      environment: test
    asset_governance:
      execution_asset_root: "D:\\\\UI-Test"
      knowledge_root: "D:\\\\RAG"
      staging_root: "D:\\\\UI-Test\\\\_tmp"
      forbidden_persistent_roots: ['C:\\']
      layout_version: 1
      levels:
        - project_group
        - product
        - system
        - module_path
        - function
        - case
        - branch
        - run
      segment_naming: stable-id__display-name
      asset_type_policy_version: ui-test.asset-types.v1
    systems:
      - system_id: announcement
        display_name: 公告系统
        modules:
          - module_id: announcement-core
            display_name: 公告核心
            aliases: ["announcement"]
            module_path:
              - module_id: announcement-core
                display_name: 公告核心
            functions:
              - function_id: create-announcement
                display_name: 创建公告
            direct_route_ref: routes/announcement.yaml
    runtime_value_index_ref: "path:D:/UI-Test/_private/runtime-values/tianjin/bops-announcement/test/runtime-value-index.yaml"
    runtime_refs:
      base_url: "value:tianjin-test-base-url"
    checkpoint_runtime:
      root_ref: "checkpoints/announcement.yaml"
    knowledge_space:
      knowledge_space_id: tianjin-bops
      relative_path: "tianjin/bops-announcement"
    wait_strategy:
      strategy: visible
    semantic_post_signatures: []
    execution_policies: []
    credential_index_ref: "path:D:/UI-Test/_private/runtime-values/tianjin/bops-announcement/test/credential-index.yaml"
    pycharm_manual_execution:
      contract_version: 3
      origin_detection: jetbrains-runner-path
      entry_scope: stable-active-runners
      r2_authorization: auto-test-only
      run_scope: per-node
      r2_parallelism: serial-project-environment
      auto_generate_run_id: true
      auto_approve_r2_visible_ui: true
      finalization_contract: transaction-v1
      run_result_contract: v5
      session_result_contract: v1
      acceptance_contract: external-exit-v1
""")

_V20_CONFIG_YAML = textwrap.dedent("""\
    schema_version: "2.0"
    scope:
      project_group: tianjin
      project_group_name: 天津
      product: bops-announcement
      product_name: 公告管理
      environment: test
    asset_governance:
      execution_asset_root: "D:\\\\UI-Test"
      knowledge_root: "D:\\\\RAG"
      staging_root: "D:\\\\UI-Test\\\\_tmp"
      forbidden_persistent_roots: ['C:\\']
      layout_version: 1
      levels:
        - project_group
        - product
        - system
        - module_path
        - function
        - case
        - branch
        - run
      segment_naming: stable-id__display-name
      asset_type_policy_version: ui-test.asset-types.v1
    systems:
      - system_id: announcement
        display_name: 公告系统
        modules:
          - module_id: announcement-core
            display_name: 公告核心
            aliases: ["announcement"]
            module_path:
              - module_id: announcement-core
                display_name: 公告核心
            functions:
              - function_id: create-announcement
                display_name: 创建公告
            direct_route_ref: routes/announcement.yaml
    runtime_value_index_ref: "path:D:/UI-Test/_private/runtime-values/tianjin/bops-announcement/test/runtime-value-index.yaml"
    runtime_refs:
      base_url: "value:tianjin-test-base-url"
    checkpoint_runtime:
      root_ref: "checkpoints/announcement.yaml"
    knowledge_space:
      knowledge_space_id: tianjin-bops
      relative_path: "tianjin/bops-announcement"
    wait_strategy:
      strategy: visible
    semantic_post_signatures: []
    execution_policies: []
    credential_index_ref: "path:D:/UI-Test/_private/runtime-values/tianjin/bops-announcement/test/credential-index.yaml"
""")


def _write_conftest_with_config(pytester: pytest.Pytester, config_yaml: str) -> None:
    """写入根 conftest（加载插件并提供项目配置路径 hook）和项目配置文件。"""
    conftest = _PLUGIN_CONTEST + textwrap.dedent(f"""\
        import pathlib

        def pytest_ui_test_project_config_path():
            return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")
    """)
    pytester.makeconftest(conftest)
    (pytester.path / "ui-test.project.yaml").write_text(config_yaml, encoding="utf-8")  # 保持hook声明的精确文件名。


def _write_pycharm_conftest_with_config(pytester: pytest.Pytester, config_yaml: str) -> None:
    """让pytester子进程通过真实存在的JetBrains runner结构进入PyCharm来源。"""

    conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
        import os
        import sys

        _runner = pathlib.Path(__file__).parent / "plugins" / "python-ce" / "helpers" / "pycharm" / "_jb_pytest_runner.py"
        _runner.parent.mkdir(parents=True)
        _runner.write_text("# runner\\n", encoding="utf-8")
        sys.argv[0] = "pytest"
        sys.orig_argv = ["python.exe", "-m", "pytest"]
        sys.modules["__main__"].__file__ = "pytest"
        import scripts.ui_test_core.pycharm_runtime as pycharm_runtime
        pycharm_runtime._windows_process_argv = lambda: ("python.exe", str(_runner), "--path", "case.py")  # 复现只有Windows原始进程命令行保留runner的最深改写形态。
        os.environ["TEAMCITY_VERSION"] = "LOCAL"  # PyCharm helper用于TeamCity消息格式的本地传输标记不得覆盖精确runner。

        def pytest_addoption(parser):
            parser.addoption("--ui-pre-submit-only", action="store_true", default=False)

        def pytest_ui_test_project_config_path():
            return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")
    """)
    pytester.makeconftest(conftest)
    (pytester.path / "ui-test.project.yaml").write_text(config_yaml, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. 插件显式加载与 --trace-config 可见
# ---------------------------------------------------------------------------

class TestPluginExplicitLoad:
    # 插件必须能通过根 conftest 的 pytest_plugins 显式加载

    def test_trace_config_shows_plugin(self, pytester: pytest.Pytester) -> None:
        # --trace-config 必须看到 pytest_runtime_plugin
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_dummy="def test_dummy(): pass")
        result = pytester.runpytest_subprocess("--trace-config")
        result.stdout.fnmatch_lines(["*pytest_runtime_plugin*"])

    def test_plugin_adds_options(self, pytester: pytest.Pytester) -> None:
        # --help 必须显示三个 --ui- 参数
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        result = pytester.runpytest_subprocess("--help")
        result.stdout.fnmatch_lines(["*--ui-run-id*", "*--ui-r2-approved*", "*--ui-execution-origin*"])


# ---------------------------------------------------------------------------
# 2. 普通 pytest 用例不受影响
# ---------------------------------------------------------------------------

class TestNormalTestsNotAffected:
    # 非 ui_test 用例不被插件影响，正常通过

    def test_plain_test_passes_without_ui_markers(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_plain="def test_plain(): assert True")
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# 3. 每 node 独立上下文
# ---------------------------------------------------------------------------

class TestPerNodeContext:
    # 每个 ui_test item 获得独立的 ExecutionContextV3

    def test_two_nodes_get_distinct_contexts(self, pytester: pytest.Pytester) -> None:
        _write_pycharm_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_nodes=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_node_a(ui_test_execution_context):
                ctx = ui_test_execution_context
                assert ctx.case_id == "CASE-A"
                assert ctx.risk_level == "r0-read-only"
                assert ctx.schema_version == "ui-test.execution-context.v3"

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-B")
            @pytest.mark.branch_id("BRANCH-B")
            @pytest.mark.r0
            def test_node_b(ui_test_execution_context):
                ctx = ui_test_execution_context
                assert ctx.case_id == "CASE-B"
                assert ctx.node_id != ""
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=2)


# ---------------------------------------------------------------------------
# 4. Marker 缺失/冲突在 BrowserContext 前失败
# ---------------------------------------------------------------------------

class TestMarkerValidation:
    # 缺失 case_id、branch_id 或 risk marker 必须失败

    def test_missing_case_id_fails(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_missing_case=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_missing_case():
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)

    def test_missing_branch_id_fails(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_missing_branch=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.r2
            def test_missing_branch():
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)

    def test_missing_risk_marker_fails(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_missing_risk=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            def test_missing_risk():
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)

    def test_conflicting_risk_markers_fails(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_conflict_risk=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            @pytest.mark.r3
            def test_conflict_risk():
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)


# ---------------------------------------------------------------------------
# 5. v2.0 配置阻断
# ---------------------------------------------------------------------------

class TestV20Blocked:
    # v2.0 项目配置不得通过执行门禁

    def test_v2_0_config_blocks_ui_test(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V20_CONFIG_YAML)
        pytester.makepyfile(test_v20=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_v20(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)


# ---------------------------------------------------------------------------
# 6. CLI 无 Run ID 时不自动授权
# ---------------------------------------------------------------------------

class TestCliNoRunId:
    # CLI 来源且无 --ui-run-id 时必须在测试执行前失败

    def test_cli_without_run_id_not_approved(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_cli=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_cli_no_run_id(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*E_FORMAL_RUN_ID_REQUIRED*"])

    def test_cli_with_explicit_run_id_approved(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_cli_explicit=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_cli_explicit_run_id(ui_test_execution_context):
                ctx = ui_test_execution_context
                assert ctx.run_id == "RVI-EXPLICIT-001"
                assert ctx.approved is True
                assert ctx.approval_source == "explicit-cli"
        """))
        result = pytester.runpytest_subprocess("--ui-run-id", "RVI-EXPLICIT-001", "--ui-r2-approved", "-v")
        result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# 7. PyCharm 来源（通过真实存在的JetBrains runner结构模拟）
# ---------------------------------------------------------------------------

class TestPycharmSource:
    # PyCharm 来源且 v2.2 策略匹配时自动生成 Run ID 和候选批准

    def test_pycharm_origin_auto_generates_run_id(self, pytester: pytest.Pytester) -> None:
        _write_pycharm_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_pycharm=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_pycharm_auto(ui_test_execution_context):
                ctx = ui_test_execution_context
                assert ctx.execution_origin == "pycharm"
                assert ctx.run_id is not None
                assert ctx.approved is True
                assert ctx.approval_source == "pycharm-project-policy"
                assert ctx.environment == "test"
                assert ctx.config_summary is not None
                assert ctx.config_summary["schema_version"] == "2.2"
                assert ctx.config_summary["contract_version"] == 3
                assert ctx.finalization_contract == "transaction-v1"
                assert ctx.project_config_digest is not None
                assert ctx.attempt_ref.startswith("attempts/")  # 引用与ST-006实际append-only目录一致。
        """))
        result = pytester.runpytest_subprocess("--ui-pre-submit-only", "-v")
        result.assert_outcomes(passed=1)


# ---------------------------------------------------------------------------
# 8. Active mismatch 在BrowserContext前失败
# ---------------------------------------------------------------------------

class TestActiveMismatchBoundary:
    # active attachment必须与当前stable runner摘要一致

    def test_active_mismatch_fails_before_fixture(self, pytester: pytest.Pytester) -> None:
        conftest_with_resolver = _PLUGIN_CONTEST + textwrap.dedent("""\
            def pytest_ui_test_project_config_path():
                return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

            def pytest_ui_test_active_identity_resolver():
                def resolver(seed):
                    return {
                        "active_build_fingerprint": "sha256:" + "a" * 64,
                        "active_attachment_digest": "sha256:" + "b" * 64,
                    }
                return resolver
        """)
        pytester.makeconftest(conftest_with_resolver)
        (pytester.path / "ui-test.project.yaml").write_text(_V21_CONFIG_YAML, encoding="utf-8")
        pytester.makepyfile(test_active=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_active_values(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess("--ui-run-id", "RVI-EXPLICIT-001", "--ui-r2-approved", "-v")
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*E_PYCHARM_ENTRY_NOT_STABLE_ACTIVE*"])


# ---------------------------------------------------------------------------
# 9. 零提交qualification不得进入正式RunResult finalizer
# ---------------------------------------------------------------------------

class TestQualificationFinalizerBoundary:
    def _write_finalizer_probe(self, pytester: pytest.Pytester) -> None:
        """安装会显式失败的finalizer，用于证明qualification是否错误调用。"""
        conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
            def pytest_ui_test_project_config_path():
                return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

            def pytest_addoption(parser):
                parser.addoption("--ui-pre-submit-only", action="store_true", default=False)

            def pytest_ui_test_finalize_run_result_v4(*, run_id, node_id, attempt_store):
                raise RuntimeError("E_FINALIZER_MUST_NOT_RUN_FOR_QUALIFICATION")
        """)
        pytester.makeconftest(conftest)
        (pytester.path / "ui-test.project.yaml").write_text(_V21_CONFIG_YAML, encoding="utf-8")
        pytester.makepyfile(test_qualification=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_qualification(ui_test_execution_context):
                assert ui_test_execution_context.approved is True
        """))

    def test_pre_submit_skips_formal_run_result_finalizer(self, pytester: pytest.Pytester) -> None:
        """qualification保留attempt/terminal，但不得要求正式run的approval/pending。"""
        self._write_finalizer_probe(pytester)
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "QUAL-FINALIZER-001", "--ui-r2-approved", "--ui-pre-submit-only", "-v"
        )
        result.assert_outcomes(passed=1)
        assert "E_FINALIZER_MUST_NOT_RUN_FOR_QUALIFICATION" not in result.stdout.str()
        attempt = next((pytester.path / "evidence" / "attempts").iterdir())
        start = __import__("json").loads((attempt / "attempt-start.json").read_text(encoding="utf-8"))
        terminal = __import__("json").loads((attempt / "terminal.json").read_text(encoding="utf-8"))
        assert start["finalization_mode"] == "not_applicable_qualification"
        assert terminal["status"] == "passed"
        assert not list(pytester.path.glob("**/finalization-commit.json"))
        assert not list(pytester.path.glob("**/finalization-receipt.json"))
        session_path = next((pytester.path / "evidence" / "sessions").glob("*.json"))
        session = __import__("json").loads(session_path.read_text(encoding="utf-8"))
        assert session["pytest_exitstatus"] == 0
        assert session["nodes"][0]["finalization_status"] == "not_applicable_qualification"


class TestInvalidFinalizationCandidate:
    _write_finalizer_probe = TestQualificationFinalizerBoundary._write_finalizer_probe

    def test_missing_target_uses_attempt_local_failure_receipt(self, pytester: pytest.Pytester) -> None:
        _write_conftest_with_config(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_missing_target=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-TARGET")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_missing_target(ui_test_execution_context):
                assert ui_test_execution_context.approved is True
        """))
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "RUN-TARGET-001", "--ui-r2-approved", "-v"
        )
        result.assert_outcomes(passed=1, errors=1)
        attempt = next((pytester.path / "evidence" / "attempts").iterdir())
        receipt = attempt / "finalization-failure-receipt.json"
        assert receipt.is_file()
        assert "E_FINALIZATION_TARGET_REQUIRED" in result.stdout.str()

    def test_oserror_crosses_receipt_terminal_session_and_longrepr(self, pytester: pytest.Pytester) -> None:
        conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
            def pytest_ui_test_project_config_path():
                return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

            def pytest_ui_test_finalization_target_v1(run_id, node_id, attempt_store):
                return {"run_root": str(pathlib.Path(__file__).parent / "oserror-run")}

            def pytest_ui_test_build_finalization_candidate_v1(
                run_id, node_id, transaction_id, pre_terminal_events_hash,
                pytest_phase_status, attempt_store
            ):
                raise OSError("synthetic finalizer io failure")
        """)
        pytester.makeconftest(conftest)
        (pytester.path / "ui-test.project.yaml").write_text(_V21_CONFIG_YAML, encoding="utf-8")
        pytester.makepyfile(test_oserror=textwrap.dedent("""\
            import pytest
            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-OSERROR")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_oserror(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "RUN-OSERROR-001", "--ui-r2-approved", "-v"
        )
        result.assert_outcomes(passed=1, errors=1)
        assert "OSError; message_digest=sha256:" in result.stdout.str()
        attempt = next((pytester.path / "evidence" / "attempts").iterdir())
        terminal = __import__("json").loads((attempt / "terminal.json").read_text(encoding="utf-8"))
        assert terminal["status"] == "error"
        receipt = __import__("json").loads(
            (pytester.path / "oserror-run" / "finalization" / "finalization-receipt.json").read_text(encoding="utf-8")
        )
        assert receipt["status"] == "failed" and receipt["exception_class"] == "OSError"
        session = __import__("json").loads(
            next((pytester.path / "evidence" / "sessions").glob("*.json")).read_text(encoding="utf-8")
        )
        assert session["session_status"] == "failed" and session["pytest_exitstatus"] == 1

    def test_finalization_runs_after_other_makereport_wrapper_post_yield(self, pytester: pytest.Pytester) -> None:
        conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
            import pytest

            def pytest_ui_test_project_config_path():
                return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

            @pytest.hookimpl(hookwrapper=True, trylast=True)
            def pytest_runtest_makereport(item, call):
                outcome = yield
                if call.when == "teardown":
                    (pathlib.Path(__file__).parent / "wrapper-post-yield.done").write_text("done", encoding="utf-8")

            def pytest_ui_test_finalization_target_v1(run_id, node_id, attempt_store):
                return {"run_root": str(pathlib.Path(__file__).parent / "wrapper-run")}

            def pytest_ui_test_build_finalization_candidate_v1(
                run_id, node_id, transaction_id, pre_terminal_events_hash,
                pytest_phase_status, attempt_store
            ):
                marker = pathlib.Path(__file__).parent / "wrapper-post-yield.done"
                if not marker.is_file():
                    raise RuntimeError("E_WRAPPER_POST_YIELD_NOT_FINISHED")
                raise RuntimeError("E_WRAPPER_POST_YIELD_CONFIRMED")
        """)
        pytester.makeconftest(conftest)
        (pytester.path / "ui-test.project.yaml").write_text(_V21_CONFIG_YAML, encoding="utf-8")
        pytester.makepyfile(test_wrapper=textwrap.dedent("""\
            import pytest
            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-WRAPPER")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_wrapper(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "RUN-WRAPPER-001", "--ui-r2-approved", "-v"
        )
        result.assert_outcomes(passed=1, errors=1)
        assert "E_WRAPPER_POST_YIELD_CONFIRMED" in result.stdout.str()
        assert "E_WRAPPER_POST_YIELD_NOT_FINISHED" not in result.stdout.str()
    @pytest.mark.parametrize("candidate_expression", ["None", "[]", "{}"])
    def test_invalid_candidate_has_error_terminal_receipt_and_longrepr(
        self, pytester: pytest.Pytester, candidate_expression: str
    ) -> None:
        conftest = _PLUGIN_CONTEST + textwrap.dedent(f"""\
            def pytest_ui_test_project_config_path():
                return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

            def pytest_ui_test_finalization_target_v1(run_id, node_id, attempt_store):
                return {{"run_root": str(pathlib.Path(__file__).parent / "synthetic-run")}}

            def pytest_ui_test_build_finalization_candidate_v1(
                run_id, node_id, transaction_id, pre_terminal_events_hash,
                pytest_phase_status, attempt_store
            ):
                return {candidate_expression}
        """)
        pytester.makeconftest(conftest)
        (pytester.path / "ui-test.project.yaml").write_text(_V21_CONFIG_YAML, encoding="utf-8")
        pytester.makepyfile(test_invalid_candidate=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-CANDIDATE")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_invalid_candidate(ui_test_execution_context):
                assert ui_test_execution_context.approved is True
        """))
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "RUN-CANDIDATE-001", "--ui-r2-approved", "-v"
        )
        result.assert_outcomes(passed=1, errors=1)
        assert "message_digest=sha256:" in result.stdout.str()
        terminal = next((pytester.path / "evidence" / "attempts").glob("*/terminal.json"))
        assert __import__("json").loads(terminal.read_text(encoding="utf-8"))["status"] == "error"
        receipt = pytester.path / "synthetic-run" / "finalization" / "finalization-receipt.json"
        assert receipt.is_file()

    def test_normal_run_still_calls_formal_run_result_finalizer(self, pytester: pytest.Pytester) -> None:
        """普通正式run继续fail closed，避免qualification修复削弱RunResult门禁。"""
        self._write_finalizer_probe(pytester)
        result = pytester.runpytest_subprocess(
            "--ui-run-id", "RUN-FINALIZER-001", "--ui-r2-approved", "-v"
        )
        result.assert_outcomes(passed=1, errors=1)

    def test_failed_call_keeps_original_failure_without_success_finalizer_error(self, pytester: pytest.Pytester) -> None:
        """失败terminal不具备成功pending，必须保留原失败且不追加teardown错误。"""
        self._write_finalizer_probe(pytester)
        (pytester.path / "test_qualification.py").write_text(textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-A")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_qualification(ui_test_execution_context):
                raise RuntimeError("E_SYNTHETIC_ORIGINAL_CALL_FAILURE")
        """), encoding="utf-8")
        result = pytester.runpytest_subprocess("--ui-run-id", "RUN-FAILED-001", "--ui-r2-approved", "-v")
        result.assert_outcomes(failed=1)
        assert "E_FINALIZER_MUST_NOT_RUN_FOR_QUALIFICATION" not in result.stdout.str()
