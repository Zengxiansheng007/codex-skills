from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
FIXTURE_ROOT = ROOT / "assets" / "fixtures" / "runtime-root"
TEST_OUTPUT_ROOT = Path(tempfile.gettempdir()) / "ui-test-checkpoint-runtime-tests"


def run_cli(*args: str, root: Path | None = None, expect_report: bool = True) -> tuple[int, dict]:
    TEST_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    report = TEST_OUTPUT_ROOT / "runtime-report.json"
    if report.exists():
        report.unlink()
    cmd = [
        PYTHON,
        "-B",
        "-m",
        "checkpoint_runtime",
        "--root",
        str(root or FIXTURE_ROOT),
        "--system-id",
        "demo-system",
        "--module-id",
        "requirement-pool",
        "--report",
        str(report),
        *args,
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "scripts")},
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if not report.exists():
        if not expect_report:
            return completed.returncode, {"stdout": completed.stdout, "stderr": completed.stderr}
        raise AssertionError(f"report was not created; stdout={completed.stdout} stderr={completed.stderr}")
    return completed.returncode, json.loads(report.read_text(encoding="utf-8"))


def test_readonly_button_plans_successfully() -> None:
    code, report = run_cli(
        "--button-id",
        "open-create-page",
        "--environment-alias",
        "test",
        "--run-id",
        "run-test-001",
        "--correlation-id",
        "corr-test-001",
    )
    assert code == 0
    assert report["result"] == "planned"
    assert report["blocked"] is False
    assert report["run_id"] == "run-test-001"
    assert report["correlation_id"] == "corr-test-001"
    assert report["executed_chain"] == [
        "CP1-login-state",
        "CP2-project-switch",
        "CP3-module-entry",
        "open-create-page",
    ]
    assert "state_path_ref" not in report["auth_ref"]
    assert report["evidence"]["redaction"]["storage_state_included"] is False
    assert report["report_hash"]
    assert report["mode"] == "dry-run"


def test_write_button_is_blocked() -> None:
    code, report = run_cli("--button-id", "submit-form", "--environment-alias", "test")
    assert code == 2
    assert report["result"] == "blocked"
    assert report["block_reason"] == "blocked-write-checkpoint"
    assert report["failure_attribution"]["layer"] == "safety-policy"
    assert report["failure_attribution"]["failure_type"] == "blocked_write_action"


def test_unknown_button_is_requirement_gap() -> None:
    code, report = run_cli("--button-id", "missing-button", "--environment-alias", "test")
    assert code == 2
    assert report["block_reason"] == "unknown-function-button"
    assert report["failure_attribution"]["layer"] == "requirement-ambiguity"
    assert report["failure_attribution"]["failure_type"] == "missing_button"


def test_module_entry_without_button() -> None:
    code, report = run_cli("--environment-alias", "test")
    assert code == 0
    assert report["executed_chain"] == ["CP1-login-state", "CP2-project-switch", "CP3-module-entry"]


def copy_fixture_tree() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="checkpoint-runtime-test-"))
    shutil.rmtree(tmp)
    shutil.copytree(FIXTURE_ROOT, tmp)
    return tmp


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_expired_auth_is_blocked_stale() -> None:
    tmp = copy_fixture_tree()
    auth_path = tmp / "systems" / "demo-system" / "modules" / "requirement-pool" / "auth" / "auth-ref.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    auth["expires_at"] = "2000-01-01T00:00:00Z"
    write_json(auth_path, auth)
    code, report = run_cli("--environment-alias", "test", root=tmp)
    assert code == 2
    assert report["block_reason"] == "auth-ref-expired"
    assert report["failure_attribution"]["layer"] == "auth-expired"
    assert report["failure_attribution"]["failure_type"] == "auth_ref_expired"


def test_r2_checkpoint_index_is_rejected_by_schema() -> None:
    tmp = copy_fixture_tree()
    index_path = tmp / "systems" / "demo-system" / "modules" / "requirement-pool" / "checkpoint.index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["checkpoints"][0]["risk_level"] = "R2"
    write_json(index_path, index)
    code, report = run_cli("--environment-alias", "test", root=tmp, expect_report=False)
    assert code != 0
    assert "validation failed" in report["stderr"]


def test_auth_reportable_true_fails_closed() -> None:
    tmp = copy_fixture_tree()
    auth_path = tmp / "systems" / "demo-system" / "modules" / "requirement-pool" / "auth" / "auth-ref.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    auth["reportable"] = True
    write_json(auth_path, auth)
    code, report = run_cli("--environment-alias", "test", root=tmp, expect_report=False)
    assert code != 0
    assert "validation failed" in report["stderr"] or "auth_ref must not be reportable" in report["stderr"]


def test_module_manifest_requires_public_execution_contract() -> None:
    manifest_path = FIXTURE_ROOT / "systems" / "demo-system" / "modules" / "requirement-pool" / "module.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["base_url"].startswith("https://")
    assert manifest["module_assertions"]["visible_text"]
    button = next(item for item in manifest["function_buttons"] if item["button_id"] == "open-create-page")
    assert button["locator"]["strategy"] in {"role", "text", "test_id", "css"}
    assert button["result_assertions"]["visible_text"]


def main() -> int:
    tests = [
        test_readonly_button_plans_successfully,
        test_write_button_is_blocked,
        test_unknown_button_is_requirement_gap,
        test_module_entry_without_button,
        test_expired_auth_is_blocked_stale,
        test_r2_checkpoint_index_is_rejected_by_schema,
        test_auth_reportable_true_fails_closed,
        test_module_manifest_requires_public_execution_contract,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
