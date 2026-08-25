"""Governed UI-Test asset paths with fixed asset-type to root mapping."""

from __future__ import annotations

import ntpath
import os
import re
from pathlib import Path, PureWindowsPath
from typing import Any


class PathPlanningError(ValueError):
    pass


_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
_REPARSE_POINT = 0x400

ASSET_TYPES: dict[str, dict[str, Any]] = {
    "project_config": {"root": "execution", "path": ("_shared", "config", "ui-test.project.yaml")},
    "shared_flow": {"root": "execution", "path": ("_shared", "flows"), "ref": True, "ext": ".json"},
    "shared_page": {"root": "execution", "path": ("_shared", "pages"), "ref": True, "ext": ".py"},
    "shared_component": {"root": "execution", "path": ("_shared", "components"), "ref": True, "ext": ".py"},
    "shared_binding": {"root": "execution", "path": ("_shared", "bindings"), "ref": True, "ext": ".json"},
    "source_case": {"root": "execution", "case": True, "path": ("source", "source-case.json")},
    "resolved_case": {"root": "execution", "case": True, "path": ("resolved", "resolved-case.json")},
    "human_view": {"root": "execution", "case": True, "path": ("views", "human.md")},
    "midscene_view": {"root": "execution", "case": True, "path": ("views", "midscene.json")},
    "playwright_test": {"root": "execution", "case": True, "path": ("tests",), "case_filename": True},
    "case_manifest": {"root": "execution", "case": True, "path": ("manifest.json",)},
    "run_result": {"root": "execution", "run": True, "path": ("run-result.json",)},
    "run_evidence": {"root": "execution", "run": True, "path": ("evidence",), "ref": True},
    "run_report": {"root": "execution", "run": True, "path": ("report", "report.html")},
    "run_trace": {"root": "execution", "run": True, "path": ("trace", "trace.zip")},
    "staging": {"root": "staging", "run": True, "path": ()},
    "experience_candidate": {"root": "knowledge", "path": ("candidate",), "ref": True, "ext": ".json"},
    "experience_observed": {"root": "knowledge", "path": ("observed",), "ref": True, "ext": ".json"},
    "knowledge_evidence_index": {"root": "knowledge", "path": ("indexes", "evidence"), "ref": True, "ext": ".json"},
    "knowledge_reference": {"root": "knowledge", "path": ("references",), "ref": True, "ext": ".md"},
}


def plan_asset_path(config: dict[str, Any], asset_type: str, selection: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema_version") != "2.0" or not config.get("write_ready"):
        raise PathPlanningError("E_CONFIG_NOT_WRITE_READY")
    spec = ASSET_TYPES.get(asset_type)
    if spec is None:
        raise PathPlanningError("E_ASSET_TYPE_UNKNOWN")
    if {"root", "target_root", "output_dir", "target_path"}.intersection(selection):
        raise PathPlanningError("E_CALLER_ROOT_FORBIDDEN")
    scope_parts, resolved = _resolve_scope(config, selection)
    governance = config["asset_governance"]
    root_kind = spec["root"]
    if root_kind == "execution":
        root = PureWindowsPath(governance["execution_asset_root"])
        parts = scope_parts
    elif root_kind == "knowledge":
        root = PureWindowsPath(governance["knowledge_root"])
        relative = PureWindowsPath(config["knowledge_space"]["relative_path"])
        parts = list(relative.parts)
    else:
        root = PureWindowsPath(governance["staging_root"])
        parts = scope_parts
    if spec.get("case"):
        parts.extend(["cases", _required_identifier(selection, "case_id", _RUN_ID), "branches", _required_identifier(selection, "branch_id", _RUN_ID)])
    if spec.get("run"):
        run_id = _required_identifier(selection, "run_id", _RUN_ID)
        year = str(selection.get("year", ""))
        month = str(selection.get("month", ""))
        if not re.fullmatch(r"20\d{2}", year) or not re.fullmatch(r"0[1-9]|1[0-2]", month):
            raise PathPlanningError("E_RUN_PARTITION_INVALID")
        parts.extend([
            "cases", _required_identifier(selection, "case_id", _RUN_ID),
            "branches", _required_identifier(selection, "branch_id", _RUN_ID),
            "runs", year, month, run_id,
        ])
        if root_kind == "staging":
            parts.append(asset_type)
    parts.extend(spec["path"])
    if spec.get("case_filename"):
        parts.append("test_" + _required_identifier(selection, "case_id", _RUN_ID).lower().replace("-", "_").replace(".", "_") + ".py")
    if spec.get("ref"):
        reference = _required_identifier(selection, "asset_id", _RUN_ID)
        parts.append(reference + spec.get("ext", ""))
    target = root.joinpath(*parts)
    _assert_windows_containment(root, target)
    return {
        "schema_version": "ui-test.path-plan.v1",
        "asset_type": asset_type,
        "root_kind": root_kind,
        "root": str(root),
        "target_path": str(target),
        "scope": resolved,
        "caller_selected_root": False,
    }


def validate_existing_path_containment(root: str | Path, target: str | Path) -> None:
    root_path = Path(root).resolve(strict=True)
    target_path = Path(target)
    candidate = target_path.resolve(strict=False)
    try:
        candidate.relative_to(root_path)
    except ValueError as error:
        raise PathPlanningError("E_PATH_OUTSIDE_ROOT") from error
    current = target_path
    existing: list[Path] = []
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if current == current.parent:
            break
        current = current.parent
    for item in reversed(existing):
        try:
            attributes = getattr(item.lstat(), "st_file_attributes", 0)
        except OSError as error:
            raise PathPlanningError("E_PATH_INSPECTION_FAILED") from error
        is_junction = bool(getattr(item, "is_junction", lambda: False)())
        if item.is_symlink() or is_junction or attributes & _REPARSE_POINT:
            raise PathPlanningError("E_PATH_REPARSE_POINT_BLOCKED")


def is_ui_test_project_asset(asset_type: str) -> bool:
    return asset_type in ASSET_TYPES


def _resolve_scope(config: dict[str, Any], selection: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    scope = config["scope"]
    system_id = _required_identifier(selection, "system", _STABLE_ID)
    module_ids = selection.get("module_path")
    function_id = _required_identifier(selection, "function", _STABLE_ID)
    if not isinstance(module_ids, list) or not module_ids or any(not isinstance(item, str) for item in module_ids):
        raise PathPlanningError("E_MODULE_PATH_REQUIRED")
    system = next((item for item in config["systems"] if item["system_id"] == system_id), None)
    if system is None:
        raise PathPlanningError("E_SYSTEM_UNKNOWN")
    module = next((item for item in system["modules"] if [part["module_id"] for part in item["module_path"]] == module_ids), None)
    if module is None:
        raise PathPlanningError("E_MODULE_PATH_UNKNOWN")
    function = next((item for item in module["functions"] if item["function_id"] == function_id), None)
    if function is None:
        raise PathPlanningError("E_FUNCTION_UNKNOWN")
    parts = [
        _segment(scope["project_group"], scope["project_group_name"]),
        _segment(scope["product"], scope["product_name"]),
        _segment(system_id, system["display_name"]),
        *[_segment(part["module_id"], part["display_name"]) for part in module["module_path"]],
        _segment(function_id, function["display_name"]),
    ]
    resolved = {
        "project_group": scope["project_group"],
        "product": scope["product"],
        "system": system_id,
        "module_path": module_ids,
        "function": function_id,
    }
    return parts, resolved


def _segment(identifier: str, display_name: str) -> str:
    return f"{identifier}__{display_name}"


def _required_identifier(selection: dict[str, Any], field: str, pattern: re.Pattern[str]) -> str:
    value = selection.get(field)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise PathPlanningError(f"E_{field.upper()}_INVALID")
    return value


def _assert_windows_containment(root: PureWindowsPath, target: PureWindowsPath) -> None:
    root_text = ntpath.normcase(ntpath.normpath(str(root)))
    target_text = ntpath.normcase(ntpath.normpath(str(target)))
    try:
        if ntpath.commonpath([root_text, target_text]) != root_text:
            raise PathPlanningError("E_PATH_OUTSIDE_ROOT")
    except ValueError as error:
        raise PathPlanningError("E_PATH_OUTSIDE_ROOT") from error
