"""r2_project_lock 和 pytest插件R2锁集成的单元/集成测试。

覆盖：首个获取、第二进程冲突、释放后获取、子进程异常退出恢复、
R0/R1旁路、R3/xdist拒绝、teardown释放、context manager。
中文注释；不运行测试或输出敏感形状。
"""

import os
import sys
import textwrap
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]  # 启用pytester验证真实插件发现流程。

_SKILL_ROOT = Path(__file__).resolve().parents[1]  # pytester子进程需要显式导入候选Skill。


@pytest.fixture(autouse=True)
def _force_pytester_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONUTF8", "1")  # Windows子进程统一UTF-8输出。
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")


# ---------------------------------------------------------------------------
# 共用配置和conftest模板
# ---------------------------------------------------------------------------

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

    def pytest_ui_test_project_config_path():
        return str(pathlib.Path(__file__).parent / "ui-test.project.yaml")

    def pytest_ui_test_execution_evidence_root():
        return str(pathlib.Path(__file__).parent / "evidence")

    def pytest_addoption(parser):
        parser.addoption("--ui-pre-submit-only", action="store_true", default=False)
""")


def _write_pycharm_conftest(pytester: pytest.Pytester, config_yaml: str) -> None:
    """写入根conftest（加载插件、提供项目配置路径hook）和项目配置文件。"""
    conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
        import sys
        _runner = pathlib.Path(__file__).parent / "plugins" / "python-ce" / "helpers" / "pycharm" / "_jb_pytest_runner.py"
        _runner.parent.mkdir(parents=True)
        _runner.write_text("# runner\\n", encoding="utf-8")
        sys.argv[0] = str(_runner)
    """)
    pytester.makeconftest(conftest)
    (pytester.path / "ui-test.project.yaml").write_text(config_yaml, encoding="utf-8")


def _write_cli_conftest(pytester: pytest.Pytester, config_yaml: str) -> None:
    """写入CLI来源的conftest（不模拟PyCharm runner路径）。"""
    pytester.makeconftest(_PLUGIN_CONTEST)
    (pytester.path / "ui-test.project.yaml").write_text(config_yaml, encoding="utf-8")


# ===========================================================================
# 单元测试：R2ProjectLock 基础行为
# ===========================================================================

class TestR2ProjectLockUnit:
    # 锁名称派生和基础属性

    def test_lock_name_derived_from_scope(self) -> None:
        # 锁名称仅由project_group/product/environment的SHA-256派生
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="tianjin",
            product="bops-announcement",
            environment="test",
        )
        # 验证锁名称前缀和SHA-256长度
        assert lock.lock_name.startswith("Local\\UIT-R2-")
        assert len(lock.lock_name) == len("Local\\UIT-R2-") + 64

    def test_lock_name_case_insensitive(self) -> None:
        # 大小写不同的scope映射到同一锁名称
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock1 = R2ProjectLock(project_group="Tianjin", product="BOPS", environment="Test")
        lock2 = R2ProjectLock(project_group="tianjin", product="bops", environment="test")
        assert lock1.lock_name == lock2.lock_name

    def test_lock_name_different_scope(self) -> None:
        # 不同scope映射到不同锁名称
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock1 = R2ProjectLock(project_group="tianjin", product="bops", environment="test")
        lock2 = R2ProjectLock(project_group="beijing", product="bops", environment="test")
        assert lock1.lock_name != lock2.lock_name

    def test_lock_name_no_private_values(self) -> None:
        # 锁名称不含原始scope值
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="super_secret_group",
            product="super_secret_product",
            environment="super_secret_env",
        )
        assert "super_secret_group" not in lock.lock_name
        assert "super_secret_product" not in lock.lock_name
        assert "super_secret_env" not in lock.lock_name

    def test_invalid_scope_raises(self) -> None:
        # 空或非字符串scope必须失败
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock, R2ProjectLockError
        with pytest.raises(R2ProjectLockError):
            R2ProjectLock(project_group="", product="bops", environment="test")
        with pytest.raises(R2ProjectLockError):
            R2ProjectLock(project_group="tianjin", product="", environment="test")
        with pytest.raises(R2ProjectLockError):
            R2ProjectLock(project_group="tianjin", product="bops", environment="")

    def test_initial_state_not_held(self) -> None:
        # 新创建的锁对象初始状态为未持有
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(project_group="tianjin", product="bops", environment="test")
        assert not lock.is_held


# ===========================================================================
# 单元测试：acquire/release 行为（Windows平台）
# ===========================================================================

class TestAcquireRelease:
    # 首个获取、重复acquire、重复release

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_first_acquire_succeeds(self) -> None:
        # 首个进程获取锁成功
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="test-pg",
            product="test-prod",
            environment="test",
        )
        try:
            lock.acquire()
            assert lock.is_held
        finally:
            lock.release()

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_double_acquire_raises(self) -> None:
        # 同一锁对象重复acquire报E_R2_PROJECT_LOCK_HELD
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock, R2ProjectLockError
        lock = R2ProjectLock(
            project_group="test-pg2",
            product="test-prod",
            environment="test",
        )
        try:
            lock.acquire()
            with pytest.raises(R2ProjectLockError) as exc_info:
                lock.acquire()
            assert exc_info.value.code == "E_R2_PROJECT_LOCK_HELD"
        finally:
            lock.release()

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_release_allows_reacquire(self) -> None:
        # 释放后可以重新获取
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="test-pg3",
            product="test-prod",
            environment="test",
        )
        lock.acquire()
        lock.release()
        # 释放后应可重新获取
        lock.acquire()
        assert lock.is_held
        lock.release()

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_double_release_is_safe(self) -> None:
        # 重复release安全拒绝（幂等，不抛异常）
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="test-pg4",
            product="test-prod",
            environment="test",
        )
        lock.acquire()
        assert lock.release() is True
        assert lock.release() is False  # 重复release明确拒绝，不伪造已释放。
        assert lock.release() is False
        assert not lock.is_held

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_context_manager(self) -> None:
        # context manager正确获取和释放
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock
        lock = R2ProjectLock(
            project_group="test-pg5",
            product="test-prod",
            environment="test",
        )
        with lock:
            assert lock.is_held
        assert not lock.is_held

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_release_failure_is_not_reported_as_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ReleaseMutex失败必须保留held状态并上报，不能清stash后伪造完成。
        import scripts.ui_test_core.r2_project_lock as lock_module

        class FailingKernel32:
            @staticmethod
            def ReleaseMutex(handle):
                return 0

        lock = lock_module.R2ProjectLock(
            project_group="release-failure-pg",
            product="test-prod",
            environment="test",
        )
        lock._handle = 1
        lock._held = True
        monkeypatch.setattr(lock_module, "_kernel32", FailingKernel32())
        monkeypatch.setattr(lock_module.ctypes, "get_last_error", lambda: 288)

        with pytest.raises(lock_module.R2ProjectLockError) as exc_info:
            lock.release()
        assert exc_info.value.code == "E_R2_LOCK_RELEASE_FAILED:288"
        assert lock.is_held

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_second_process_conflict(self) -> None:
        # 子进程持锁并发出READY后，父进程的同scope获取必须立即失败。
        import subprocess
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock, R2ProjectLockError

        child_script = textwrap.dedent(f'''\
            import sys
            sys.path.insert(0, r"{_SKILL_ROOT}")
            from scripts.ui_test_core.r2_project_lock import R2ProjectLock
            lock = R2ProjectLock(project_group="conflict-pg", product="conflict-prod", environment="test")
            lock.acquire()
            print("READY", flush=True)
            sys.stdin.readline()
            lock.release()
        ''')
        child = subprocess.Popen(
            [sys.executable, "-c", child_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        lock2 = R2ProjectLock(project_group="conflict-pg", product="conflict-prod", environment="test")
        try:
            assert child.stdout is not None
            assert child.stdout.readline().strip() == "READY"
            with pytest.raises(R2ProjectLockError) as exc_info:
                lock2.acquire()
            assert exc_info.value.code == "E_R2_PROJECT_LOCK_HELD"
            assert not lock2.is_held
        finally:
            if child.stdin is not None:
                child.stdin.write("release\n")
                child.stdin.flush()
            stdout, stderr = child.communicate(timeout=30)
            assert child.returncode == 0, f"子进程退出失败: {stdout} {stderr}"


# ===========================================================================
# 单元测试：异常进程退出恢复
# ===========================================================================

class TestAbandonedRecovery:
    # 子进程异常退出后锁可恢复

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_abandoned_mutex_recoverable(self) -> None:
        # 子进程获取Mutex后异常退出（不release），父进程应能获取锁
        import subprocess
        from scripts.ui_test_core.r2_project_lock import R2ProjectLock

        # 使用唯一scope避免与其他测试冲突
        pg = "abandon-recovery-test"
        product = "test-prod"
        env = "test"

        # 子进程获取锁后直接退出（不release），模拟异常退出
        child_script = textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, r"{_SKILL_ROOT}")
            from scripts.ui_test_core.r2_project_lock import R2ProjectLock
            lock = R2ProjectLock(
                project_group="{pg}",
                product="{product}",
                environment="{env}",
            )
            lock.acquire()
            # 绕过析构直接结束进程，确保覆盖WAIT_ABANDONED而不是普通release。
            import os
            os._exit(0)
        """)
        result = subprocess.run(
            [sys.executable, "-c", child_script],
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, f"子进程异常退出: {result.stderr}"

        # 父进程应能获取同一scope的锁（WAIT_ABANDONED路径）
        lock = R2ProjectLock(
            project_group=pg,
            product=product,
            environment=env,
        )
        try:
            lock.acquire()
            assert lock.is_held
        finally:
            lock.release()


# ===========================================================================
# 单元测试：工厂函数
# ===========================================================================

class TestCreateFromConfig:

    def test_create_from_valid_config(self) -> None:
        # 从已验证配置创建锁
        from scripts.ui_test_core.r2_project_lock import create_r2_project_lock
        config = {
            "scope": {
                "project_group": "tianjin",
                "product": "bops-announcement",
                "environment": "test",
            }
        }
        lock = create_r2_project_lock(config=config)
        assert lock.lock_name.startswith("Local\\UIT-R2-")

    def test_create_from_config_missing_scope(self) -> None:
        # 缺少scope字段报E_R2_LOCK_SCOPE_REQUIRED
        from scripts.ui_test_core.r2_project_lock import create_r2_project_lock, R2ProjectLockError
        with pytest.raises(R2ProjectLockError) as exc_info:
            create_r2_project_lock(config={})
        assert exc_info.value.code == "E_R2_LOCK_SCOPE_REQUIRED"

    def test_create_from_config_invalid_scope(self) -> None:
        # scope字段不完整报E_R2_LOCK_SCOPE_INVALID
        from scripts.ui_test_core.r2_project_lock import create_r2_project_lock, R2ProjectLockError
        with pytest.raises(R2ProjectLockError):
            create_r2_project_lock(config={"scope": {"project_group": "tianjin"}})


# ===========================================================================
# 单元测试：xdist检测
# ===========================================================================

class TestXdistDetection:

    def test_no_xdist_env(self) -> None:
        # 无xdist环境变量时返回False
        from scripts.ui_test_core.r2_project_lock import detect_xdist_parallel
        assert not detect_xdist_parallel(environ={})

    def test_xdist_worker_env(self) -> None:
        # PYTEST_XDIST_WORKER存在时返回True
        from scripts.ui_test_core.r2_project_lock import detect_xdist_parallel
        assert detect_xdist_parallel(environ={"PYTEST_XDIST_WORKER": "gw0"})

    def test_xdist_worker_count_env(self) -> None:
        # PYTEST_XDIST_WORKER_COUNT存在时返回True
        from scripts.ui_test_core.r2_project_lock import detect_xdist_parallel
        assert detect_xdist_parallel(environ={"PYTEST_XDIST_WORKER_COUNT": "2"})

    def test_xdist_auto_option(self) -> None:
        # --numprocesses=auto不能因int转换失败而被误判为非并行。
        from scripts.ui_test_core.r2_project_lock import detect_xdist_parallel

        class Config:
            def getoption(self, name, default=None):
                return "auto" if name == "--numprocesses" else default

        assert detect_xdist_parallel(config=Config(), environ={})


# ===========================================================================
# 集成测试：pytest插件 R2锁生命周期
# ===========================================================================

class TestPluginR2LockLifecycle:
    # R2 item在fixture前获取锁，teardown释放

    def test_r2_acquires_and_releases_lock(self, pytester: pytest.Pytester) -> None:
        # R2 PyCharm来源item获取锁并在teardown后释放
        _write_pycharm_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_r2_lock=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-LOCK-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_r2_lock_acquire(ui_test_execution_context):
                # 锁应在fixture前获取；context可用即说明setup成功
                ctx = ui_test_execution_context
                assert ctx.risk_level == "r2-ui-write-test"
        """))
        result = pytester.runpytest_subprocess("--ui-pre-submit-only", "-v")
        # setup成功获取锁且fixture可用即说明集成工作
        result.assert_outcomes(passed=1, errors=0, failed=0)

    def test_r0_bypasses_lock(self, pytester: pytest.Pytester) -> None:
        # R0 item不获取锁
        _write_pycharm_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_r0=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-R0-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_r0_no_lock(ui_test_execution_context):
                # R0不获取锁，正常通过
                assert ui_test_execution_context.risk_level == "r0-read-only"
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)

    def test_r1_bypasses_lock(self, pytester: pytest.Pytester) -> None:
        # R1 item不获取锁
        _write_pycharm_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_r1=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-R1-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r1
            def test_r1_no_lock(ui_test_execution_context):
                assert ui_test_execution_context.risk_level == "r1-read-only-authenticated"
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)


class TestPluginR3Blocked:
    # R3 item在BrowserContext前报E_R3_BLOCKED

    def test_r3_blocked(self, pytester: pytest.Pytester) -> None:
        _write_pycharm_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_r3=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-R3-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r3
            def test_r3_blocked(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*E_R3_BLOCKED*"])


class TestPluginXdistForbidden:
    # xdist环境下R2并行在锁前报E_R2_PARALLEL_FORBIDDEN

    def test_xdist_r2_forbidden(self, pytester: pytest.Pytester) -> None:
        _write_cli_conftest(pytester, _V21_CONFIG_YAML)
        # 模拟xdist环境变量
        pytester.makepyfile(test_xdist=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-XDIST-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_xdist_r2(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess(
            "-v",
            "--ui-run-id", "UIT-XDIST-001",
            "--ui-r2-approved",
            "--ui-pre-submit-only",
        )
        # 在没有xdist环境变量的情况下应正常通过
        result.assert_outcomes(passed=1)

    def test_xdist_env_blocks_r2(self, pytester: pytest.Pytester) -> None:
        # 设置xdist环境变量后R2应被拒绝
        _write_cli_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_xdist_env=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-XDIST-ENV-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_xdist_env_r2(ui_test_execution_context):
                pass
        """))
        # 使用子进程环境变量模拟xdist
        # runpytest_subprocess继承当前环境，需要直接设置
        old_val = os.environ.get("PYTEST_XDIST_WORKER")
        os.environ["PYTEST_XDIST_WORKER"] = "gw0"
        try:
            result = pytester.runpytest_subprocess(
                "-v",
                "--ui-run-id", "UIT-XDIST-002",
                "--ui-r2-approved",
            )
        finally:
            if old_val is None:
                os.environ.pop("PYTEST_XDIST_WORKER", None)
            else:
                os.environ["PYTEST_XDIST_WORKER"] = old_val
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*E_R2_PARALLEL_FORBIDDEN*"])


class TestPluginTeardownRelease:
    # teardown正确释放锁

    @pytest.mark.skipif(
        sys.platform != "win32" and os.name != "nt",
        reason="Windows命名Mutex测试需要Windows平台",
    )
    def test_lock_released_after_test(self, pytester: pytest.Pytester) -> None:
        # R2测试完成后锁应释放；第二个测试可获取
        _write_pycharm_conftest(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_release=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-REL-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_release_first(ui_test_execution_context):
                pass

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-REL-002")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r2
            def test_release_second(ui_test_execution_context):
                pass
        """))
        result = pytester.runpytest_subprocess("--ui-pre-submit-only", "-v")
        # 两个R2测试都应通过：第一个释放后第二个可获取
        result.assert_outcomes(passed=2)
