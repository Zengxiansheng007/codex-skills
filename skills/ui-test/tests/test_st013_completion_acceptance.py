"""ST-013 验证 V5 不能绕过外部 PyCharm 进程验收。"""

from __future__ import annotations

from scripts.ui_test_core.completion import evaluate_release
from scripts.ui_test_core.completion_projector import CompletionProjector, REQUIRED_LAYERS
from scripts.ui_test_core.result_model import evaluate_completion
from scripts.ui_test_core.run_governance import project_run_result

from test_st013_pycharm_acceptance import _build_from_files


def _v5() -> dict:
    return {
        "schema_version": "ui-test.run-result.v5",
        "run_id": "RUN-001",
        "case_id": "CASE-001",
        "branch_id": "primary",
        "overall_status": "passed",
        "evidence_refs": [],
        "step_results": [],
    }


def _acceptance() -> dict:
    return {
        "schema_version": "ui-test.pycharm-acceptance-result.v1",
        "overall_status": "passed",
        "observed_process_exit_code": 0,
        "post_run_recovery": False,
    }


def _valid_chain(tmp_path):
    acceptance, documents = _build_from_files(tmp_path)
    chain = {
        "run_result": documents["run"],
        "finalization_commit": documents["commit"],
        "finalization_receipt": documents["receipt"],
        "pytest_session_result": documents["session"],
        "acceptance_result": acceptance,
        "approval_record": documents["approval"],
        "execution_context": documents["context"],
        "terminal": documents["terminal"],
        "process_evidence": documents["process"],
    }
    return acceptance, documents, chain


def test_completion_projector_blocks_v5_without_external_acceptance() -> None:
    layers = {layer: "passed" for layer in REQUIRED_LAYERS}
    result = CompletionProjector(layers=layers, severity="clear", run_result=_v5()).project()
    assert result["completed"] is False
    assert result["layered_status"]["pycharm_integration"] == "blocked"
    assert result["layered_status"]["human_r2"] == "blocked"


def test_completion_projector_accepts_hash_bound_external_exit_projection(tmp_path) -> None:
    layers = {layer: "passed" for layer in REQUIRED_LAYERS}
    acceptance, documents, chain = _valid_chain(tmp_path)
    result = CompletionProjector(
        layers=layers,
        severity="clear",
        run_result=documents["run"],
        acceptance_result=acceptance,
        acceptance_chain=chain,
    ).project()
    assert result["completed"] is True


def test_release_gate_requires_receipt_session_and_acceptance_for_v5(tmp_path) -> None:
    common = {
        "rtm": {"valid": True},
        "run_result": _v5(),
        "tests_ok": True,
        "sensitive_scan": {"status": "passed"},
        "public_pilot": {"passed": True},
        "migration_ok": True,
        "xmind_golden": {"passed": True},
    }
    blocked = evaluate_release(**common)
    assert blocked["completed"] is False
    assert "external-pycharm-acceptance-missing" in blocked["blockers"]

    acceptance, documents, chain = _valid_chain(tmp_path)
    passed_common = {**common, "run_result": documents["run"]}
    passed = evaluate_release(
        **passed_common,
        finalization_receipt=documents["receipt"],
        pytest_session_result=documents["session"],
        acceptance_result=acceptance,
        acceptance_chain=chain,
    )
    assert passed["completed"] is True


def test_legacy_completion_helper_cannot_accept_v5_business_pass_alone(tmp_path) -> None:
    kwargs = {
        "run_result": _v5(),
        "required_requirements": {"FR-013"},
        "passed_requirements": {"FR-013"},
        "sensitive_scan_ok": True,
        "migration_ok": True,
        "state_valid": True,
        "risk_isolated": True,
        "p0_p1_findings": [],
    }
    assert evaluate_completion(**kwargs)["completed"] is False
    acceptance, documents, chain = _valid_chain(tmp_path)
    accepted = evaluate_completion(
        **{**kwargs, "run_result": documents["run"]},
        finalization_receipt=documents["receipt"],
        pytest_session_result=documents["session"],
        acceptance_result=acceptance,
        acceptance_chain=chain,
    )
    assert accepted["completed"] is True


def test_v5_experience_projection_is_negative_without_external_acceptance(tmp_path) -> None:
    assert project_run_result(_v5(), "experience-candidate")["experience_status"] == "negative"
    acceptance, documents, chain = _valid_chain(tmp_path)
    assert project_run_result(
        documents["run"],
        "experience-candidate",
        acceptance_result=acceptance,
        acceptance_chain=chain,
    )["experience_status"] == "observed"


def test_minimal_forged_acceptance_never_completes() -> None:
    layers = {layer: "passed" for layer in REQUIRED_LAYERS}
    result = CompletionProjector(
        layers=layers,
        severity="clear",
        run_result=_v5(),
        acceptance_result=_acceptance(),
        acceptance_chain={},
    ).project()
    assert result["completed"] is False
    forged = _acceptance()
    release = evaluate_release(
        rtm={"valid": True},
        run_result=_v5(),
        tests_ok=True,
        sensitive_scan={"status": "passed"},
        public_pilot={"passed": True},
        migration_ok=True,
        xmind_golden={"passed": True},
        finalization_receipt={"status": "committed", "recovery_mode": "none"},
        pytest_session_result={"pytest_exitstatus": 0},
        acceptance_result=forged,
        acceptance_chain={},
    )
    assert release["completed"] is False
    legacy = evaluate_completion(
        run_result=_v5(),
        required_requirements={"FR-013"},
        passed_requirements={"FR-013"},
        sensitive_scan_ok=True,
        migration_ok=True,
        state_valid=True,
        risk_isolated=True,
        p0_p1_findings=[],
        finalization_receipt={"status": "committed", "recovery_mode": "none"},
        pytest_session_result={"pytest_exitstatus": 0},
        acceptance_result=forged,
        acceptance_chain={},
    )
    assert legacy["completed"] is False
    projection = project_run_result(
        _v5(), "experience-candidate", acceptance_result=forged, acceptance_chain={}
    )
    assert projection["experience_status"] == "negative"
