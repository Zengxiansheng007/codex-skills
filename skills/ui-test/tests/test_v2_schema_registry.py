from pathlib import Path

from scripts.ui_test_core.registry_validator import validate_contract_registry
from scripts.ui_test_core.strict_json import load_strict_json


SKILL_ROOT = Path(__file__).resolve().parents[1]


def test_registry_tracks_active_transaction_family_and_deprecates_prior_execution_contracts():
    registry_path = SKILL_ROOT / "schemas" / "contract-registry.json"
    assert validate_contract_registry(registry_path, SKILL_ROOT) == []
    registry = load_strict_json(registry_path)
    statuses = {item["contract_id"]: item["status"] for item in registry["contracts"]}
    for contract_id in (
        "ui-test.test-data.v2",
        "ui-test.case-parameter-manifest.v2",
        "ui-test.source-case.v2",
        "ui-test.case-manifest.v2",
        "ui-test.compile-plan.v2",
        "ui-test.sync-state.v2",
        "ui-test.resolved-test-data.v2",
        "ui-test.failure-repair-event.v2",
    ):
        assert statuses[contract_id] == "active"
    for contract_id in (
        "ui-test.source-case.v1",
        "ui-test.case-ir.v1",
        "ui-test.resolved-ir.v1",
        "ui-test.case-manifest.v1",
        "ui-test.compile-receipt.v1",
        "ui-test.run-result.v2",
    ):
        assert statuses[contract_id] == "deprecated"
    # v2.1 迁移后 v2.0 项目配置、v1 R2 批准记录和 v3 RunResult 降级为只读审计
    for contract_id in (
        "ui-test.project.v2",
        "ui-test.r2-approval-record.v1",
        "ui-test.run-result.v3",
    ):
        assert statuses[contract_id] == "deprecated"
    # v2.1执行族与V4结果转为历史只读契约。
    for contract_id in (
        "ui-test.project.v2.1",
        "ui-test.execution-context.v2",
        "ui-test.execution-attempt.v1",
        "ui-test.run-result.v4",
    ):
        assert statuses[contract_id] == "deprecated"
    # ST-013新增transaction-v1执行族；R2 Approval V2继续有效。
    for contract_id in (
        "ui-test.r2-approval-record.v2",
        "ui-test.project.v2.2",
        "ui-test.execution-context.v3",
        "ui-test.execution-attempt.v2",
        "ui-test.run-result.v5",
        "ui-test.finalization-commit.v1",
        "ui-test.run-finalization-receipt.v1",
        "ui-test.pytest-session-result.v1",
        "ui-test.pycharm-process-evidence.v1",
        "ui-test.pycharm-acceptance-result.v1",
    ):
        assert statuses[contract_id] == "active"


def test_generic_active_surfaces_have_no_project_specific_identifiers():
    roots = [SKILL_ROOT / "scripts", SKILL_ROOT / "schemas", SKILL_ROOT / "references"]
    files = [SKILL_ROOT / "SKILL.md"]
    for root in roots:
        files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".py", ".json", ".md", ".yaml", ".yml"})
    forbidden = ("tianjin", "天津", "BOPS-ANNOUNCEMENT", "公告管理")
    findings = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker.lower() in text.lower() for marker in forbidden):
            findings.append(path.relative_to(SKILL_ROOT).as_posix())
    assert findings == []
