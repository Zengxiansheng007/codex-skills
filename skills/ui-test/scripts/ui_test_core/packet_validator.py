"""Fail-closed JSON Schema and semantic validator for ui-test-packet v2."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "2.0"
SKILL_ROOT = Path(__file__).resolve().parents[2]
RISK_LEVELS = {"r0-read-only", "r1-read-only-authenticated", "r2-ui-write-test", "r3-high-impact"}
RISK_ORDER = {"r0-read-only": 0, "r1-read-only-authenticated": 1, "r2-ui-write-test": 2, "r3-high-impact": 3}
STATES = {"requirements-review", "plan", "preflight", "explore", "verify", "evidence", "review", "checkpoint", "learn", "report", "repair", "rerun", "blocked", "done"}
ACTIONS = {"login", "navigate", "module-ready", "click", "fill", "select", "check", "query", "assert", "explore", "verify", "screenshot", "observe-network", "submit", "update", "delete", "approve", "publish"}
READ_ONLY_RISKS = {"r0-read-only", "r1-read-only-authenticated"}
WRITE_ACTIONS = {"fill", "submit", "update", "delete", "approve", "publish"}
SCOPE_FIELDS = ("project_group", "product", "system", "function", "checkpoint", "environment", "risk_level")
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|token|cookie|authorization|storageState|storage_state)\s*[:=]"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def _problem(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def effective_risk_level(steps: list[dict[str, Any]], fallback: str | None = None) -> str | None:
    risks = [step.get("risk_level") for step in steps if isinstance(step, dict) and step.get("risk_level") in RISK_ORDER]
    if not risks:
        return fallback if fallback in RISK_ORDER else None
    return max(risks, key=lambda item: RISK_ORDER[item])


def validate_packet(packet: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(packet, dict):
        return [_problem("E_PACKET_TYPE", "$", "packet must be an object")]

    if packet.get("schema_version") == "1.0":
        return [_problem("E_PACKET_MIGRATION_REQUIRED", "$.schema_version", "packet v1 must pass through the governed migration adapter")]
    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(_problem("E_PACKET_VERSION_UNKNOWN", "$.schema_version", "unsupported schema_version"))
    else:
        schema = json.loads((SKILL_ROOT / "schemas" / "ui-test-packet-v2.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(packet), key=lambda item: list(item.absolute_path)):
            path = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
            errors.append(_problem("E_PACKET_SCHEMA", path, error.message))
    if packet.get("packet_type") != "ui-test-packet":
        errors.append(_problem("E_PACKET_TYPE_UNKNOWN", "$.packet_type", "packet_type must be ui-test-packet"))
    for field in ("packet_id", "scope", "risk_level", "state", "case", "branch", "run", "steps", "lineage", "evidence_policy", "retry_policy", "next_action"):
        if field not in packet:
            errors.append(_problem("E_PACKET_FIELD_MISSING", f"$.{field}", "required field is missing"))

    scope = packet.get("scope")
    if not isinstance(scope, dict):
        errors.append(_problem("E_SCOPE_INVALID", "$.scope", "scope must be an object"))
        scope = {}
    for field in SCOPE_FIELDS:
        if not isinstance(scope.get(field), str) or not scope.get(field):
            errors.append(_problem("E_SCOPE_FIELD_MISSING", f"$.scope.{field}", "scope field must be a non-empty string"))
    module_path = scope.get("module_path")
    if not isinstance(module_path, list) or not module_path or any(not isinstance(item, str) or not item for item in module_path):
        errors.append(_problem("E_SCOPE_MODULE_PATH_INVALID", "$.scope.module_path", "module_path must be a non-empty string array"))

    packet_risk = packet.get("risk_level")
    if packet_risk not in RISK_LEVELS:
        errors.append(_problem("E_RISK_UNKNOWN", "$.risk_level", "unknown risk_level"))
    if packet.get("state") not in STATES:
        errors.append(_problem("E_STATE_ILLEGAL", "$.state", "unknown or illegal lifecycle state"))
    if packet.get("next_action") not in {"route", "validate", "explore", "verify", "collect-evidence", "review", "promote-candidate", "repair", "rerun", "blocked", "complete"}:
        errors.append(_problem("E_ACTION_UNKNOWN", "$.next_action", "unknown next_action"))

    for name in ("case", "branch", "run"):
        value = packet.get(name)
        if not isinstance(value, dict) or not any(isinstance(item, str) and item for item in value.values()):
            errors.append(_problem("E_IDENTITY_MISSING", f"$.{name}", f"{name} must contain a non-empty identity"))
    steps = packet.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(_problem("E_STEPS_MISSING", "$.steps", "at least one step is required"))
        steps = []
    step_ids: list[str] = []
    for index, step in enumerate(steps):
        path = f"$.steps[{index}]"
        if not isinstance(step, dict):
            errors.append(_problem("E_STEP_INVALID", path, "step must be an object"))
            continue
        if not step.get("step_id"):
            errors.append(_problem("E_STEP_ID_MISSING", f"{path}.step_id", "step_id is required"))
        else:
            step_ids.append(step["step_id"])
        action = step.get("action")
        if action not in ACTIONS:
            errors.append(_problem("E_ACTION_UNKNOWN", f"{path}.action", "unknown step action"))
        step_risk = step.get("risk_level")
        if step_risk not in RISK_LEVELS:
            errors.append(_problem("E_RISK_UNKNOWN", f"{path}.risk_level", "unknown step risk_level"))
        if action in WRITE_ACTIONS and step_risk in READ_ONLY_RISKS:
            errors.append(_problem("E_RISK_ACTION_CONFLICT", f"{path}.risk_level", "write action must be classified as R2 or R3"))
        if step_risk == "r3-high-impact":
            errors.append(_problem("E_R3_BLOCKED", f"{path}.risk_level", "R3 steps are not accepted by ui-test packet validation"))
        if not isinstance(step.get("required"), bool):
            errors.append(_problem("E_STEP_REQUIRED_FLAG", f"{path}.required", "required must be boolean true/false"))
    if len(step_ids) != len(set(step_ids)):
        errors.append(_problem("E_STEP_ID_DUPLICATE", "$.steps", "step_id must be unique"))

    computed_risk = effective_risk_level(steps, packet_risk)
    declared_effective = packet.get("effective_risk_level", packet_risk)
    if declared_effective not in RISK_LEVELS:
        errors.append(_problem("E_RISK_UNKNOWN", "$.effective_risk_level", "unknown effective_risk_level"))
    elif computed_risk and declared_effective != computed_risk:
        errors.append(_problem("E_EFFECTIVE_RISK_MISMATCH", "$.effective_risk_level", "effective_risk_level must equal the highest step risk"))
    if scope.get("risk_level") not in {packet_risk, declared_effective}:
        errors.append(_problem("E_SCOPE_RISK_MISMATCH", "$.scope.risk_level", "scope risk_level must match packet risk_level or effective_risk_level"))

    if isinstance(packet.get("evidence_policy"), dict):
        policy = packet["evidence_policy"]
        if policy.get("screenshot_on_ui_change") is not True:
            errors.append(_problem("E_EVIDENCE_POLICY", "$.evidence_policy.screenshot_on_ui_change", "UI changes require screenshots"))
        if policy.get("redaction_required") is not True:
            errors.append(_problem("E_EVIDENCE_POLICY", "$.evidence_policy.redaction_required", "redaction is mandatory"))
    retry = packet.get("retry_policy")
    if isinstance(retry, dict) and (not isinstance(retry.get("max_attempts"), int) or retry.get("max_attempts") < 0 or retry.get("max_attempts") > 3):
        errors.append(_problem("E_RETRY_BUDGET_INVALID", "$.retry_policy.max_attempts", "max_attempts must be between 0 and 3"))
    lineage = packet.get("lineage")
    if not isinstance(lineage, dict) or not lineage.get("anchor_id"):
        errors.append(_problem("E_LINEAGE_MISSING", "$.lineage.anchor_id", "anchor_id is required"))

    for path, value in _walk_strings(packet):
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            errors.append(_problem("E_SECRET_DETECTED", path, "secret-like value is not allowed in packet"))
            break
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for error in errors:
        key = (error["code"], error["path"])
        if key not in seen:
            unique.append(error)
            seen.add(key)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a unified ui-test-packet")
    parser.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    try:
        packet = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [_problem("E_PACKET_READ", args.input, str(exc))]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    errors = validate_packet(packet)
    print(json.dumps({"valid": not errors, "schema_version": SCHEMA_VERSION, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
