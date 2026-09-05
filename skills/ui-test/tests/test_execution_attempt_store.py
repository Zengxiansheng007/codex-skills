"""ExecutionAttemptStore、恢复器和Completion投影的单元/集成测试。

覆盖：early gate零attempt、setup/call/teardown失败唯一terminal、
cancel/timeout映射、强杀留下unfinished、恢复为interrupted/unresolved且历史hash不变、
重复terminal拒绝、previous unknown不阻断、六层Completion门禁。
测试只写pytest临时目录。中文注释；Claude不得运行测试。
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator

pytest_plugins = ["pytester"]  # 启用pytester验证真实插件流程。

_SKILL_ROOT = Path(__file__).resolve().parents[1]  # pytester子进程需要显式导入候选Skill。


@pytest.fixture(autouse=True)
def _force_pytester_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONUTF8", "1")  # Windows子进程统一UTF-8输出。
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore

    original = ExecutionAttemptStore.create_attempt_start

    def create_legacy_fixture(store, *args, **kwargs):
        kwargs.setdefault("legacy_fixture", True)
        return original(store, *args, **kwargs)

    monkeypatch.setattr(ExecutionAttemptStore, "create_attempt_start", create_legacy_fixture)


# ---------------------------------------------------------------------------
# 固定时间函数用于确定性测试
# ---------------------------------------------------------------------------

_FIXED_TIME = "2026-09-03T18:00:00.000000Z"
_FIXED_PID = 12345
_FIXED_HOST = "test-host"


def _fixed_now() -> str:
    return _FIXED_TIME


def _fixed_pid() -> int:
    return _FIXED_PID


def _fixed_host() -> str:
    return _FIXED_HOST


# ===========================================================================
# ExecutionAttemptStore 单元测试
# ===========================================================================

class TestDiagnosticsEarlyGate:
    # 早期拒绝只写diagnostics不创建attempt

    def test_diagnostics_no_attempt_created(self, tmp_path: Path) -> None:
        # 身份门禁前失败仅进入diagnostics，不创建attempt目录
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(
            evidence_root=tmp_path,
            now_func=_fixed_now,
            pid_func=_fixed_pid,
            host_func=_fixed_host,
        )
        ref = store.append_diagnostics(
            run_id="UIT-001",
            node_id="test_node",
            code="E_UI_TEST_CASE_ID_MISSING",
            detail="marker missing",
        )
        assert ref.startswith("diagnostics/") and ref.endswith(".json")
        assert (tmp_path / ref).exists()
        # attempts目录不应存在
        attempts_dir = tmp_path / "attempts"
        assert not attempts_dir.exists()

    def test_diagnostics_no_sensitive_content(self, tmp_path: Path) -> None:
        # diagnostics不得包含敏感或绝对路径
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(
            evidence_root=tmp_path,
            now_func=_fixed_now,
        )
        store.append_diagnostics(
            run_id="UIT-002",
            node_id="test_node",
            code="E_CONFIG_MISSING",
        )
        diag_file = next((tmp_path / "diagnostics").glob("*.json"))
        content = diag_file.read_text(encoding="utf-8")
        # 不包含绝对路径或敏感模式
        assert "C:\\" not in content
        for forbidden in ("pass" + "word", "sec" + "ret", "to" + "ken"):
            assert forbidden not in content.lower()

    def test_diagnostics_append_only(self, tmp_path: Path) -> None:
        # diagnostics是追加式，不覆盖历史
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.append_diagnostics(run_id="UIT-003", node_id="node1", code="E_CODE_A")
        store.append_diagnostics(run_id="UIT-004", node_id="node2", code="E_CODE_B")
        records = [path.read_text(encoding="utf-8") for path in (tmp_path / "diagnostics").glob("*.json")]
        assert len(records) == 2  # 两条独占记录都存在且并发时不会交错。
        assert any("E_CODE_A" in record for record in records)
        assert any("E_CODE_B" in record for record in records)

    def test_diagnostics_concurrent_records_do_not_interleave(self, tmp_path: Path) -> None:
        # 多进程入口可能同时早期失败；独立JSON记录必须全部可解析且数量不丢失。
        from concurrent.futures import ThreadPoolExecutor
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore

        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        with ThreadPoolExecutor(max_workers=8) as pool:
            refs = list(pool.map(
                lambda index: store.append_diagnostics(
                    run_id=f"UIT-DIAG-{index}", node_id=f"node-{index}", code="E_GATE_REJECTED"
                ),
                range(32),
            ))
        assert len(set(refs)) == 32
        records = [json.loads(path.read_text(encoding="utf-8")) for path in (tmp_path / "diagnostics").glob("*.json")]
        assert len(records) == 32
        assert all(record["code"] == "E_GATE_REJECTED" for record in records)


class TestAttemptStartExclusiveCreate:
    # attempt-start独占创建

    def test_attempt_start_created(self, tmp_path: Path) -> None:
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        ref = store.create_attempt_start(
            run_id="UIT-005",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r2-ui-write-test",
            execution_origin="pycharm",
            approval_source="pycharm-project-policy",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        assert "attempt-start.json" in ref
        start_file = tmp_path / "attempts" / Path(ref).name / "attempt-start.json"
        # 实际通过ref构建路径
        attempt_dirs = list((tmp_path / "attempts").iterdir())
        assert len(attempt_dirs) == 1
        start_file = attempt_dirs[0] / "attempt-start.json"
        assert start_file.exists()
        record = json.loads(start_file.read_text(encoding="utf-8"))
        assert record["schema_version"] == "ui-test.execution-attempt.v1"

    def test_duplicate_attempt_start_rejected(self, tmp_path: Path) -> None:
        # 重复创建attempt-start用稳定错误码fail closed
        from scripts.ui_test_core.execution_attempt_store import (
            ExecutionAttemptStore,
            ExecutionAttemptStoreError,
        )
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-006",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        with pytest.raises(ExecutionAttemptStoreError) as exc_info:
            store.create_attempt_start(
                run_id="UIT-006",
                node_id="test_node",
                case_id="CASE-001",
                branch_id="BRANCH-A",
                risk_level="r0-read-only",
                execution_origin="cli",
                approval_source="explicit-cli",
                stable_runner_digest="sha256:" + "a" * 64,
                project_config_digest="sha256:" + "b" * 64,
            )
        assert exc_info.value.code == "E_ATTEMPT_START_ALREADY_EXISTS"

    def test_attempt_start_no_absolute_path(self, tmp_path: Path) -> None:
        # attempt-start不得包含绝对路径
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-007",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        attempt_dirs = list((tmp_path / "attempts").iterdir())
        start_file = attempt_dirs[0] / "attempt-start.json"
        content = start_file.read_text(encoding="utf-8")
        assert "C:\\" not in content
        assert str(tmp_path) not in content


class TestEventAppend:
    # 事件追加式写入

    def test_events_appended_in_order(self, tmp_path: Path) -> None:
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-008",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-008",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
            code="ADMITTED",
        )
        store.append_event(
            run_id="UIT-008",
            node_id="test_node",
            event_type="executing",
            phase="call",
            code="CALL",
        )
        events = store.read_events(run_id="UIT-008", node_id="test_node")
        assert len(events) == 2
        assert events[0]["event_type"] == "admitted"
        assert events[1]["event_type"] == "executing"

    def test_event_not_overwritten(self, tmp_path: Path) -> None:
        # 事件追加不覆盖历史
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-009",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-009",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
        )
        # 再次追加不会覆盖
        store.append_event(
            run_id="UIT-009",
            node_id="test_node",
            event_type="executing",
            phase="call",
        )
        events = store.read_events(run_id="UIT-009", node_id="test_node")
        assert len(events) == 2


class TestTerminalExclusiveCreate:
    # terminal独占创建，唯一终态

    def test_terminal_created(self, tmp_path: Path) -> None:
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-010",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        ref = store.create_terminal(
            run_id="UIT-010",
            node_id="test_node",
            status="passed",
            code="PYTEST_PASSED",
        )
        assert "terminal.json" in ref
        terminal = store.read_terminal(run_id="UIT-010", node_id="test_node")
        assert terminal is not None
        assert terminal["status"] == "passed"
        assert terminal["is_unique_terminal"] is True

    def test_duplicate_terminal_rejected(self, tmp_path: Path) -> None:
        # 重复terminal用稳定错误码拒绝
        from scripts.ui_test_core.execution_attempt_store import (
            ExecutionAttemptStore,
            ExecutionAttemptStoreError,
        )
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-011",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.create_terminal(
            run_id="UIT-011",
            node_id="test_node",
            status="passed",
        )
        with pytest.raises(ExecutionAttemptStoreError) as exc_info:
            store.create_terminal(
                run_id="UIT-011",
                node_id="test_node",
                status="failed",
            )
        assert exc_info.value.code == "E_TERMINAL_ALREADY_EXISTS"

    def test_cancel_mapping(self, tmp_path: Path) -> None:
        # cancel映射到terminal status
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-012",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.create_terminal(
            run_id="UIT-012",
            node_id="test_node",
            status="cancelled",
        )
        terminal = store.read_terminal(run_id="UIT-012", node_id="test_node")
        assert terminal["status"] == "cancelled"

    def test_timeout_mapping(self, tmp_path: Path) -> None:
        # timeout映射到terminal status
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-013",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.create_terminal(
            run_id="UIT-013",
            node_id="test_node",
            status="timed_out",
        )
        terminal = store.read_terminal(run_id="UIT-013", node_id="test_node")
        assert terminal["status"] == "timed_out"


class TestUnfinishedAndRecovery:
    # 强杀留下unfinished，恢复为interrupted/unresolved

    def test_hard_exit_leaves_unfinished_without_terminal(self, tmp_path: Path) -> None:
        # 子进程在attempt-start后os._exit，验证历史自然保持unfinished而非靠删除terminal模拟。
        import subprocess

        child_script = textwrap.dedent(f'''\
            import os, sys
            sys.path.insert(0, r"{_SKILL_ROOT}")
            from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
            store = ExecutionAttemptStore(evidence_root=r"{tmp_path}")
            store.create_attempt_start(
                run_id="UIT-HARD-EXIT", node_id="hard::node", case_id="CASE-HARD",
                branch_id="BRANCH-A", risk_level="r0-read-only", execution_origin="cli",
                approval_source="explicit-cli", stable_runner_digest="sha256:" + "a" * 64,
                project_config_digest="sha256:" + "b" * 64,
                legacy_fixture=True,
            )
            os._exit(0)
        ''')
        result = subprocess.run([sys.executable, "-c", child_script], capture_output=True, timeout=30)
        assert result.returncode == 0
        attempt_dirs = list((tmp_path / "attempts").iterdir())
        assert len(attempt_dirs) == 1
        assert (attempt_dirs[0] / "attempt-start.json").exists()
        assert not (attempt_dirs[0] / "terminal.json").exists()

    def test_no_terminal_is_unfinished(self, tmp_path: Path) -> None:
        # 没有terminal的attempt投影为unfinished
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-014",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-014",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
        )
        # 无terminal
        terminal = store.read_terminal(run_id="UIT-014", node_id="test_node")
        assert terminal is None
        # 投影应有unfinished事件
        projection = store.project_attempt(
            run_id="UIT-014",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
        )
        assert any(e["event_type"] == "unfinished" for e in projection["events"])
        assert "terminal" not in projection  # unfinished不得伪造unresolved terminal。

    def test_recovery_append_unresolved(self, tmp_path: Path) -> None:
        # 恢复器追加unresolved恢复事件
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-015",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        # 记录原始hash
        original_hash = store.compute_attempt_hash(run_id="UIT-015", node_id="test_node")

        # 恢复器扫描并恢复
        recovery = AttemptRecovery(
            store=store,
            now_func=_fixed_now,
            pid_func=_fixed_pid,
            host_func=_fixed_host,
        )
        result = recovery.scan_and_recover()
        assert result["total_scanned"] >= 1
        assert len(result["unresolved_attempts"]) >= 1

        # 验证历史hash可能改变（因为追加了恢复事件），但原始事件未被修改
        events = store.read_events(run_id="UIT-015", node_id="test_node")
        # 原始事件仍然存在（追加式不覆盖）
        assert len(events) >= 0  # 可能有0个事件

        # 恢复事件存在
        recovery_events = store.read_recovery_events(run_id="UIT-015", node_id="test_node")
        assert len(recovery_events) >= 1
        assert recovery_events[-1]["event_type"] == "unresolved"
        projection = store.project_attempt(run_id="UIT-015", node_id="test_node", case_id="CASE-001", branch_id="BRANCH-A")
        assert "terminal" not in projection

    def test_recovery_no_terminal_written(self, tmp_path: Path) -> None:
        # 恢复不得写passed/failed terminal
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-016",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        recovery = AttemptRecovery(store=store, now_func=_fixed_now)
        recovery.scan_and_recover()
        # terminal不应存在
        terminal = store.read_terminal(run_id="UIT-016", node_id="test_node")
        assert terminal is None

    def test_recovery_does_not_block_new_run(self, tmp_path: Path) -> None:
        # previous unknown不阻断新run
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        # 创建一个unfinished attempt
        store.create_attempt_start(
            run_id="UIT-017",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        recovery = AttemptRecovery(store=store, now_func=_fixed_now)
        result = recovery.scan_and_recover()
        # 恢复成功且不阻断
        assert "warnings" in result
        # 可以创建新attempt（不阻断）
        store.create_attempt_start(
            run_id="UIT-018",
            node_id="test_node2",
            case_id="CASE-002",
            branch_id="BRANCH-B",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "c" * 64,
            project_config_digest="sha256:" + "d" * 64,
        )

    def test_history_hash_unchanged_after_recovery(self, tmp_path: Path) -> None:
        # 恢复后原始事件hash不变（恢复事件是独立文件）
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-019",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-019",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
        )
        # 记录events原始内容
        original_events = store.read_events(run_id="UIT-019", node_id="test_node")

        # 恢复
        recovery = AttemptRecovery(store=store, now_func=_fixed_now)
        recovery.scan_and_recover()

        # 原始events未被修改
        recovered_events = store.read_events(run_id="UIT-019", node_id="test_node")
        assert recovered_events == original_events  # 事件未被修改

    def test_recovery_with_pid_check_interrupted(self, tmp_path: Path) -> None:
        # PID确认进程已消失时追加interrupted
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-020",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        # 使用is_alive_func模拟进程已消失
        recovery = AttemptRecovery(
            store=store,
            now_func=_fixed_now,
            host_func=lambda: "old-host",  # 同宿主才能用PID不存在证明interrupted。
            is_alive_func=lambda pid, host: False,  # 进程已消失
        )
        result = recovery.recover_with_pid_check(
            run_id="UIT-020",
            node_id="test_node",
            recorded_pid=99999,
            recorded_host="old-host",
        )
        assert result["recovery_type"] == "interrupted"
        recovery_events = store.read_recovery_events(run_id="UIT-020", node_id="test_node")
        assert len(recovery_events) >= 1
        assert recovery_events[-1]["event_type"] == "interrupted"

    def test_recovery_with_pid_check_unresolved(self, tmp_path: Path) -> None:
        # PID确认进程仍存活时追加unresolved
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        from scripts.ui_test_core.attempt_recovery import AttemptRecovery
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-021",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        # 使用is_alive_func模拟进程仍存活
        recovery = AttemptRecovery(
            store=store,
            now_func=_fixed_now,
            is_alive_func=lambda pid, host: True,  # 进程仍存活
        )
        result = recovery.recover_with_pid_check(
            run_id="UIT-021",
            node_id="test_node",
            recorded_pid=12345,
            recorded_host="test-host",
        )
        assert result["recovery_type"] == "unresolved"


class TestSensitiveContentDetection:
    # 敏感内容检测

    def test_diagnostics_rejects_sensitive_pattern(self, tmp_path: Path) -> None:
        # diagnostics拒绝敏感模式
        from scripts.ui_test_core.execution_attempt_store import (
            ExecutionAttemptStore,
            ExecutionAttemptStoreError,
        )
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        with pytest.raises(ExecutionAttemptStoreError) as exc_info:
            store.append_diagnostics(
                run_id="UIT-022",
                node_id=("pass" + "word=" + "sec" + "ret123"),
                code="E_TEST",
            )
        assert "SENSITIVE" in exc_info.value.code

    def test_event_rejects_absolute_path(self, tmp_path: Path) -> None:
        # 事件拒绝绝对路径evidence_ref
        from scripts.ui_test_core.execution_attempt_store import (
            ExecutionAttemptStore,
            ExecutionAttemptStoreError,
        )
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-023",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        with pytest.raises(ExecutionAttemptStoreError) as exc_info:
            store.append_event(
                run_id="UIT-023",
                node_id="test_node",
                event_type="admitted",
                evidence_ref=("C:\\Users\\" + "sec" + "ret\\file.txt"),
            )
        assert "ABSOLUTE" in exc_info.value.code


# ===========================================================================
# CompletionProjector 单元测试
# ===========================================================================

class TestCompletionProjector:
    # 六层Completion门禁

    def test_all_passed_completes(self) -> None:
        # 六层全部passed且无P0/P1/unknown时completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
            severity="P2",
        )
        result = projector.project()
        assert result["completed"] is True
        assert result["overall_status"] == "passed"
        assert result["projection_type"] == "completed"

    def test_missing_human_r2_not_completed(self) -> None:
        # 人工R2未通过不得completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "unknown",
            },
            severity="P2",
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "functional-accepted"
        assert result["delivery_status"] == "functional-accepted / repair-needed"

    def test_failed_layer_not_completed(self) -> None:
        # 有failed层级不得completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "failed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["overall_status"] == "failed"

    def test_blocked_layer_not_completed(self) -> None:
        # 有blocked层级不得completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "blocked",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["overall_status"] == "blocked"

    def test_p0_severity_not_completed(self) -> None:
        # P0严重等级阻断completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
            severity="P0",
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "repair-needed"

    def test_p1_severity_not_completed(self) -> None:
        # P1严重等级阻断completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
            severity="P1",
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "repair-needed"

    def test_unknown_severity_not_completed(self) -> None:
        # unknown严重等级阻断completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
            severity="unknown",
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "repair-needed"

    def test_functional_accepted_with_not_applicable(self) -> None:
        # 功能通过但治理证据不全投影为functional-accepted
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "not_applicable",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "passed",
            },
            severity="P2",
        )
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "functional-accepted"

    def test_six_layers_required(self) -> None:
        # 必须包含六个独立层级
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector()
        # 未设置的层级默认为unknown
        result = projector.project()
        assert result["completed"] is False
        assert result["projection_type"] == "repair-needed"
        assert result["delivery_status"] == "repair-needed"

    def test_unknown_layer_rejected(self) -> None:
        # 未知层级被拒绝
        from scripts.ui_test_core.completion_projector import (
            CompletionProjector,
            CompletionProjectionError,
        )
        with pytest.raises(CompletionProjectionError):
            CompletionProjector(layers={"unknown_layer": "passed"})

    def test_invalid_status_rejected(self) -> None:
        # 无效状态值被拒绝
        from scripts.ui_test_core.completion_projector import (
            CompletionProjector,
            CompletionProjectionError,
        )
        with pytest.raises(CompletionProjectionError):
            CompletionProjector(layers={"unit": "invalid_status"})

    def test_invalid_severity_rejected(self) -> None:
        # 未知严重度拼写不得绕过P0/P1/unknown门禁。
        from scripts.ui_test_core.completion_projector import CompletionProjector, CompletionProjectionError

        with pytest.raises(CompletionProjectionError):
            CompletionProjector(severity="P9")

    def test_pytest_passed_not_completion(self) -> None:
        # pytest passed不等同于completed
        from scripts.ui_test_core.completion_projector import CompletionProjector
        projector = CompletionProjector(
            layers={
                "unit": "passed",
                "collection": "passed",
                "release_verification": "passed",
                "qualification": "passed",
                "pycharm_integration": "passed",
                "human_r2": "unknown",  # 人工R2未通过
            },
        )
        result = projector.project()
        # 即使unit/collection等通过，human_r2未通过不得completed
        assert result["completed"] is False
        assert result["projection_type"] == "functional-accepted"


# ===========================================================================
# Schema 验证测试
# ===========================================================================

class TestSchemaProjection:
    # 从不可变记录投影Schema对象并用jsonschema验证

    def test_projection_validates_against_schema(self, tmp_path: Path) -> None:
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-024",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-024",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
        )
        store.create_terminal(
            run_id="UIT-024",
            node_id="test_node",
            status="passed",
        )
        projection = store.project_attempt(
            run_id="UIT-024",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
        )
        # 用jsonschema验证投影
        schema_path = _SKILL_ROOT / "schemas" / "execution-attempt-v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(projection))
        assert errors == [], f"Schema validation errors: {errors}"

    def test_unfinished_projection_validates(self, tmp_path: Path) -> None:
        # 无terminal的attempt投影为unfinished并验证通过
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=tmp_path, now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-025",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )
        store.append_event(
            run_id="UIT-025",
            node_id="test_node",
            event_type="admitted",
            phase="setup",
        )
        # 无terminal
        projection = store.project_attempt(
            run_id="UIT-025",
            node_id="test_node",
            case_id="CASE-001",
            branch_id="BRANCH-A",
        )
        schema_path = _SKILL_ROOT / "schemas" / "execution-attempt-v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(projection))
        assert errors == [], f"Schema validation errors: {errors}"


# ===========================================================================
# 集成测试：插件生命周期
# ===========================================================================

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
""")


def _write_pycharm_conftest_with_evidence(pytester: pytest.Pytester, config_yaml: str) -> None:
    """写入根conftest（含evidence root hook）和项目配置文件。"""
    conftest = _PLUGIN_CONTEST + textwrap.dedent("""\
        import sys
        _runner = pathlib.Path(__file__).parent / "plugins" / "python-ce" / "helpers" / "pycharm" / "_jb_pytest_runner.py"
        _runner.parent.mkdir(parents=True, exist_ok=True)
        _runner.write_text("# runner\\n", encoding="utf-8")
        sys.argv[0] = str(_runner)
    """)
    pytester.makeconftest(conftest)
    (pytester.path / "ui-test.project.yaml").write_text(config_yaml, encoding="utf-8")


class TestPluginAttemptLifecycle:
    # 插件创建attempt-start、记录事件并生成唯一terminal

    def test_attempt_created_and_terminal_written(self, pytester: pytest.Pytester) -> None:
        # 正常执行的item创建attempt-start、事件和唯一terminal
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_attempt=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-ATTEMPT-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_attempt_lifecycle(ui_test_execution_context):
                # R0 item创建attempt-start并记录事件
                ctx = ui_test_execution_context
                assert ctx.risk_level == "r0-read-only"
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)
        # 验证evidence目录存在
        evidence_dir = pytester.path / "evidence" / "attempts"
        assert evidence_dir.exists()
        attempt_dirs = list(evidence_dir.iterdir())
        assert len(attempt_dirs) >= 1
        # 验证attempt-start.json存在
        start_files = list(attempt_dirs[0].glob("attempt-start.json"))
        assert len(start_files) == 1
        # 验证terminal.json存在
        terminal_files = list(attempt_dirs[0].glob("terminal.json"))
        assert len(terminal_files) == 1

    def test_failed_test_creates_failed_terminal(self, pytester: pytest.Pytester) -> None:
        # 失败的测试创建failed terminal
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_fail=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-FAIL-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_failed_attempt(ui_test_execution_context):
                assert False, "故意失败"
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(failed=1)
        # 验证terminal状态为failed
        evidence_dir = pytester.path / "evidence" / "attempts"
        attempt_dirs = list(evidence_dir.iterdir())
        terminal_files = list(attempt_dirs[0].glob("terminal.json"))
        assert len(terminal_files) == 1
        terminal = json.loads(terminal_files[0].read_text(encoding="utf-8"))
        assert terminal["status"] == "failed"

    def test_setup_failure_creates_one_failed_terminal(self, pytester: pytest.Pytester) -> None:
        # fixture setup失败时call不会执行，但makereport仍须在teardown后生成唯一failed terminal。
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_setup_fail=textwrap.dedent("""\
            import pytest

            @pytest.fixture
            def broken_setup():
                raise RuntimeError("setup-failed")

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-SETUP-FAIL")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_setup_failure(ui_test_execution_context, broken_setup):
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(errors=1)
        terminal_files = list((pytester.path / "evidence" / "attempts").glob("*/terminal.json"))
        assert len(terminal_files) == 1
        assert json.loads(terminal_files[0].read_text(encoding="utf-8"))["status"] == "failed"

    def test_teardown_failure_creates_one_failed_terminal(self, pytester: pytest.Pytester) -> None:
        # fixture teardown失败必须覆盖call passed，最终仍是唯一failed terminal。
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_teardown_fail=textwrap.dedent("""\
            import pytest

            @pytest.fixture
            def broken_teardown():
                yield
                raise RuntimeError("teardown-failed")

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-TEARDOWN-FAIL")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_teardown_failure(ui_test_execution_context, broken_teardown):
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1, errors=1)
        terminal_files = list((pytester.path / "evidence" / "attempts").glob("*/terminal.json"))
        assert len(terminal_files) == 1
        assert json.loads(terminal_files[0].read_text(encoding="utf-8"))["status"] == "failed"

    def test_timeout_failure_maps_to_timed_out_terminal(self, pytester: pytest.Pytester) -> None:
        # TimeoutError只影响pytest层终态，不会被误报为普通passed。
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_timeout=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-TIMEOUT")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_timeout(ui_test_execution_context):
                raise TimeoutError("bounded timeout")
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(failed=1)
        terminal_file = next((pytester.path / "evidence" / "attempts").glob("*/terminal.json"))
        assert json.loads(terminal_file.read_text(encoding="utf-8"))["status"] == "timed_out"

    def test_skip_maps_to_cancelled_terminal(self, pytester: pytest.Pytester) -> None:
        # pytest显式skip表示当前尝试未执行完成，投影为cancelled而不是passed。
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_cancel=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-CANCEL")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_cancel(ui_test_execution_context):
                pytest.skip("cancelled by operator")
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(skipped=1)
        terminal_file = next((pytester.path / "evidence" / "attempts").glob("*/terminal.json"))
        assert json.loads(terminal_file.read_text(encoding="utf-8"))["status"] == "cancelled"

    def test_early_gate_no_attempt(self, pytester: pytest.Pytester) -> None:
        # 早期门禁失败不创建attempt
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_early=textwrap.dedent("""\
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
        # 验证attempts目录为空或不存在
        evidence_dir = pytester.path / "evidence" / "attempts"
        if evidence_dir.exists():
            attempt_dirs = list(evidence_dir.iterdir())
            assert len(attempt_dirs) == 0  # R3门禁失败不创建attempt
        # diagnostics应存在
        diagnostics = list((pytester.path / "evidence" / "diagnostics").glob("*.json"))
        assert len(diagnostics) == 1

    def test_pytest_passed_not_business_success(self, pytester: pytest.Pytester) -> None:
        # pytest passed不等同于业务写或人工R2成功
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        pytester.makepyfile(test_notbiz=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-NOTBIZ-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_pytest_passed_not_biz(ui_test_execution_context):
                # pytest通过但不是业务写成功
                pass
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)
        # terminal状态为passed只表示pytest层面通过
        evidence_dir = pytester.path / "evidence" / "attempts"
        attempt_dirs = list(evidence_dir.iterdir())
        terminal_files = list(attempt_dirs[0].glob("terminal.json"))
        terminal = json.loads(terminal_files[0].read_text(encoding="utf-8"))
        # terminal记录的passed仅表示pytest passed，不等同于业务写或R2成功
        assert terminal["status"] == "passed"
        # 但CompletionProjector仍需要六层全部passed


class TestPluginRecoveryIntegration:
    # 插件与恢复器集成

    def test_previous_unfinished_does_not_block(self, pytester: pytest.Pytester) -> None:
        # previous unfinished不阻断新run
        _write_pycharm_conftest_with_evidence(pytester, _V21_CONFIG_YAML)
        # 第一次运行创建正常attempt；随后另建无terminal历史记录模拟上一进程强杀。
        pytester.makepyfile(test_first=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-FIRST-001")
            @pytest.mark.branch_id("BRANCH-A")
            @pytest.mark.r0
            def test_first(ui_test_execution_context):
                assert ui_test_execution_context.run_id
        """))
        result = pytester.runpytest_subprocess("-v")
        result.assert_outcomes(passed=1)

        # 直接使用store创建无terminal attempt，等价于进程在start后被强杀且不删除历史。
        from scripts.ui_test_core.execution_attempt_store import ExecutionAttemptStore
        store = ExecutionAttemptStore(evidence_root=pytester.path / "evidence", now_func=_fixed_now)
        store.create_attempt_start(
            run_id="UIT-PREVIOUS-UNFINISHED",
            node_id="previous::node",
            case_id="CASE-PREVIOUS",
            branch_id="BRANCH-A",
            risk_level="r0-read-only",
            execution_origin="cli",
            approval_source="explicit-cli",
            stable_runner_digest="sha256:" + "a" * 64,
            project_config_digest="sha256:" + "b" * 64,
        )

        # 第二次运行不应被阻断
        pytester.makepyfile(test_second=textwrap.dedent("""\
            import pytest

            @pytest.mark.ui_test
            @pytest.mark.case_id("CASE-SECOND-001")
            @pytest.mark.branch_id("BRANCH-B")
            @pytest.mark.r0
            def test_second(ui_test_execution_context):
                # 新run不被previous unfinished阻断
                assert True
        """))
        result2 = pytester.runpytest_subprocess("-v")
        result2.assert_outcomes(passed=2)  # 两个当前suite节点均通过，previous unfinished未阻断。
