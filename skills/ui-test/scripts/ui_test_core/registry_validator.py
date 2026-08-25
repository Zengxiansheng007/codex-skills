"""Validate the cross-skill contract registry and copied source baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ACTIVE_STATUSES = {"active", "deprecated"}
KNOWN_STATUSES = ACTIVE_STATUSES | {"planned", "archived"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_contract_registry(registry_path: str | Path, skill_root: str | Path | None = None) -> list[dict[str, str]]:
    path = Path(registry_path).resolve()
    root = Path(skill_root).resolve() if skill_root else path.parent.parent
    issues: list[dict[str, str]] = []

    try:
        registry = _load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return [{"code": "REGISTRY_LOAD_FAILED", "path": str(path), "message": str(error)}]

    contracts = registry.get("contracts") if isinstance(registry, dict) else None
    if not isinstance(contracts, list):
        return [{"code": "REGISTRY_CONTRACTS_INVALID", "path": str(path), "message": "contracts must be an array"}]

    seen: set[str] = set()
    for index, contract in enumerate(contracts):
        item_path = f"contracts[{index}]"
        if not isinstance(contract, dict):
            issues.append({"code": "REGISTRY_ENTRY_INVALID", "path": item_path, "message": "entry must be an object"})
            continue
        contract_id = contract.get("contract_id")
        status = contract.get("status")
        schema_ref = contract.get("path")
        if not isinstance(contract_id, str) or not contract_id:
            issues.append({"code": "CONTRACT_ID_REQUIRED", "path": item_path, "message": "contract_id is required"})
        elif contract_id in seen:
            issues.append({"code": "CONTRACT_ID_DUPLICATE", "path": item_path, "message": contract_id})
        else:
            seen.add(contract_id)
        if status not in KNOWN_STATUSES:
            issues.append({"code": "CONTRACT_STATUS_INVALID", "path": item_path, "message": str(status)})
            continue
        if status == "planned":
            if schema_ref is not None or not contract.get("owner_story"):
                issues.append({"code": "PLANNED_CONTRACT_INVALID", "path": item_path, "message": "planned contracts require null path and owner_story"})
            continue
        if status in ACTIVE_STATUSES:
            if not isinstance(schema_ref, str) or not schema_ref:
                issues.append({"code": "CONTRACT_PATH_REQUIRED", "path": item_path, "message": contract_id or item_path})
                continue
            referenced = (root / schema_ref).resolve()
            try:
                referenced.relative_to(root)
            except ValueError:
                issues.append({"code": "CONTRACT_PATH_OUTSIDE_ROOT", "path": item_path, "message": schema_ref})
                continue
            if not referenced.is_file():
                issues.append({"code": "CONTRACT_PATH_MISSING", "path": item_path, "message": schema_ref})
                continue
            try:
                schema = _load_json(referenced)
            except (OSError, json.JSONDecodeError) as error:
                issues.append({"code": "CONTRACT_SCHEMA_LOAD_FAILED", "path": item_path, "message": str(error)})
                continue
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as error:
                issues.append({"code": "CONTRACT_SCHEMA_INVALID", "path": item_path, "message": error.message})
    return issues


def validate_source_baseline(baseline_path: str | Path) -> list[dict[str, str]]:
    path = Path(baseline_path).resolve()
    try:
        records = _load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return [{"code": "BASELINE_LOAD_FAILED", "path": str(path), "message": str(error)}]
    if not isinstance(records, list) or not records:
        return [{"code": "BASELINE_INVALID", "path": str(path), "message": "baseline must be a non-empty array"}]

    issues: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        item_path = f"baseline[{index}]"
        if not isinstance(record, dict):
            issues.append({"code": "BASELINE_ENTRY_INVALID", "path": item_path, "message": "entry must be an object"})
            continue
        skill = record.get("skill")
        expected_hash = record.get("skill_md_sha256")
        source_value = Path(str(record.get("source", "")))
        source = source_value if source_value.is_absolute() else (path.parent / source_value).resolve()
        if not isinstance(skill, str) or not skill:
            issues.append({"code": "BASELINE_SKILL_REQUIRED", "path": item_path, "message": "skill is required"})
        elif skill in seen:
            issues.append({"code": "BASELINE_SKILL_DUPLICATE", "path": item_path, "message": skill})
        else:
            seen.add(skill)
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            issues.append({"code": "BASELINE_HASH_REQUIRED", "path": item_path, "message": skill or item_path})
            continue
        skill_file = source / "SKILL.md"
        if not skill_file.is_file():
            issues.append({"code": "BASELINE_SOURCE_MISSING", "path": item_path, "message": str(skill_file)})
        elif _sha256(skill_file) != expected_hash.upper():
            issues.append({"code": "BASELINE_HASH_MISMATCH", "path": item_path, "message": skill or item_path})
    return issues


def validate_registry_and_baseline(
    registry_path: str | Path,
    baseline_path: str | Path,
    skill_root: str | Path | None = None,
) -> dict[str, Any]:
    issues = validate_contract_registry(registry_path, skill_root)
    issues.extend(validate_source_baseline(baseline_path))
    return {"valid": not issues, "issues": issues}
