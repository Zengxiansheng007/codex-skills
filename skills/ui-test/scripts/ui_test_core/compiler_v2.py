"""Deterministic v2 compiler sharing one complete parameter manifest across projections."""

from __future__ import annotations

import copy
import json
import pprint
import re
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .test_data_contracts import resolve_parameter_manifest


class CompileV2Error(ValueError):
    """稳定 v2 编译错误。"""


def _require_valid(document: Any, schema_name: str, code: str) -> None:
    issues = validate_document(document, schema_name)
    if issues:
        raise CompileV2Error(f"{code}:{issues[0]['path']}")


def _parameter_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["parameter_id"]: item for item in manifest["parameters"]}


def _resolve_steps(source_case: dict[str, Any], parameter_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    available = _parameter_map(parameter_manifest)
    step_ids: set[str] = set()
    resolved: list[dict[str, Any]] = []
    for sequence, source_step in enumerate(source_case["steps"], 1):
        step_id = source_step["step_id"]
        if step_id in step_ids:
            raise CompileV2Error("E_SOURCE_STEP_ID_DUPLICATE")
        step_ids.add(step_id)
        missing = [item for item in source_step["parameter_ids"] if item not in available]
        if missing:
            raise CompileV2Error(f"E_STEP_PARAMETER_NOT_FOUND:{missing[0]}")
        resolved.append({
            "resolved_step_id": f"RS-{sequence:03d}",
            "source_step_id": step_id,
            "section": source_step["section"],
            "sequence": sequence,
            "intent": source_step["intent"],
            "action": source_step["action"],
            "binding_ref": source_step.get("binding_ref"),
            "parameters": [copy.deepcopy(available[item]) for item in source_step["parameter_ids"]],
            "expected_result": source_step["expected_result"],
            "evidence": copy.deepcopy(source_step.get("evidence", [])),
        })
    return resolved


def _display_parameter(parameter: dict[str, Any]) -> str:
    if parameter.get("reference_only"):
        rendered = parameter["ref"]
    else:
        value = parameter.get("value")
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return f"{parameter['label']}：{rendered}"


def _render_human(source_case: dict[str, Any], resolved_steps: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    lines = [
        "<!-- do_not_edit: true -->",
        f"<!-- build_fingerprint: {metadata['build_fingerprint']} -->",
        f"# {source_case['display_name']}",
        "",
        "| 序号 | 操作 | 参数/数据 | 预期结果 |",
        "| --- | --- | --- | --- |",
    ]
    for step in resolved_steps:
        parameters = "；".join(_display_parameter(item) for item in step["parameters"]) or "-"
        lines.append(f"| {step['sequence']} | {step['intent']} | {parameters} | {step['expected_result']} |")
    return "\n".join(lines) + "\n"


def _render_playwright(source_case: dict[str, Any], parameter_manifest: dict[str, Any], metadata: dict[str, Any]) -> str:
    function_suffix = re.sub(r"[^0-9A-Za-z_]+", "_", f"{source_case['case_id']}_{source_case['branch_id']}").strip("_").lower()
    # 使用 Python 字面量而非 JSON 布尔值，确保生成模块可以直接导入执行。
    manifest_literal = pprint.pformat(parameter_manifest, sort_dicts=True, width=120)
    metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"# 生成元数据: {metadata_json}\n"
        "# CASE_PARAMETER_MANIFEST 由 test-data.json 编译生成，禁止在本文件手工维护。\n"
        "import pytest\n\n"
        f"pytestmark = [pytest.mark.{source_case['priority'].lower()}, pytest.mark.ui_test, pytest.mark.{source_case['risk_level'].lower()}]\n\n"
        f"CASE_PARAMETER_MANIFEST = {manifest_literal}\n\n"
        f"@pytest.mark.case_id({source_case['case_id']!r})\n"
        f"@pytest.mark.branch_id({source_case['branch_id']!r})\n"
        f"def test_{function_suffix}(ui_test_runtime):\n"
        "    # 运行时必须先校验参数身份，再由项目场景消费清单。\n"
        f"    ui_test_runtime.execute_case(case_id={source_case['case_id']!r}, branch_id={source_case['branch_id']!r}, parameter_manifest=CASE_PARAMETER_MANIFEST)\n"
    )


def compile_case_v2(
    *,
    source_case: dict[str, Any],
    test_data: dict[str, Any],
    dependency_assets: Mapping[str, Any],
    config_fingerprint: str,
    runtime_values: Mapping[str, Any] | None = None,
    credential_keys: set[str] | None = None,
    sequence_keys: set[str] | None = None,
    compiler_version: str = "2.0.0",
    renderer_version: str = "2.1.0",
) -> dict[str, Any]:
    """Compile one exact case+branch into an immutable v2 attachment set."""
    _require_valid(source_case, "source-case-v2.schema.json", "E_SOURCE_CASE_V2_INVALID")
    if test_data.get("case_id") != source_case["case_id"] or test_data.get("branch_id") != source_case["branch_id"]:
        raise CompileV2Error("E_SOURCE_TEST_DATA_SCOPE_MISMATCH")
    declared_runtime_refs = set(test_data.get("runtime_refs", []))
    used_runtime_refs = {item["ref"] for item in source_case["parameter_bindings"] if not item["ref"].startswith("test-data:")}
    if used_runtime_refs != declared_runtime_refs:
        raise CompileV2Error("E_SOURCE_TEST_DATA_RUNTIME_REF_MISMATCH")
    parameter_manifest = resolve_parameter_manifest(
        parameter_bindings=source_case["parameter_bindings"],
        test_data=test_data,
        runtime_values=runtime_values,
        credential_keys=credential_keys,
        sequence_keys=sequence_keys,
    )
    _require_valid(parameter_manifest, "case-parameter-manifest.schema.json", "E_PARAMETER_MANIFEST_INVALID")
    missing_dependencies = [item for item in source_case["dependency_refs"] if item not in dependency_assets]
    if missing_dependencies:
        raise CompileV2Error(f"E_DEPENDENCY_MISSING:{missing_dependencies[0]}")
    dependency_material = [
        {"id": item, "content_hash": canonical_hash(dependency_assets[item])}
        for item in sorted(source_case["dependency_refs"])
    ]
    dependency_digest = canonical_hash(dependency_material)
    source_hash = canonical_hash(source_case)
    resolved_steps = _resolve_steps(source_case, parameter_manifest)
    identity = {
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "runtime_material_digest": parameter_manifest["runtime_material_digest"],
        "dependency_digest": dependency_digest,
        "config_fingerprint": config_fingerprint,
        "compiler_version": compiler_version,
        "renderer_version": renderer_version,
    }
    build_fingerprint = canonical_hash(identity)
    case_ir = {
        "schema_version": "ui-test.case-ir.v2",
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "case_version": source_case["case_version"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "scope": copy.deepcopy(source_case["scope"]),
        "priority": source_case["priority"],
        "risk_level": source_case["risk_level"],
        "steps": copy.deepcopy(source_case["steps"]),
        "dependency_refs": copy.deepcopy(source_case["dependency_refs"]),
    }
    resolved_ir = {
        "schema_version": "ui-test.resolved-ir.v2",
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "dependency_digest": dependency_digest,
        "resolved_steps": resolved_steps,
    }
    metadata = {
        "source_case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "build_fingerprint": build_fingerprint,
        "do_not_edit": True,
    }
    outputs: dict[str, Any] = {
        "source-case.json": copy.deepcopy(source_case),
        "test-data.json": {key: copy.deepcopy(value) for key, value in test_data.items() if key not in {"test_data_hash", "source_path"}},
        "case-ir.json": case_ir,
        "resolved-ir.json": resolved_ir,
        "case-parameter-manifest.json": parameter_manifest,
        "human.md": _render_human(source_case, resolved_steps, metadata),
        "midscene.json": {"metadata": metadata, "steps": copy.deepcopy(resolved_steps)},
        "playwright-test.py": _render_playwright(source_case, parameter_manifest, metadata),
    }
    receipt = {
        "schema_version": "ui-test.compile-receipt.v2",
        **identity,
        "build_fingerprint": build_fingerprint,
        "artifact_names": sorted([*outputs, "compile-receipt.json"]),
    }
    outputs["compile-receipt.json"] = receipt
    manifest = {
        "schema_version": "ui-test.case-manifest.v2",
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "build_fingerprint": build_fingerprint,
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "runtime_material_digest": parameter_manifest["runtime_material_digest"],
        "dependency_digest": dependency_digest,
        "config_fingerprint": config_fingerprint,
        "generator_version": compiler_version,
        "renderer_version": renderer_version,
        "artifacts": {name: canonical_hash(content) for name, content in sorted(outputs.items())},
    }
    _require_valid(case_ir, "case-ir-v2.schema.json", "E_CASE_IR_V2_INVALID")
    _require_valid(resolved_ir, "resolved-ir-v2.schema.json", "E_RESOLVED_IR_V2_INVALID")
    _require_valid(receipt, "compile-receipt-v2.schema.json", "E_COMPILE_RECEIPT_V2_INVALID")
    _require_valid(manifest, "case-manifest-v2.schema.json", "E_CASE_MANIFEST_V2_INVALID")
    return {
        "identity": identity,
        "parameter_manifest": parameter_manifest,
        "case_ir": case_ir,
        "resolved_ir": resolved_ir,
        "outputs": outputs,
        "manifest": manifest,
    }
