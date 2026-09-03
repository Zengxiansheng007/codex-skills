"""Generate the product Human View and XMind outline from validated Case IR."""

from __future__ import annotations

import copy
import re
from typing import Any, Iterable

from .case_contracts import canonical_hash, validate_document
from .semantic_rules import validate_p0_suite


class AggregateError(ValueError):
    """Raised when a product aggregate cannot be generated safely."""


def render_product_aggregate(
    compiled_cases: Iterable[dict[str, Any]],
    *,
    display_registry: dict[str, dict[str, str]] | None = None,
    project_group_display_name: str | None = None,
    product_display_name: str | None = None,
    system_display_name: str | None = None,
    compiler_version: str = "1.0.0",
    renderer_version: str = "1.1.0",
    schema_version: str = "ui-test.case-ir.v1",
    config_fingerprint: str = "",
) -> dict[str, Any]:
    entries = [_validate_entry(item) for item in compiled_cases]
    if not entries:
        raise AggregateError("E_AGGREGATE_EMPTY")
    entries.sort(key=_case_sort_key)
    first_scope = entries[0]["case_ir"]["scope"]
    _assert_same_scope(entries, first_scope)
    context = _resolve_display_context(
        first_scope, entries, display_registry=display_registry,
        project_group_display_name=project_group_display_name,
        product_display_name=product_display_name,
        system_display_name=system_display_name,
    )
    p0_issues = validate_p0_suite([item["case_ir"] for item in entries])
    if any(issue.get("blocking") for issue in p0_issues):
        raise AggregateError("E_AGGREGATE_P0_COVERAGE")
    if len({item["case_ir"]["case_id"] for item in entries}) != len(entries):
        raise AggregateError("E_AGGREGATE_DUPLICATE_CASE")
    outline = _build_outline(context, entries)
    markdown = _render_markdown(outline)
    included = [
        {"case_id": item["case_ir"]["case_id"], "branch_id": item["case_ir"].get("branch_id"),
         "priority": item["case_ir"]["priority"], "source_hash": item["case_ir"]["source_hash"],
         "case_manifest_hash": canonical_hash(item["manifest"])}
        for item in entries
    ]
    manifest = {
        "schema_version": "ui-test.product-aggregate-manifest.v1", "status": "in_sync",
        "is_unmodified": True, "project_group_display_name": context["project_group_display_name"],
        "product_display_name": context["product_display_name"], "system_display_name": context["system_display_name"],
        "scope": {"project_group": first_scope["project_group"], "product": first_scope["product"],
                   "system": first_scope["system"], "module_path": copy.deepcopy(first_scope["module_path"])},
        "included_cases": included, "compiler_version": compiler_version, "renderer_version": renderer_version,
        "schema_version_source": schema_version, "config_fingerprint": config_fingerprint,
        "markdown_hash": canonical_hash(markdown), "outline_hash": canonical_hash(outline),
    }
    safe_name = _safe_filename(context["product_display_name"])
    return {"outputs": {f"{safe_name}.总测试用例.md": markdown, f"{safe_name}.总测试用例.outline.json": outline},
            "outline": outline, "manifest": manifest, "included_cases": included}


def render_product_aggregate_v2(
    compiled_cases: Iterable[dict[str, Any]],
    *,
    display_registry: dict[str, dict[str, str]],
    config_fingerprint: str,
    compiler_version: str = "2.0.0",
    renderer_version: str = "2.2.0",
) -> dict[str, Any]:
    """从已验证的 v2 Case/Resolved IR 构造产品树，而不是拼接单用例 Human View。"""
    raw_entries = list(compiled_cases)
    if not raw_entries:
        raise AggregateError("E_AGGREGATE_EMPTY")
    entries = [_normalize_v2_entry(item) for item in raw_entries]
    entries.sort(key=_case_sort_key)
    first_scope = entries[0]["case_ir"]["scope"]
    _assert_same_scope(entries, first_scope)
    context = _resolve_display_context(
        first_scope,
        entries,
        display_registry=display_registry,
        project_group_display_name=None,
        product_display_name=None,
        system_display_name=None,
    )
    if len({item["case_ir"]["case_id"] for item in entries}) != len(entries):
        raise AggregateError("E_AGGREGATE_DUPLICATE_CASE")
    outline = _build_outline(context, entries)
    markdown = _render_markdown(outline)
    included = [
        {
            "case_id": item["case_ir"]["case_id"],
            "branch_id": item["case_ir"]["branch_id"],
            "priority": item["case_ir"]["priority"],
            "source_hash": item["case_ir"]["source_hash"],
            "test_data_hash": item["case_ir"]["test_data_hash"],
            "parameter_manifest_hash": item["case_ir"]["parameter_manifest_hash"],
            "case_manifest_hash": canonical_hash(item["manifest"]),
            "build_fingerprint": item["manifest"]["build_fingerprint"],
        }
        for item in entries
    ]
    manifest = {
        "schema_version": "ui-test.product-aggregate-manifest.v2",
        "status": "in_sync",
        "is_unmodified": True,
        "project_group_display_name": context["project_group_display_name"],
        "product_id": context["product_id"],
        "product_display_name": context["product_display_name"],
        "system_display_name": context["system_display_name"],
        "scope": {
            "project_group": first_scope["project_group"],
            "product": first_scope["product"],
            "system": first_scope["system"],
            "module_path": copy.deepcopy(first_scope["module_path"]),
            "function": first_scope["function"],
        },
        "included_cases": included,
        "compiler_version": compiler_version,
        "renderer_version": renderer_version,
        "config_fingerprint": config_fingerprint,
        "markdown_hash": canonical_hash(markdown),
        "outline_hash": canonical_hash(outline),
    }
    manifest["aggregate_hash"] = canonical_hash(manifest)
    if validate_document(outline, "product-outline-v2.schema.json"):
        raise AggregateError("E_AGGREGATE_OUTLINE_V2_INVALID")
    if validate_document(manifest, "product-aggregate-manifest-v2.schema.json"):
        raise AggregateError("E_AGGREGATE_MANIFEST_V2_INVALID")
    safe_name = _safe_filename(context["product_display_name"])
    return {
        "outputs": {f"{safe_name}.总测试用例.md": markdown, f"{safe_name}.总测试用例.outline.json": outline},
        "outline": outline,
        "manifest": manifest,
        "included_cases": included,
    }


def _normalize_v2_entry(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AggregateError("E_AGGREGATE_ENTRY_INVALID")
    case_ir = item.get("case_ir")
    resolved_ir = item.get("resolved_ir")
    manifest = item.get("manifest")
    release_state = item.get("release_state")
    if not all(isinstance(value, dict) for value in (case_ir, resolved_ir, manifest, release_state)):
        raise AggregateError("E_AGGREGATE_ENTRY_CONTRACT")
    if validate_document(case_ir, "case-ir-v2.schema.json"):
        raise AggregateError(f"E_AGGREGATE_CASE_IR_INVALID:{case_ir.get('case_id', 'unknown')}")
    if validate_document(resolved_ir, "resolved-ir-v2.schema.json"):
        raise AggregateError(f"E_AGGREGATE_RESOLVED_IR_INVALID:{case_ir['case_id']}")
    if validate_document(manifest, "case-manifest-v2.schema.json"):
        raise AggregateError(f"E_AGGREGATE_CASE_MANIFEST_INVALID:{case_ir['case_id']}")
    if release_state.get("release_integrity") != "valid" or release_state.get("input_sync") != "in_sync" or release_state.get("execution_gate") != "ready":
        raise AggregateError(f"E_AGGREGATE_CASE_NOT_IN_SYNC:{case_ir['case_id']}")
    if manifest.get("source_hash") != case_ir.get("source_hash") or resolved_ir.get("source_hash") != case_ir.get("source_hash"):
        raise AggregateError(f"E_AGGREGATE_SOURCE_HASH_MISMATCH:{case_ir['case_id']}")
    normalized = copy.deepcopy(case_ir)
    normalized["normalized_steps"] = copy.deepcopy(resolved_ir["resolved_steps"])
    return {"case_ir": normalized, "resolved_ir": copy.deepcopy(resolved_ir), "manifest": copy.deepcopy(manifest), "release_state": copy.deepcopy(release_state)}


def _validate_entry(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AggregateError("E_AGGREGATE_ENTRY_INVALID")
    case_ir, manifest = item.get("case_ir"), item.get("manifest")
    if not isinstance(case_ir, dict) or not isinstance(manifest, dict):
        raise AggregateError("E_AGGREGATE_ENTRY_CONTRACT")
    if validate_document(case_ir, "case-ir.schema.json"):
        raise AggregateError(f"E_AGGREGATE_CASE_IR_INVALID:{case_ir.get('case_id', 'unknown')}")
    if manifest.get("status") != "in_sync":
        raise AggregateError(f"E_AGGREGATE_CASE_NOT_IN_SYNC:{case_ir['case_id']}")
    if manifest.get("source_hash") != case_ir.get("source_hash"):
        raise AggregateError(f"E_AGGREGATE_SOURCE_HASH_MISMATCH:{case_ir['case_id']}")
    return {"case_ir": case_ir, "manifest": manifest}


def _case_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    case_ir, scope = item["case_ir"], item["case_ir"]["scope"]
    return (tuple(scope["module_path"]), scope["function"], case_ir["priority"], case_ir["case_id"], case_ir.get("branch_id") or "")


def _assert_same_scope(entries: list[dict[str, Any]], first_scope: dict[str, Any]) -> None:
    expected = (first_scope["project_group"], first_scope["product"], first_scope["system"], tuple(first_scope["module_path"]))
    for item in entries:
        scope = item["case_ir"]["scope"]
        actual = (scope["project_group"], scope["product"], scope["system"], tuple(scope["module_path"]))
        if actual != expected:
            raise AggregateError(f"E_AGGREGATE_SCOPE_MISMATCH:{item['case_ir']['case_id']}")


def _resolve_display_context(scope: dict[str, Any], entries: list[dict[str, Any]], *, display_registry: dict[str, dict[str, str]] | None,
                             project_group_display_name: str | None, product_display_name: str | None,
                             system_display_name: str | None) -> dict[str, Any]:
    registry = display_registry or {}

    def resolve(kind: str, stable_id: str, explicit: str | None = None) -> str:
        value = explicit or registry.get(kind, {}).get(stable_id)
        if not isinstance(value, str) or not value.strip():
            raise AggregateError(f"E_AGGREGATE_DISPLAY_NAME_MISSING:{kind}:{stable_id}")
        return value.strip()

    return {
        "project_group_id": scope["project_group"],
        "project_group_display_name": resolve("project_groups", scope["project_group"], project_group_display_name),
        "product_id": scope["product"], "product_display_name": resolve("products", scope["product"], product_display_name),
        "system_id": scope["system"], "system_display_name": resolve("systems", scope["system"], system_display_name),
        "module_display_names": {mid: resolve("modules", mid) for mid in scope["module_path"]},
        "function_display_name": resolve("functions", scope["function"]),
        "case_display_names": {item["case_ir"]["case_id"]: str(item["case_ir"].get("display_name", "")).strip() for item in entries},
    }


def _build_outline(context: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    root = _node("project-group", context["project_group_display_name"], "project-group|" + context["project_group_id"], [], context["project_group_id"])
    product = _node("product", context["product_display_name"], "product|" + context["product_id"], [], context["product_id"])
    system = _node("system", context["system_display_name"], "system|" + context["system_id"], [], context["system_id"])
    root["children"].append(product); product["children"].append(system)
    groups: dict[tuple[str, ...], dict[str, Any]] = {}; function_entries: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in entries:
        case_ir, scope = item["case_ir"], item["case_ir"]["scope"]
        path = tuple(scope["module_path"]); parent = system; prefix: list[str] = []
        for segment in path:
            prefix.append(segment); key = tuple(prefix); child = groups.get(key)
            if child is None:
                child = _node("module", context["module_display_names"][segment], "module|" + "|".join(prefix), [], segment)
                groups[key] = child; parent["children"].append(child)
            parent = child
        function_key = path + ("@function", scope["function"]); function_node = groups.get(function_key)
        if function_node is None:
            function_node = _node("function", context["function_display_name"], "function|" + "|".join(function_key), [], scope["function"])
            groups[function_key] = function_node; parent["children"].append(function_node)
        function_entries.setdefault(function_key, []).append(item)
    for key, items in function_entries.items():
        node = groups[key]
        for group_id, grouped in _group_preconditions(items): node["children"].append(_build_common_precondition_node(group_id, grouped))
        for item in sorted(items, key=_case_sort_key): node["children"].append(_build_case_node(item["case_ir"], context))
    return root


def _group_preconditions(entries: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        group_id = item["case_ir"].get("precondition_group")
        if not isinstance(group_id, str) or not group_id.strip(): raise AggregateError(f"E_COMMON_PRECONDITION_GROUP_MISSING:{item['case_ir']['case_id']}")
        grouped.setdefault(group_id, []).append(item)
    return sorted(grouped.items(), key=lambda pair: pair[0])


def _build_common_precondition_node(group_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    first = entries[0]["case_ir"]; setup = [step for step in first["normalized_steps"] if step["section"] == "setup"]; expected = canonical_hash(setup)
    for item in entries[1:]:
        actual = [step for step in item["case_ir"]["normalized_steps"] if step["section"] == "setup"]
        if canonical_hash(actual) != expected: raise AggregateError(f"E_COMMON_PRECONDITION_CONFLICT:{group_id}")
    node = _node("common-preconditions", "公共前置操作", "common-preconditions|" + group_id, [], group_id)
    node["source_ref"] = {"precondition_group": group_id, "flow_refs": copy.deepcopy(first["flow_refs"]), "case_ids": [item["case_ir"]["case_id"] for item in entries]}
    for index, step in enumerate(setup, 1): node["children"].append(_build_step_node(first["case_id"], "common-preconditions", index, step))
    return node


def _build_case_node(case_ir: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    case_id = case_ir["case_id"]; display_name = context["case_display_names"].get(case_id, "")
    if not display_name: raise AggregateError(f"E_AGGREGATE_DISPLAY_NAME_MISSING:case:{case_id}")
    node = _node("case", display_name, "case|" + case_id, [], case_id)
    node.update({"priority": case_ir["priority"], "branch_id": case_ir.get("branch_id"), "is_unmodified": True,
                 "source_ref": {"case_id": case_id, "source_hash": case_ir["source_hash"]}})
    node["children"].append(_label_node("metadata", "是否未修改：True", "case|" + case_id + "|is_unmodified"))
    node["children"].append(_label_node("metadata", f"用例编号：{case_id}", "case|" + case_id + "|case-id"))
    for section, label in (("special_preconditions", "特殊前置操作"), ("feature", "操作"), ("assertions", "断言")):
        steps = [step for step in case_ir["normalized_steps"] if step["section"] == section]
        if not steps: continue
        section_node = _node("section", label, f"case|{case_id}|{section}", [])
        for index, step in enumerate(steps, 1): section_node["children"].append(_build_step_node(case_id, section, index, step))
        node["children"].append(section_node)
    return node


def _build_step_node(case_id: str, section: str, index: int, step: dict[str, Any]) -> dict[str, Any]:
    step_id = step["source_step_id"]; node = _node("operation", f"操作{index}：{step['intent']}", f"step|{case_id}|{step_id}", [])
    node["source_ref"] = {"case_id": case_id, "step_id": step_id, "section": section}
    parameter_node = _node("parameters", "参数/数据", f"step|{case_id}|{step_id}|parameters", [])
    parameters = step.get("parameters", [])
    if parameters:
        for p_index, parameter in enumerate(parameters, 1): parameter_node["children"].append(_label_node("parameter", _format_parameter(parameter), f"step|{case_id}|{step_id}|parameter|{p_index}"))
    else: parameter_node["children"].append(_label_node("parameter", "无", f"step|{case_id}|{step_id}|parameter|empty"))
    node["children"].append(parameter_node)
    assertions = []
    for item in step.get("postconditions", []):
        expected = item.get("expected_value", item.get("expected_reference", item.get("expected_ref", "")))
        assertions.append(f"{item['assertion_id']} {item['operator']} {expected}")
    expected_label = f"预期：{step['expected_result']}"
    if assertions:
        expected_label += "；断言：" + "；".join(assertions)
    node["children"].append(_label_node("expected", expected_label, f"step|{case_id}|{step_id}|expected"))
    return node


def _node(node_type: str, label: str, node_id: str, children: list[dict[str, Any]], stable_id: str | None = None) -> dict[str, Any]:
    node = {"node_id": node_id, "node_type": node_type, "label": label, "children": children}
    if stable_id is not None: node["stable_id"] = stable_id
    return node


def _label_node(node_type: str, label: str, node_id: str) -> dict[str, Any]: return _node(node_type, label, node_id, [])


def _format_parameter(parameter: dict[str, Any]) -> str:
    label = str(parameter.get("label", "")).strip()
    if parameter.get("reference_only"):
        value = str(parameter.get("ref", "")).strip()
    else:
        value = str(parameter.get("display_value", parameter.get("value", ""))).strip()
    pieces = [f"{label}：{value}" if label else value]
    index_ref = str(parameter.get("index_ref", "")).strip()
    if index_ref: pieces.append(f"索引：{index_ref}")
    source_type = str(parameter.get("source_type", "")).strip()
    if source_type: pieces.append(f"来源：{source_type}")
    if parameter.get("sensitive"): pieces.append("脱敏")
    notes = str(parameter.get("notes", "")).strip()
    if notes: pieces.append(notes)
    return "；".join(piece.replace("\n", " ").strip() for piece in pieces if piece.strip())


def _render_markdown(outline: dict[str, Any]) -> str:
    lines = [f"# {outline['label']}", ""]
    for child in outline["children"]: _render_node(child, lines, 0)
    return "\n".join(lines).rstrip() + "\n"


def _render_node(node: dict[str, Any], lines: list[str], depth: int) -> None:
    lines.append(f"{'  ' * depth}- {_markdown_label(node)}")
    for child in node.get("children", []): _render_node(child, lines, depth + 1)


def _markdown_label(node: dict[str, Any]) -> str: return f"{node['priority']}-{node['label']}" if node["node_type"] == "case" else node["label"]


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip(" .")
    return cleaned or "product"
