"""Deterministic v2 compiler sharing one complete parameter manifest across projections."""

from __future__ import annotations

import copy
import json
import pprint
import re
from typing import Any, Mapping

from .case_contracts import canonical_hash, validate_document
from .test_data_contracts import resolve_json_pointer, resolve_parameter_manifest


class CompileV2Error(ValueError):
    """稳定 v2 编译错误。"""


def _prevalidate_step_contracts(source_case: Mapping[str, Any]) -> None:
    """在 Schema 汇总错误前，把常见步骤缺失映射为稳定语义错误码。"""
    steps = source_case.get("steps")
    if not isinstance(steps, list):
        raise CompileV2Error("E_STEP_POSTCONDITION_MISSING:steps")
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise CompileV2Error(f"E_STEP_POSTCONDITION_MISSING:index-{index}")
        step_id = step.get("step_id", index)
        if not isinstance(step.get("module_id"), str) or not step.get("module_id", "").strip():
            raise CompileV2Error(f"E_P0_MODULE_COVERAGE_MISSING:{step_id}")
        postconditions = step.get("postconditions")
        if not isinstance(postconditions, list) or not postconditions:
            raise CompileV2Error(f"E_STEP_POSTCONDITION_MISSING:{step_id}")


def _require_valid(document: Any, schema_name: str, code: str) -> None:
    issues = validate_document(document, schema_name)
    if issues:
        raise CompileV2Error(f"{code}:{issues[0]['path']}")


def _parameter_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["parameter_id"]: item for item in manifest["parameters"]}


def _resolve_expected_ref(reference: str, *, test_data: dict[str, Any], available: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prefix, separator, target = reference.partition(":")
    if not separator or not target:
        raise CompileV2Error("E_STEP_POSTCONDITION_MISSING")
    if prefix == "test-data":
        return {"expected_value": copy.deepcopy(resolve_json_pointer(test_data, target))}
    if prefix == "parameter":
        parameter = available.get(target)
        if parameter is None:
            raise CompileV2Error(f"E_STEP_PARAMETER_NOT_FOUND:{target}")
        if parameter.get("reference_only"):
            return {"expected_reference": parameter["ref"], "reference_only": True}
        return {"expected_value": copy.deepcopy(parameter.get("value"))}
    if prefix == "literal":
        return {"expected_value": target}
    return {"expected_reference": reference, "reference_only": True}


def _validate_module_coverage(source_case: dict[str, Any], page_module_registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    _require_valid(page_module_registry, "page-module-registry.schema.json", "E_PAGE_MODULE_REGISTRY_INVALID")
    branch_id = source_case["branch_id"]
    modules = page_module_registry["modules"]
    page_steps: dict[str, list[dict[str, Any]]] = {}
    assertion_ids: set[str] = set()
    for step in source_case["steps"]:
        for postcondition in step["postconditions"]:
            assertion_id = postcondition["assertion_id"]
            if assertion_id in assertion_ids:
                raise CompileV2Error("E_STEP_POSTCONDITION_MISSING:duplicate-assertion-id")
            assertion_ids.add(assertion_id)
        if step["section"] != "feature" or step["action"] in {"screenshot", "submit"}:
            continue
        module_id = step["module_id"]
        if module_id not in modules:
            raise CompileV2Error(f"E_ASSERTION_TARGET_UNREGISTERED:{module_id}")
        if len(step["postconditions"]) != 1:
            raise CompileV2Error(f"E_COMPOSITE_PAGE_OPERATION_FORBIDDEN:{step['step_id']}")
        page_steps.setdefault(module_id, []).append(step)

    coverage: list[dict[str, Any]] = []
    for module_id, definition in sorted(modules.items()):
        mode = definition["branch_modes"].get(branch_id, "not-applicable")
        steps = page_steps.pop(module_id, [])
        if mode == "not-applicable":
            if steps:
                raise CompileV2Error(f"E_COMPOSITE_PAGE_OPERATION_FORBIDDEN:{module_id}")
            coverage.append({"module_id": module_id, "mode": mode, "step_id": None, "assertion_id": None})
            continue
        if len(steps) != 1:
            raise CompileV2Error(f"E_P0_MODULE_COVERAGE_MISSING:{module_id}")
        step = steps[0]
        if mode == "assert-default":
            postcondition = step["postconditions"][0]
            if step["action"] != "assert-default" or not postcondition["expected_ref"].startswith("test-data:"):
                raise CompileV2Error(f"E_DEFAULT_EXPECTATION_MISSING:{module_id}")
        elif step["action"] == "assert-default":
            raise CompileV2Error(f"E_COMPOSITE_PAGE_OPERATION_FORBIDDEN:{module_id}")
        coverage.append({
            "module_id": module_id,
            "mode": mode,
            "step_id": step["step_id"],
            "assertion_id": step["postconditions"][0]["assertion_id"],
        })
    if page_steps:
        raise CompileV2Error(f"E_ASSERTION_TARGET_UNREGISTERED:{sorted(page_steps)[0]}")
    return coverage


def _resolve_steps(source_case: dict[str, Any], parameter_manifest: dict[str, Any], test_data: dict[str, Any]) -> list[dict[str, Any]]:
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
        postconditions = []
        for postcondition in source_step["postconditions"]:
            resolved_postcondition = copy.deepcopy(postcondition)
            resolved_postcondition.update(_resolve_expected_ref(postcondition["expected_ref"], test_data=test_data, available=available))
            postconditions.append(resolved_postcondition)
        resolved.append({
            "resolved_step_id": f"RS-{sequence:03d}",
            "source_step_id": step_id,
            "section": source_step["section"],
            "sequence": sequence,
            "intent": source_step["intent"],
            "action": source_step["action"],
            "module_id": source_step["module_id"],
            "binding_ref": source_step.get("binding_ref"),
            "parameters": [copy.deepcopy(available[item]) for item in source_step["parameter_ids"]],
            "expected_result": source_step["expected_result"],
            "evidence": copy.deepcopy(source_step.get("evidence", [])),
            "postconditions": postconditions,
        })
    return resolved


def _display_parameter(parameter: dict[str, Any]) -> str:
    if parameter.get("reference_only"):
        rendered = parameter["ref"]
    else:
        value = parameter.get("value")
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return f"{parameter['label']}：{rendered}"


def _display_postcondition(postcondition: dict[str, Any]) -> str:
    if postcondition.get("reference_only"):
        expected = postcondition["expected_reference"]
    else:
        value = postcondition.get("expected_value")
        expected = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return f"{postcondition['assertion_id']} {postcondition['operator']} {expected}"


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
        assertions = "；".join(_display_postcondition(item) for item in step["postconditions"])
        lines.append(f"| {step['sequence']} | {step['intent']} | {parameters} | {step['expected_result']}；断言：{assertions} |")
    return "\n".join(lines) + "\n"


def _render_playwright(source_case: dict[str, Any], parameter_manifest: dict[str, Any], resolved_steps: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    function_suffix = re.sub(r"[^0-9A-Za-z_]+", "_", f"{source_case['case_id']}_{source_case['branch_id']}").strip("_").lower()
    # 使用 Python 字面量而非 JSON 布尔值，确保生成模块可以直接导入执行。
    manifest_literal = pprint.pformat(parameter_manifest, sort_dicts=True, width=120)
    step_manifest_literal = pprint.pformat(resolved_steps, sort_dicts=True, width=120)
    metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"# 生成元数据: {metadata_json}\n"
        "# CASE_PARAMETER_MANIFEST 由 test-data.json 编译生成，禁止在本文件手工维护。\n"
        "import pytest\n\n"
        f"pytestmark = [pytest.mark.{source_case['priority'].lower()}, pytest.mark.ui_test, pytest.mark.{source_case['risk_level'].lower()}]\n\n"
        f"CASE_PARAMETER_MANIFEST = {manifest_literal}\n\n"
        f"CASE_STEP_MANIFEST = {step_manifest_literal}\n\n"
        f"@pytest.mark.case_id({source_case['case_id']!r})\n"
        f"@pytest.mark.branch_id({source_case['branch_id']!r})\n"
        f"def test_{function_suffix}(ui_test_runtime):\n"
        "    # 运行时必须先校验参数身份，再由项目场景消费清单。\n"
        f"    ui_test_runtime.execute_case(case_id={source_case['case_id']!r}, branch_id={source_case['branch_id']!r}, parameter_manifest=CASE_PARAMETER_MANIFEST, step_manifest=CASE_STEP_MANIFEST)\n"
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
    page_module_registry: Mapping[str, Any] | None = None,
    compiler_version: str = "2.0.0",
    renderer_version: str = "2.2.0",
) -> dict[str, Any]:
    """Compile one exact case+branch into an immutable v2 attachment set."""
    _prevalidate_step_contracts(source_case)
    _require_valid(source_case, "source-case-v2.schema.json", "E_SOURCE_CASE_V2_INVALID")
    if page_module_registry is None:
        raise CompileV2Error("E_PAGE_MODULE_REGISTRY_INVALID:missing")
    module_coverage = _validate_module_coverage(source_case, page_module_registry)
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
    resolved_steps = _resolve_steps(source_case, parameter_manifest, test_data)
    page_module_registry_digest = canonical_hash(page_module_registry)
    module_coverage_digest = canonical_hash(module_coverage)
    identity = {
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "runtime_material_digest": parameter_manifest["runtime_material_digest"],
        "dependency_digest": dependency_digest,
        "page_module_registry_digest": page_module_registry_digest,
        "module_coverage_digest": module_coverage_digest,
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
        "display_name": source_case["display_name"],
        "p0_suite_id": source_case["p0_suite_id"],
        "precondition_group": "|".join(sorted({step["binding_ref"] for step in source_case["steps"] if step["section"] == "setup" and step.get("binding_ref")})),
        "flow_refs": sorted({step["binding_ref"] for step in source_case["steps"] if step["section"] == "setup" and step.get("binding_ref")}),
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "scope": copy.deepcopy(source_case["scope"]),
        "priority": source_case["priority"],
        "risk_level": source_case["risk_level"],
        "steps": copy.deepcopy(source_case["steps"]),
        "dependency_refs": copy.deepcopy(source_case["dependency_refs"]),
        "module_coverage": copy.deepcopy(module_coverage),
    }
    resolved_ir = {
        "schema_version": "ui-test.resolved-ir.v2",
        "case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "dependency_digest": dependency_digest,
        "module_coverage": copy.deepcopy(module_coverage),
        "resolved_steps": resolved_steps,
    }
    metadata = {
        "source_case_id": source_case["case_id"],
        "branch_id": source_case["branch_id"],
        "source_hash": source_hash,
        "test_data_hash": test_data["test_data_hash"],
        "parameter_manifest_hash": parameter_manifest["parameter_manifest_hash"],
        "dependency_digest": dependency_digest,
        "config_fingerprint": config_fingerprint,
        "compiler_version": compiler_version,
        "renderer_version": renderer_version,
        "page_module_registry_digest": page_module_registry_digest,
        "module_coverage_digest": module_coverage_digest,
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
        "playwright-test.py": _render_playwright(source_case, parameter_manifest, resolved_steps, metadata),
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
        "page_module_registry_digest": page_module_registry_digest,
        "module_coverage_digest": module_coverage_digest,
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
