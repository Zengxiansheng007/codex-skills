"""Deterministic UI-Test dependency graph, compiler and local release state."""

from __future__ import annotations

import copy
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .case_contracts import canonical_hash, validate_document


class CompileError(ValueError):
    pass


ASSET_TYPES = {"flow", "page", "component", "binding"}
STATUS_VALUES = {"in_sync", "source_stale", "dependency_stale", "manual_drift", "binding_missing", "binding_incompatible", "generation_failed", "plan_stale", "concurrent_update"}


def build_dependency_graph(registry: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    assets = registry.get("assets")
    if not isinstance(assets, list):
        raise CompileError("E_DEPENDENCY_REGISTRY_INVALID")
    by_id: dict[str, dict[str, Any]] = {}
    for asset in assets:
        asset_id = asset.get("id") if isinstance(asset, dict) else None
        if not isinstance(asset_id, str) or not asset_id or asset_id in by_id:
            raise CompileError("E_DEPENDENCY_ID_INVALID")
        if asset.get("type") not in ASSET_TYPES or not isinstance(asset.get("version"), int):
            raise CompileError("E_DEPENDENCY_CONTRACT_INVALID")
        by_id[asset_id] = copy.deepcopy(asset)
    edges: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = {asset_id: [] for asset_id in by_id}
    for asset_id, asset in by_id.items():
        dependencies = sorted(set(asset.get("depends_on", [])))
        if any(item not in by_id for item in dependencies):
            raise CompileError("E_DEPENDENCY_MISSING")
        edges[asset_id] = dependencies
        for dependency in dependencies:
            reverse[dependency].append(asset_id)
    _assert_acyclic(edges)
    case_refs: dict[str, list[str]] = {}
    for case in cases:
        case_id = case.get("case_id")
        refs = sorted(set(case.get("dependency_refs", [])))
        if not isinstance(case_id, str) or not case_id or any(item not in by_id for item in refs):
            raise CompileError("E_CASE_DEPENDENCY_INVALID")
        case_refs[case_id] = refs
    return {
        "schema_version": "ui-test.dependency-graph.v1", "assets": by_id, "edges": edges,
        "reverse_edges": {key: sorted(value) for key, value in reverse.items()}, "case_refs": case_refs,
        "registry_digest": canonical_hash({"assets": assets}),
    }


def affected_cases(graph: dict[str, Any], changed_asset_ids: list[str]) -> dict[str, Any]:
    unknown = sorted(set(changed_asset_ids) - set(graph["assets"]))
    if unknown:
        raise CompileError("E_DEPENDENCY_UNKNOWN")
    affected_assets = set(changed_asset_ids)
    queue = list(changed_asset_ids)
    while queue:
        current = queue.pop(0)
        for dependent in graph["reverse_edges"].get(current, []):
            if dependent not in affected_assets:
                affected_assets.add(dependent)
                queue.append(dependent)
    cases = sorted(case_id for case_id, refs in graph["case_refs"].items() if affected_assets.intersection(refs))
    return {"schema_version": "ui-test.affected-cases.v1", "changed_assets": sorted(set(changed_asset_ids)), "affected_assets": sorted(affected_assets), "affected_cases": cases}


def compile_case(
    case_ir: dict[str, Any], graph: dict[str, Any], *, compiler_version: str,
    renderer_version: str, schema_version: str, config_fingerprint: str,
) -> dict[str, Any]:
    schema_issues = validate_document(case_ir, "case-ir.schema.json")
    if schema_issues:
        raise CompileError("E_CASE_IR_INVALID")
    case_id = case_ir["case_id"]
    direct_refs = graph["case_refs"].get(case_id)
    if direct_refs is None:
        raise CompileError("E_CASE_DEPENDENCY_INVALID")
    closure = _dependency_closure(graph, direct_refs)
    referenced_assets = {key: graph["assets"][key] for key in closure}
    resolved_steps = []
    for step in case_ir["normalized_steps"]:
        binding_ref = step.get("binding_ref")
        binding = referenced_assets.get(binding_ref) if binding_ref else None
        if binding_ref and binding is None:
            raise CompileError(f"E_BINDING_MISSING:{binding_ref}")
        if binding is not None:
            compatible_flow = binding.get("type") == "flow" and step["action"] == "flow"
            compatible_action = binding.get("type") == "binding" and binding.get("action") == step["action"] and binding.get("risk_level") == step["risk_level"]
            if not (compatible_flow or compatible_action):
                raise CompileError(f"E_BINDING_INCOMPATIBLE:{binding_ref}")
        resolved_steps.append({
            "resolved_step_id": f"RS-{step['sequence']:03d}", "source_step_id": step["source_step_id"],
            "section": step["section"], "sequence": step["sequence"], "intent": step["intent"],
            "action": step["action"], "binding_ref": binding_ref,
            "binding_target": (binding.get("target") or binding_ref) if binding else None,
            "expected_result": step["expected_result"], "risk_level": step["risk_level"],
            "required": step["required"], "parameters": step.get("parameters", []), "evidence": step.get("evidence", []),
        })
    dependency_material = [{"id": key, "version": graph["assets"][key]["version"], "content_hash": canonical_hash(graph["assets"][key].get("content", graph["assets"][key]))} for key in closure]
    dependency_digest = canonical_hash(dependency_material)
    identity = {
        "source_hash": case_ir["source_hash"], "dependency_digest": dependency_digest,
        "compiler_version": compiler_version, "renderer_version": renderer_version,
        "schema_version": schema_version, "config_fingerprint": config_fingerprint,
    }
    build_fingerprint = canonical_hash(identity)
    resolved_ir = {
        "schema_version": "ui-test.resolved-ir.v1", "case_id": case_id, "source_hash": case_ir["source_hash"],
        "dependency_digest": dependency_digest, "resolved_steps": resolved_steps,
        "flow_versions": {key: graph["assets"][key]["version"] for key in closure if graph["assets"][key]["type"] == "flow"},
        "binding_versions": {key: graph["assets"][key]["version"] for key in closure if graph["assets"][key]["type"] == "binding"},
        "risk_mapping": {item["resolved_step_id"]: item["risk_level"] for item in resolved_steps},
        "evidence_mapping": {item["resolved_step_id"]: item["evidence"] for item in resolved_steps},
    }
    outputs = _render_outputs(case_ir, resolved_ir, build_fingerprint, compiler_version, renderer_version)
    manifest = {
        "schema_version": "ui-test.case-manifest.v1", "case_id": case_id, "case_version": case_ir["case_version"],
        "source_hash": case_ir["source_hash"], "dependency_digest": dependency_digest,
        "build_fingerprint": build_fingerprint, "status": "in_sync", "generated_from": "Source Case",
        "generator_version": compiler_version, "renderer_version": renderer_version, "do_not_edit": True,
        "artifacts": {name: canonical_hash(content) for name, content in outputs.items()},
    }
    receipt = {
        "schema_version": "ui-test.compile-receipt.v1", "case_id": case_id, "build_fingerprint": build_fingerprint,
        "source_hash": case_ir["source_hash"], "dependency_digest": dependency_digest,
        "compiler_version": compiler_version, "renderer_version": renderer_version,
        "schema_contract_version": schema_version, "config_fingerprint": config_fingerprint,
        "dependency_material": dependency_material, "byproducts": sorted(outputs),
    }
    return {"identity": identity, "case_ir": copy.deepcopy(case_ir), "resolved_ir": resolved_ir, "outputs": outputs, "manifest": manifest, "compile_receipt": receipt, "dependency_material": dependency_material}


def create_compile_plan(compiled: dict[str, Any], expected_active_build: str | None) -> dict[str, Any]:
    return {
        "schema_version": "ui-test.compile-plan.v1", "case_id": compiled["manifest"]["case_id"],
        "build_fingerprint": compiled["manifest"]["build_fingerprint"],
        "source_hash": compiled["manifest"]["source_hash"], "dependency_digest": compiled["manifest"]["dependency_digest"],
        "expected_active_build": expected_active_build, "input_fingerprint": canonical_hash(compiled["identity"]),
        "operations": ["write-immutable-release", "validate-release", "activate-pointer"],
    }


def sync_release(release_root: str | Path, plan: dict[str, Any], compiled: dict[str, Any], *, fail_after_files: int | None = None, audit_fixture: bool = False) -> dict[str, Any]:
    root = Path(release_root)
    root_text = str(root.resolve()).replace("/", "\\").lower()
    if not audit_fixture or root_text.startswith("d:\\ui-test\\"):
        # V1 仅保留审计和隔离 fixture 回归，不得再向正式 UI-Test 根发布或恢复执行资格。
        return {**_sync_result("generation_failed", None), "error_code": "E_LEGACY_V1_WRITE_FORBIDDEN"}
    root.mkdir(parents=True, exist_ok=True)
    active_path = root / "active.json"
    current = _read_json(active_path) if active_path.is_file() else None
    current_build = current.get("build_fingerprint") if isinstance(current, dict) else None
    if plan.get("input_fingerprint") != canonical_hash(compiled["identity"]):
        return _sync_result("plan_stale", current_build)
    if current_build != plan.get("expected_active_build"):
        return _sync_result("concurrent_update", current_build)
    build = compiled["manifest"]["build_fingerprint"]
    if current_build == build:
        return {**_sync_result("in_sync", current_build), "no_op": True}
    release = root / "releases" / build.removeprefix("sha256:")
    staging = root / "_staging" / build.removeprefix("sha256:")
    if release.exists():
        return _activate_existing(active_path, build, current_build)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        files = {**compiled["outputs"], "resolved-ir.json": compiled["resolved_ir"], "manifest.json": compiled["manifest"], "compile-receipt.json": compiled["compile_receipt"]}
        for index, (name, content) in enumerate(sorted(files.items()), 1):
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_serialize_artifact(content), encoding="utf-8", newline="\n")
            if fail_after_files is not None and index >= fail_after_files:
                raise RuntimeError("E_GENERATION_INJECTED_FAILURE")
        for name, expected in compiled["manifest"]["artifacts"].items():
            actual = _load_artifact(staging / name)
            if canonical_hash(actual) != expected:
                raise RuntimeError("E_RELEASE_VALIDATION_FAILED")
        release.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, release)
        pointer = {"schema_version": "ui-test.active-pointer.v1", "build_fingerprint": build, "manifest_ref": str(release / "manifest.json")}
        temporary = root / "active.next.json"
        temporary.write_text(json.dumps(pointer, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, active_path)
        if _read_json(active_path).get("build_fingerprint") != build:
            raise RuntimeError("E_ACTIVE_POINTER_READBACK_FAILED")
        return {**_sync_result("in_sync", build), "no_op": False, "release_path": str(release)}
    except Exception as error:
        if staging.exists():
            shutil.rmtree(staging)
        return {**_sync_result("generation_failed", current_build), "error_code": str(error)}


def validate_release(release_root: str | Path) -> dict[str, Any]:
    root = Path(release_root)
    active = _read_json(root / "active.json")
    manifest = _read_json(Path(active["manifest_ref"]))
    release = Path(active["manifest_ref"]).parent
    issues = []
    for name, expected in manifest.get("artifacts", {}).items():
        path = release / name
        if not path.is_file() or canonical_hash(_load_artifact(path)) != expected:
            issues.append({"code": "E_MANUAL_DRIFT", "path": name})
    return {"status": "in_sync" if not issues else "manual_drift", "issues": issues, "build_fingerprint": active["build_fingerprint"]}


def retention_metadata(asset_class: str, created_at: str, *, product_retired_at: str | None = None, legal_hold: bool = False, reference_hold: bool = False) -> dict[str, Any]:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if asset_class == "ordinary_raw_evidence":
        retain_until = created + timedelta(days=180)
    elif asset_class in {"event", "evidence_index", "failure", "security", "r2_r3_evidence"}:
        retain_until = created + timedelta(days=365)
    elif asset_class == "governance_decision":
        if not product_retired_at:
            return {"asset_class": asset_class, "retain_until": None, "disposition_status": "retirement-date-required", "hold": True}
        retain_until = datetime.fromisoformat(product_retired_at.replace("Z", "+00:00")) + timedelta(days=365)
    else:
        raise ValueError("E_RETENTION_CLASS_UNKNOWN")
    hold = legal_hold or reference_hold
    return {"asset_class": asset_class, "retain_until": retain_until.astimezone(UTC).isoformat().replace("+00:00", "Z"), "legal_hold": legal_hold, "reference_hold": reference_hold, "hold": hold, "disposition_status": "held" if hold else "eligible-after-retain-until", "automatic_delete": False}


def _render_outputs(case_ir: dict[str, Any], resolved_ir: dict[str, Any], build: str, compiler_version: str, renderer_version: str) -> dict[str, Any]:
    metadata = {"generated_from": "Source Case", "source_case_id": case_ir["case_id"], "source_hash": case_ir["source_hash"], "build_fingerprint": build, "generator_version": compiler_version, "renderer_version": renderer_version, "do_not_edit": True}
    sections = {"setup": [], "special_preconditions": [], "feature": [], "assertions": []}
    for step in resolved_ir["resolved_steps"]:
        sections[step["section"]].append({
            "step_id": step["source_step_id"], "intent": step["intent"], "action": step["action"],
            "parameters": step.get("parameters", []), "expected_result": step["expected_result"],
            "forbidden_actions": ["unapproved-write"] if step["risk_level"] != "R2" else ["api-write", "production-write", "second-submit"],
        })
    human_lines = ["<!-- do_not_edit: true -->", f"# {case_ir['case_id']}", ""]
    human_lines += _render_human_section("Fixed Preconditions", sections["setup"])
    human_lines += [""]
    if sections["special_preconditions"]:
        human_lines += _render_human_section("Special Preconditions", sections["special_preconditions"])
        human_lines += [""]
    human_lines += _render_human_section("Feature Steps", sections["feature"])
    human_lines += [""]
    human_lines += _render_human_section("Assertions", sections["assertions"])
    playwright = _render_pytest(case_ir, metadata)
    return {"human.md": "\n".join(human_lines) + "\n", "midscene.json": {"metadata": metadata, "sections": sections}, "playwright-test.py": playwright}


def _render_pytest(case_ir: dict[str, Any], metadata: dict[str, Any]) -> str:
    function_name = "test_" + "".join(character.lower() if character.isalnum() else "_" for character in case_ir["case_id"]).strip("_")
    header = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f'''# 生成元数据: {header}\nimport pytest\n\npytestmark = [pytest.mark.{case_ir["priority"].lower()}, pytest.mark.ui_test]\n\ndef {function_name}(ui_test_runtime):\n    ui_test_runtime.execute_case(case_id={case_ir["case_id"]!r}, branch_id={case_ir.get("branch_id")!r})\n'''


def _dependency_closure(graph: dict[str, Any], direct: list[str]) -> list[str]:
    result: set[str] = set()
    queue = list(direct)
    while queue:
        current = queue.pop(0)
        if current in result:
            continue
        result.add(current)
        queue.extend(graph["edges"].get(current, []))
    return sorted(result)


def _assert_acyclic(edges: dict[str, list[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise CompileError("E_DEPENDENCY_CYCLE")
        if node in visited:
            return
        visiting.add(node)
        for dependency in edges[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)
    for node in edges:
        visit(node)


def _serialize_artifact(content: Any) -> str:
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_artifact(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return text if path.suffix in {".md", ".py"} else json.loads(text)


# 即使使用不同代码页的控制台查看源文件，也要保持 Human View 文案稳定。
def _render_human_section(title: str, steps: list[dict[str, Any]]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| \u5e8f\u53f7 | \u64cd\u4f5c | \u53c2\u6570/\u6570\u636e | \u9884\u671f\u7ed3\u679c |",
        "| --- | --- | --- | --- |",
    ]
    for index, step in enumerate(steps, 1):
        lines.append(
            f"| {index} | {step['intent']} | "
            f"{_render_parameter_cell(step.get('parameters', []))} | "
            f"{step['expected_result']} |"
        )
    return lines


def _render_parameter_cell(parameters: list[dict[str, Any]]) -> str:
    if not parameters:
        return "-"
    rendered: list[str] = []
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        label = str(parameter.get("label", "")).strip()
        display_value = str(parameter.get("display_value", "")).strip()
        if not label and not display_value:
            continue
        pieces = [f"{label}\uff1a{display_value}" if label else display_value]
        index_ref = str(parameter.get("index_ref", "")).strip()
        if index_ref:
            pieces.append(f"\u7d22\u5f15\uff1a{index_ref}")
        source_type = str(parameter.get("source_type", "")).strip()
        if source_type:
            pieces.append(f"\u6765\u6e90\uff1a{source_type}")
        if parameter.get("sensitive"):
            pieces.append("\u8131\u654f")
        notes = str(parameter.get("notes", "")).strip()
        if notes:
            pieces.append(notes)
        rendered.append("\uff1b".join(pieces))
    return "\uff1b".join(rendered) if rendered else "-"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sync_result(status: str, active_build: str | None) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise ValueError(status)
    return {"schema_version": "ui-test.sync-result.v1", "status": status, "active_build": active_build}


def _activate_existing(active_path: Path, build: str, current_build: str | None) -> dict[str, Any]:
    return {**_sync_result("concurrent_update", current_build), "error_code": "E_RELEASE_EXISTS_WITHOUT_EXPECTED_ACTIVE", "candidate_build": build}
