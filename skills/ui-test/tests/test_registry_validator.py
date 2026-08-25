import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ui_test_core.registry_validator import (
    validate_contract_registry,
    validate_registry_and_baseline,
    validate_source_baseline,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SKILL_ROOT.parents[1]
REGISTRY = SKILL_ROOT / "schemas" / "contract-registry.json"
PACKAGE_BASELINE = SKILL_ROOT / "assets" / "source-baseline.json"
BASELINE = PACKAGE_BASELINE


class RegistryValidatorTests(unittest.TestCase):
    def test_workspace_registry_and_baseline_are_valid(self):
        result = validate_registry_and_baseline(REGISTRY, BASELINE, SKILL_ROOT)
        self.assertTrue(result["valid"], result["issues"])

    def test_missing_active_schema_is_reported(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["contracts"][0]["path"] = "schemas/missing.schema.json"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            issues = validate_contract_registry(path, SKILL_ROOT)
        self.assertIn("CONTRACT_PATH_MISSING", {issue["code"] for issue in issues})

    def test_duplicate_contract_id_is_reported(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["contracts"].append(copy.deepcopy(data["contracts"][0]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            issues = validate_contract_registry(path, SKILL_ROOT)
        self.assertIn("CONTRACT_ID_DUPLICATE", {issue["code"] for issue in issues})

    def test_unparseable_active_schema_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schemas = root / "schemas"
            schemas.mkdir()
            (schemas / "broken.json").write_text('{"type": "object"', encoding="utf-8")
            registry = {
                "contracts": [
                    {"contract_id": "test.broken.v1", "path": "schemas/broken.json", "status": "active"}
                ]
            }
            path = schemas / "contract-registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            issues = validate_contract_registry(path, root)
        self.assertIn("CONTRACT_SCHEMA_LOAD_FAILED", {issue["code"] for issue in issues})

    def test_invalid_active_schema_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schemas = root / "schemas"
            schemas.mkdir()
            (schemas / "invalid.json").write_text(json.dumps({"type": 7}), encoding="utf-8")
            registry = {
                "contracts": [
                    {"contract_id": "test.invalid.v1", "path": "schemas/invalid.json", "status": "active"}
                ]
            }
            path = schemas / "contract-registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            issues = validate_contract_registry(path, root)
        self.assertIn("CONTRACT_SCHEMA_INVALID", {issue["code"] for issue in issues})

    def test_planned_contract_requires_owner_and_null_path(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        data["contracts"].append({"contract_id": "test.future.v1", "path": None, "status": "planned"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            issues = validate_contract_registry(path, SKILL_ROOT)
        self.assertIn("PLANNED_CONTRACT_INVALID", {issue["code"] for issue in issues})

    def test_missing_baseline_hash_is_reported(self):
        data = json.loads(BASELINE.read_text(encoding="utf-8-sig"))
        data[0]["skill_md_sha256"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            issues = validate_source_baseline(path)
        self.assertIn("BASELINE_HASH_REQUIRED", {issue["code"] for issue in issues})


if __name__ == "__main__":
    unittest.main()
