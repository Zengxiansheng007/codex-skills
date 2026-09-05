"""ST-013 自定义 pluggy hook 参数签名回归。"""

from __future__ import annotations

import pluggy
import pytest

from scripts.ui_test_core.pytest_runtime_plugin import _UiTestExecutionHooks


def test_finalization_hooks_publish_all_runtime_argnames() -> None:
    manager = pytest.PytestPluginManager()
    manager.add_hookspecs(_UiTestExecutionHooks)
    assert manager.hook.pytest_ui_test_finalization_target_v1.spec.argnames == (
        "run_id",
        "node_id",
        "attempt_store",
    )
    assert manager.hook.pytest_ui_test_build_finalization_candidate_v1.spec.argnames == (
        "run_id",
        "node_id",
        "transaction_id",
        "pre_terminal_events_hash",
        "pytest_phase_status",
        "attempt_store",
    )


def test_keyword_only_custom_hook_reproduces_missing_argument_typeerror() -> None:
    hookspec = pluggy.HookspecMarker("st013-probe")
    hookimpl = pluggy.HookimplMarker("st013-probe")

    class BadSpec:
        @hookspec(firstresult=True)
        def st013_probe(self, *, run_id, node_id):
            raise NotImplementedError

    class BadImpl:
        @hookimpl
        def st013_probe(self, *, run_id, node_id):
            raise RuntimeError("E_EXPECTED_PROJECT_ERROR")

    manager = pluggy.PluginManager("st013-probe")
    manager.add_hookspecs(BadSpec)
    manager.register(BadImpl())
    assert manager.hook.st013_probe.spec.argnames == ()
    with pytest.raises(TypeError, match="keyword-only"):
        manager.hook.st013_probe(run_id="RUN-001", node_id="node")

