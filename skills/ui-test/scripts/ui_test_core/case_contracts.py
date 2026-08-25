"""Source Case canonicalization, validation and Case IR lowering."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .jcs import dumps as jcs_dumps, sha256 as jcs_sha256


SKILL_ROOT = Path(__file__).resolve().parents[2]


def canonical_bytes(value: Any) -> bytes:
    return jcs_dumps(value)


def canonical_hash(value: Any) -> str:
    return jcs_sha256(value)


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SKILL_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def validate_document(document: Any, schema_name: str) -> list[dict[str, str]]:
    validator = Draft202012Validator(load_schema(schema_name))
    return [
        {"code": "SCHEMA_VALIDATION_FAILED", "path": "/" + "/".join(str(part) for part in error.absolute_path), "message": error.message}
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))
    ]


def validate_source_case(source_case: Any) -> list[dict[str, str]]:
    issues = validate_document(source_case, "source-case.schema.json")
    if not isinstance(source_case, dict):
        return issues
    steps = source_case.get("steps", {})
    all_steps = [step for section in ("setup", "feature", "assertions") for step in steps.get(section, []) if isinstance(step, dict)] if isinstance(steps, dict) else []
    ids = [step.get("step_id") for step in all_steps]
    if len(ids) != len(set(ids)):
        issues.append({"code": "SOURCE_STEP_ID_DUPLICATE", "path": "/steps", "message": "step_id must be unique across all sections"})
    test_points = source_case.get("test_points", [])
    for index, point in enumerate(test_points if isinstance(test_points, list) else []):
        if isinstance(point, dict) and point.get("responsibility") in {"primary", "supporting"}:
            if point.get("coverage_method") == "not-applicable":
                issues.append({"code": "TEST_POINT_COVERAGE_REQUIRED", "path": f"/test_points/{index}", "message": "covered responsibility cannot be not-applicable"})
    for step in all_steps:
        parameters = step.get("parameters", [])
        if not isinstance(parameters, list):
            continue
        for param_index, parameter in enumerate(parameters):
            if not isinstance(parameter, dict):
                continue
            source_type = parameter.get("source_type")
            index_ref = parameter.get("index_ref")
            if source_type in {"shared-data", "public-data"} and not isinstance(index_ref, str):
                issues.append({
                    "code": "STEP_SHARED_DATA_INDEX_REQUIRED",
                    "path": f"/steps/{step.get('step_id', 'unknown')}/parameters/{param_index}",
                    "message": "shared/public data parameters must declare an index_ref",
                })
    forbidden = {"approval_token", "username", "password", "cookie", "token", "storage_state"}
    if forbidden.intersection(source_case):
        issues.append({"code": "SOURCE_CASE_RUNTIME_STATE_FORBIDDEN", "path": "/", "message": "runtime approval or credential state is forbidden"})
    return issues


def validate_semantics(source_case: dict[str, Any], *, source_path: str = "<inline>") -> list[dict[str, Any]]:
    """Run semantic Rule Registry and return a stable issue list.

    Imported lazily to avoid a circular import at module load time.
    """
    from .semantic_rules import validate_semantics as _validate_semantics
    return _validate_semantics(source_case, source_path=source_path)


def lower_to_case_ir(source_case: dict[str, Any], *, source_path: str = "<inline>") -> dict[str, Any]:
    issues = validate_source_case(source_case)
    if issues:
        raise ValueError(json.dumps(issues, ensure_ascii=False))
    semantic_issues = validate_semantics(source_case, source_path=source_path)
    if any(i.get("blocking") for i in semantic_issues):
        raise ValueError(json.dumps(semantic_issues, ensure_ascii=False))
    steps: list[dict[str, Any]] = []
    sequence = 1
    for section in ("setup", "feature", "assertions"):
        for source_step in source_case["steps"][section]:
            step = copy.deepcopy(source_step)
            step["source_step_id"] = step.pop("step_id")
            step["section"] = section
            step["sequence"] = sequence
            step.pop("forbidden_actions", None)
            step.setdefault("evidence", [])
            steps.append(step)
            sequence += 1
    for source_step in source_case.get("special_preconditions", []):
        step = copy.deepcopy(source_step)
        step["source_step_id"] = step.pop("step_id")
        step["section"] = "special_preconditions"
        step["sequence"] = sequence
        step.pop("forbidden_actions", None)
        step.setdefault("evidence", [])
        steps.append(step)
        sequence += 1
    binding_refs = sorted({step["binding_ref"] for step in steps if step.get("binding_ref")})
    return {
        "schema_version": "ui-test.case-ir.v1",
        "case_id": source_case["case_id"],
        "case_version": source_case["case_version"],
        "source_hash": canonical_hash(source_case),
        "display_name": source_case["display_name"],
        "scope": copy.deepcopy(source_case["scope"]),
        "priority": source_case["priority"],
        "p0_suite_id": source_case.get("p0_suite_id"),
        "branch_id": source_case.get("branch_id"),
        "risk_level": source_case["risk"]["risk_level"],
        "precondition_group": source_case["precondition_group"],
        "flow_refs": copy.deepcopy(source_case["precondition_flow_refs"]),
        "binding_refs": binding_refs,
        "test_points": copy.deepcopy(source_case["test_points"]),
        "normalized_steps": steps,
    }
