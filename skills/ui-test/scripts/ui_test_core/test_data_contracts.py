"""Branch-level test-data loading, RFC 6901 pointers and typed reference resolution."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .strict_json import load_strict_json


REFERENCE_PATTERN = re.compile(r"^(test-data|value|credential|sequence):(.+)$")
PROHIBITED_KEY_NAMES = (
    "pass" + "word", "pass" + "wd", "p" + "wd", "to" + "ken", "coo" + "kie",
    "author" + "ization", "storage" + "_state", "sec" + "ret",
)
PROHIBITED_KEY_PATTERN = re.compile(
    r"(?:^|_)(?:" + "|".join(PROHIBITED_KEY_NAMES) + r")(?:$|_)",
    re.IGNORECASE,
)


class TestDataError(ValueError):
    """稳定、无敏感值回显的 Test Data 错误。"""


TestDataError.__test__ = False  # 防止 pytest 将异常类型误识别为测试类。


def _decode_pointer_segment(segment: str) -> str:
    # RFC 6901 只允许 ~0 和 ~1 两种转义。
    index = 0
    output: list[str] = []
    while index < len(segment):
        character = segment[index]
        if character != "~":
            output.append(character)
            index += 1
            continue
        if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
            raise TestDataError("E_JSON_POINTER_ESCAPE_INVALID")
        output.append("~" if segment[index + 1] == "0" else "/")
        index += 2
    return "".join(output)


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 pointer and return a defensive copy."""
    if pointer == "":
        return copy.deepcopy(document)
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise TestDataError("E_JSON_POINTER_INVALID")
    current = document
    for raw_segment in pointer[1:].split("/"):
        segment = _decode_pointer_segment(raw_segment)
        if isinstance(current, dict):
            if segment not in current:
                raise TestDataError("E_JSON_POINTER_NOT_FOUND")
            current = current[segment]
        elif isinstance(current, list):
            if segment == "-" or not segment.isdigit() or (len(segment) > 1 and segment.startswith("0")):
                raise TestDataError("E_JSON_POINTER_ARRAY_INDEX_INVALID")
            position = int(segment)
            if position >= len(current):
                raise TestDataError("E_JSON_POINTER_NOT_FOUND")
            current = current[position]
        else:
            raise TestDataError("E_JSON_POINTER_NOT_CONTAINER")
    return copy.deepcopy(current)


def _find_prohibited_keys(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if PROHIBITED_KEY_PATTERN.search(str(key)):
                findings.append(child_path)
            findings.extend(_find_prohibited_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_prohibited_keys(child, f"{path}/{index}"))
    return findings


def load_test_data(path: str | Path, *, case_id: str, branch_id: str) -> dict[str, Any]:
    """Load and validate one branch-owned editable Test Data document."""
    document = load_strict_json(path)
    issues = validate_document(document, "test-data.schema.json")
    if issues:
        first = issues[0]
        raise TestDataError(f"E_TEST_DATA_SCHEMA_INVALID:{first['path']}")
    if document["case_id"] != case_id or document["branch_id"] != branch_id:
        raise TestDataError("E_TEST_DATA_SCOPE_MISMATCH")
    prohibited = _find_prohibited_keys({
        "parameters": document.get("parameters", {}),
        "generation_rules": document.get("generation_rules", {}),
    })
    if prohibited:
        raise TestDataError(f"E_TEST_DATA_PROHIBITED_KEY:{prohibited[0]}")
    loaded = copy.deepcopy(document)
    loaded["test_data_hash"] = canonical_hash(document)
    loaded["source_path"] = str(Path(path).resolve())
    return loaded


def parse_typed_reference(reference: str) -> tuple[str, str]:
    match = REFERENCE_PATTERN.fullmatch(reference) if isinstance(reference, str) else None
    if not match:
        raise TestDataError("E_TYPED_REFERENCE_INVALID")
    return match.group(1), match.group(2)


def _runtime_entry(runtime_values: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    entry = runtime_values.get(key)
    if not isinstance(entry, Mapping) or "value" not in entry:
        raise TestDataError(f"E_RUNTIME_REFERENCE_NOT_FOUND:{key}")
    return entry


def resolve_parameter_manifest(
    *,
    parameter_bindings: list[dict[str, Any]],
    test_data: dict[str, Any],
    runtime_values: Mapping[str, Any] | None = None,
    credential_keys: set[str] | None = None,
    sequence_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Create the single parameter manifest consumed by all v2 renderers."""
    runtime_values = runtime_values or {}
    credential_keys = credential_keys or set()
    sequence_keys = sequence_keys or set()
    parameters: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    runtime_material: list[dict[str, Any]] = []
    for binding in parameter_bindings:
        parameter_id = binding.get("parameter_id")
        reference = binding.get("ref")
        if not isinstance(parameter_id, str) or not parameter_id or parameter_id in seen_ids:
            raise TestDataError("E_PARAMETER_ID_INVALID_OR_DUPLICATE")
        seen_ids.add(parameter_id)
        prefix, target = parse_typed_reference(reference)
        item: dict[str, Any] = {
            "parameter_id": parameter_id,
            "label": binding.get("label", parameter_id),
            "ref": reference,
            "source_type": prefix,
            "required": bool(binding.get("required", True)),
        }
        if prefix == "test-data":
            item["value"] = resolve_json_pointer(test_data, target)
        elif prefix == "value":
            entry = _runtime_entry(runtime_values, target)
            if entry.get("sensitive") is True or entry.get("classification") not in {"ordinary", "non-sensitive"}:
                raise TestDataError(f"E_RUNTIME_VALUE_NOT_EXPANDABLE:{target}")
            item["value"] = copy.deepcopy(entry["value"])
            runtime_material.append({"key": target, "value_hash": canonical_hash(entry["value"])})
        elif prefix == "credential":
            if target not in credential_keys:
                raise TestDataError(f"E_CREDENTIAL_REFERENCE_NOT_FOUND:{target}")
            item["reference_only"] = True
        elif prefix == "sequence":
            if target not in sequence_keys:
                raise TestDataError(f"E_SEQUENCE_REFERENCE_NOT_FOUND:{target}")
            item["reference_only"] = True
        parameters.append(item)
    manifest = {
        "schema_version": "ui-test.case-parameter-manifest.v2",
        "case_id": test_data["case_id"],
        "branch_id": test_data["branch_id"],
        "data_revision": test_data["data_revision"],
        "test_data_hash": test_data["test_data_hash"],
        "runtime_material_digest": canonical_hash(sorted(runtime_material, key=lambda item: item["key"])),
        "parameters": parameters,
    }
    manifest["parameter_manifest_hash"] = canonical_hash(manifest)
    return manifest
