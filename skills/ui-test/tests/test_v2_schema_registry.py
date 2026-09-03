from pathlib import Path

from scripts.ui_test_core.registry_validator import validate_contract_registry
from scripts.ui_test_core.strict_json import load_strict_json


SKILL_ROOT = Path(__file__).resolve().parents[1]


def test_registry_contains_active_v2_family_and_deprecates_execution_v1():
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
        "ui-test.run-result.v3",
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

