"""Versioned project configuration loader with explicit scope separation."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any

import rfc8785
from jsonschema import Draft202012Validator


class ProjectConfigError(ValueError):
    pass


SKILL_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SCOPE = ("project_group", "product", "environment")
FORBIDDEN_CONFIG_KEYS = {"password", "token", "cookie", "storagestate", "storage_state", "secret"}
V1_REQUIRED_TOP_LEVEL = (
    "schema_version",
    "scope",
    "systems",
    "runtime_env_keys",
    "checkpoint_runtime",
    "knowledge_space",
    "wait_strategy",
    "semantic_post_signatures",
    "execution_policies",
)
SCHEMA_FILES = {"1.0": "ui-test-project.schema.json", "2.0": "ui-test-project-v2.schema.json"}
EXPECTED_ROOTS = {
    "execution_asset_root": r"D:\UI-Test",
    "knowledge_root": r"D:\RAG",
    "staging_root": r"D:\UI-Test\_tmp",
}


def _load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ProjectConfigError("E_CONFIG_PARSER_MISSING: PyYAML is required for YAML project config") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ProjectConfigError("E_CONFIG_INVALID: root must be an object")
    return value


def load_project_config(path: str | Path, *, purpose: str = "write") -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise ProjectConfigError("E_CONFIG_MISSING: project config does not exist")
    value = _load_document(source)
    version = value.get("schema_version")
    if version not in SCHEMA_FILES:
        raise ProjectConfigError("E_CONFIG_VERSION_UNKNOWN: unsupported project config version")
    if purpose not in {"write", "inventory"}:
        raise ProjectConfigError("E_CONFIG_PURPOSE_INVALID: purpose must be write or inventory")
    if version == "2.0":
        governance = value.get("asset_governance")
        if isinstance(governance, dict):
            for field, expected in EXPECTED_ROOTS.items():
                if field in governance and _normalized_windows_path(governance[field]) != _normalized_windows_path(expected):
                    raise ProjectConfigError(f"E_PATH_ROOT_TYPE_MISMATCH: {field}")
    schema = json.loads((SKILL_ROOT / "schemas" / SCHEMA_FILES[version]).read_text(encoding="utf-8"))
    validation_errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.absolute_path))
    if validation_errors:
        path_text = "/" + "/".join(str(part) for part in validation_errors[0].absolute_path)
        raise ProjectConfigError(f"E_CONFIG_SCHEMA_INVALID: {path_text or '/'}")
    if version == "1.0" and purpose == "write":
        raise ProjectConfigError("E_CONFIG_UPGRADE_REQUIRED: v1 is inventory-only; v2 is required for writes")
    scope = value.get("scope")
    if version == "2.0":
        _validate_v2_governance(value)
    if scope["environment"] == "production":
        policies = value.get("execution_policies", [])
        if any(
            "write" in str(action).lower() or action in {"fill", "submit", "update", "delete", "approve", "publish"}
            for item in policies if isinstance(item, dict)
            for action in item.get("allow_actions", [])
        ):
            raise ProjectConfigError("E_POLICY_PRODUCTION_WRITE_BLOCK: production write policy is forbidden")
    secrets = _find_secret_keys(value)
    if secrets:
        raise ProjectConfigError("E_SECRET_DETECTED: config contains forbidden secret keys")
    if version == "1.0" and not _valid_systems(value.get("systems")):
        raise ProjectConfigError("E_CONFIG_SYSTEMS_INVALID: systems/modules/routes are required")
    result = dict(value)
    result["config_path"] = str(source)
    result["config_fingerprint"] = "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()
    result["runtime_env_keys"] = sorted(str(item) for item in value.get("runtime_env_keys", []))
    result["runtime_env_present"] = {key: bool(os.environ.get(key)) for key in result["runtime_env_keys"]}
    result["write_ready"] = version == "2.0"
    result["config_issues"] = [] if version == "2.0" else ["E_CONFIG_UPGRADE_REQUIRED"]
    return result


def _validate_v2_governance(value: dict[str, Any]) -> None:
    scope = value["scope"]
    if any(not isinstance(scope.get(key), str) or not scope[key] for key in REQUIRED_SCOPE):
        raise ProjectConfigError("E_CONFIG_SCOPE_INVALID: project_group/product/environment are required")
    governance = value["asset_governance"]
    for field, expected in EXPECTED_ROOTS.items():
        if _normalized_windows_path(governance.get(field, "")) != _normalized_windows_path(expected):
            raise ProjectConfigError(f"E_PATH_ROOT_TYPE_MISMATCH: {field}")
    knowledge_relative = PureWindowsPath(value["knowledge_space"]["relative_path"])
    if knowledge_relative.is_absolute() or knowledge_relative.drive or ".." in knowledge_relative.parts:
        raise ProjectConfigError("E_KNOWLEDGE_PATH_INVALID: relative_path must stay below D:\\RAG")
    expected_levels = ["project_group", "product", "system", "module_path", "function", "case", "branch", "run"]
    configured_levels = governance.get("levels", expected_levels)
    if configured_levels != expected_levels:
        raise ProjectConfigError("E_PATH_LAYOUT_INVALID: governed hierarchy cannot be reordered")
    seen_systems: set[str] = set()
    for system in value["systems"]:
        system_id = system["system_id"]
        if system_id in seen_systems:
            raise ProjectConfigError("E_CONFIG_SYSTEM_DUPLICATE: system_id must be unique")
        seen_systems.add(system_id)
        seen_paths: set[tuple[str, ...]] = set()
        for module in system["modules"]:
            module_ids = tuple(item["module_id"] for item in module["module_path"])
            if module_ids[-1] != module["module_id"] or module_ids in seen_paths:
                raise ProjectConfigError("E_CONFIG_MODULE_PATH_INVALID: module path must be unique and end with module_id")
            seen_paths.add(module_ids)
            function_ids = [item["function_id"] for item in module["functions"]]
            if len(function_ids) != len(set(function_ids)):
                raise ProjectConfigError("E_CONFIG_FUNCTION_DUPLICATE: function_id must be unique per module")
    for display_name in _collect_display_names(value):
        if _invalid_display_name(display_name):
            raise ProjectConfigError("E_PATH_DISPLAY_NAME_INVALID: display name is not Windows-safe")


def _normalized_windows_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(str(value).replace("/", "\\")))


def _collect_display_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"project_group_name", "product_name", "display_name"} and isinstance(child, str):
                names.append(child)
            names.extend(_collect_display_names(child))
    elif isinstance(value, list):
        for child in value:
            names.extend(_collect_display_names(child))
    return names


def _invalid_display_name(value: str) -> bool:
    return value in {".", ".."} or value.endswith((" ", ".")) or any(character in value for character in '<>:"/\\|?*')


def _find_secret_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_CONFIG_KEYS or any(token in lowered for token in FORBIDDEN_CONFIG_KEYS):
                findings.append(f"{path}.{key}")
            findings.extend(_find_secret_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_secret_keys(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        sensitive_markers = ("bearer ", "pass" + "word=", "to" + "ken=", "coo" + "kie=", "sk-")
        if any(marker in value.lower() for marker in sensitive_markers):
            findings.append(path)
    return findings


def _valid_systems(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for system in value:
        if not isinstance(system, dict) or not system.get("system_id") or not isinstance(system.get("modules"), list) or not system["modules"]:
            return False
        for module in system["modules"]:
            if not isinstance(module, dict) or not module.get("module_id"):
                return False
            if not isinstance(module.get("aliases"), list) or not module["aliases"]:
                return False
            if not (module.get("direct_route_ref") or module.get("locator_replay_ref")):
                return False
    return True
