from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List


ALLOWED_STAGES = {f"CP{i}" for i in range(7)}
ALLOWED_STATUS = {"passed", "failed", "degraded", "blocked"}
ALLOWED_RISK_LEVELS = {"R0", "R1", "R2", "R3"}
ALLOWED_FAILURE_LAYERS = {
    "ui",
    "api",
    "task",
    "downstream",
    "data",
    "env",
    "locator",
    "model",
    "governance",
}
ALLOWED_FAILURE_TYPES = {
    "locator_drift",
    "missing_field",
    "timeout",
    "false_positive",
    "stale_source",
    "permission_denied",
    "cleanup_failed",
    "contract_mismatch",
    "route_mismatch",
    "data_stale",
    "unknown",
}
MUTATING_ACTIONS = {
    "add",
    "associate",
    "create",
    "delete",
    "deploy",
    "publish",
    "approve",
    "submit",
    "update",
    "write",
}


class CheckpointValidationError(ValueError):
    pass


def _canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canonical(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_canonical(i) for i in obj]
    return obj


def _stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(_canonical(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _require_map(payload: Any, context: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise CheckpointValidationError(f"{context} must be an object")
    return payload


def _require_fields(payload: Dict[str, Any], fields: Iterable[str], context: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise CheckpointValidationError(f"missing required field(s) in {context}: {', '.join(missing)}")


def _require_non_empty_string(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CheckpointValidationError(f"{context} must be a non-empty string")


def _require_string_list(value: Any, context: str) -> None:
    if not isinstance(value, list) or len(value) == 0:
        raise CheckpointValidationError(f"{context} must be a non-empty list")
    for item in value:
        _require_non_empty_string(item, context)


def _validate_stage_and_id(checkpoint: Dict[str, Any]) -> None:
    stage = checkpoint["stage"]
    if stage not in ALLOWED_STAGES:
        raise CheckpointValidationError(f"stage must be one of {sorted(ALLOWED_STAGES)}")
    checkpoint_id = checkpoint["checkpoint_id"]
    _require_non_empty_string(checkpoint_id, "checkpoint_id")
    if not str(checkpoint_id).startswith(stage):
        raise CheckpointValidationError("checkpoint_id must start with stage prefix")


def _validate_source_baseline(source_baseline: Dict[str, Any]) -> None:
    _require_fields(
        source_baseline,
        [
            "prd_version",
            "figma_version",
            "design_version",
            "api_version",
            "code_branch",
            "environment_ref",
            "captured_at",
        ],
        "source_baseline",
    )
    for key in [
        "prd_version",
        "figma_version",
        "design_version",
        "api_version",
        "code_branch",
        "environment_ref",
        "captured_at",
    ]:
        _require_non_empty_string(source_baseline[key], f"source_baseline.{key}")


def _validate_execution_context(execution_context: Dict[str, Any]) -> None:
    _require_fields(
        execution_context,
        [
            "base_url",
            "route",
            "role_account_type",
            "environment_ref",
            "browser_profile",
            "viewport",
            "run_mode",
            "allowed_actions",
            "forbidden_actions",
            "test_data_ref",
            "auth_ref",
            "cleanup_scope",
        ],
        "execution_context",
    )
    for key in ["base_url", "route", "role_account_type", "environment_ref", "browser_profile", "run_mode", "test_data_ref", "auth_ref", "cleanup_scope"]:
        _require_non_empty_string(execution_context[key], f"execution_context.{key}")
    viewport = _require_map(execution_context["viewport"], "execution_context.viewport")
    _require_fields(viewport, ["width", "height"], "execution_context.viewport")
    if not isinstance(viewport["width"], int) or viewport["width"] <= 0:
        raise CheckpointValidationError("execution_context.viewport.width must be a positive integer")
    if not isinstance(viewport["height"], int) or viewport["height"] <= 0:
        raise CheckpointValidationError("execution_context.viewport.height must be a positive integer")
    _require_string_list(execution_context["allowed_actions"], "execution_context.allowed_actions")
    _require_string_list(execution_context["forbidden_actions"], "execution_context.forbidden_actions")
    if set(execution_context["allowed_actions"]) & set(execution_context["forbidden_actions"]):
        raise CheckpointValidationError("allowed_actions and forbidden_actions must not overlap")


def _validate_depends_on(depends_on: Any) -> None:
    if not isinstance(depends_on, list):
        raise CheckpointValidationError("depends_on must be a list")
    for item in depends_on:
        dep = _require_map(item, "depends_on item")
        _require_fields(dep, ["checkpoint_id", "dependency_type", "impact"], "depends_on item")
        _require_non_empty_string(dep["checkpoint_id"], "depends_on.checkpoint_id")
        _require_non_empty_string(dep["dependency_type"], "depends_on.dependency_type")
        _require_non_empty_string(dep["impact"], "depends_on.impact")


def _validate_steps(steps: Any) -> None:
    if steps is None:
        return
    if not isinstance(steps, list):
        raise CheckpointValidationError("steps must be a list")
    for step in steps:
        item = _require_map(step, "steps item")
        _require_fields(item, ["id", "name", "action", "verification", "evidence_refs"], "steps item")
        for key in ["id", "name", "action", "verification"]:
            _require_non_empty_string(item[key], f"steps.{key}")
        _require_string_list(item["evidence_refs"], "steps.evidence_refs")


def _validate_validate(validate: Dict[str, Any]) -> None:
    _require_fields(validate, ["ui", "api", "task", "downstream", "schema"], "validate")
    for key in ["ui", "api", "task", "downstream", "schema"]:
        _require_string_list(validate[key], f"validate.{key}")


def _validate_evidence(evidence: Dict[str, Any]) -> None:
    _require_fields(evidence, ["artifacts", "summary"], "evidence")
    _require_non_empty_string(evidence["summary"], "evidence.summary")
    if not isinstance(evidence["artifacts"], list) or len(evidence["artifacts"]) == 0:
        raise CheckpointValidationError("evidence.artifacts must be a non-empty list")
    for artifact in evidence["artifacts"]:
        item = _require_map(artifact, "evidence.artifacts item")
        _require_fields(item, ["type", "path"], "evidence.artifacts item")
        _require_non_empty_string(item["type"], "evidence.artifacts.type")
        _require_non_empty_string(item["path"], "evidence.artifacts.path")


def _validate_governance(governance: Dict[str, Any]) -> None:
    _require_fields(governance, ["owner", "reviewer", "approved_by", "decision", "decision_reason"], "governance")
    for key in ["owner", "reviewer", "approved_by", "decision", "decision_reason"]:
        _require_non_empty_string(governance[key], f"governance.{key}")


def _validate_promotion_gate(promotion_gate: Dict[str, Any]) -> None:
    _require_fields(
        promotion_gate,
        ["candidate_type", "pass_count", "required_pass_count", "confidence", "blocked_reasons"],
        "promotion_gate",
    )
    if promotion_gate["candidate_type"] not in {"playwright", "hybrid", "manual"}:
        raise CheckpointValidationError("promotion_gate.candidate_type must be playwright, hybrid, or manual")
    if not isinstance(promotion_gate["pass_count"], int) or promotion_gate["pass_count"] < 0:
        raise CheckpointValidationError("promotion_gate.pass_count must be a non-negative integer")
    if not isinstance(promotion_gate["required_pass_count"], int) or promotion_gate["required_pass_count"] < 0:
        raise CheckpointValidationError("promotion_gate.required_pass_count must be a non-negative integer")
    if not isinstance(promotion_gate["confidence"], (int, float)) or not (0 <= promotion_gate["confidence"] <= 1):
        raise CheckpointValidationError("promotion_gate.confidence must be between 0 and 1")
    if not isinstance(promotion_gate["blocked_reasons"], list):
        raise CheckpointValidationError("promotion_gate.blocked_reasons must be a list")


def _validate_staleness_policy(staleness_policy: Dict[str, Any]) -> None:
    _require_fields(staleness_policy, ["dependency_categories", "validation_result"], "staleness_policy")
    _require_string_list(staleness_policy["dependency_categories"], "staleness_policy.dependency_categories")
    _require_non_empty_string(staleness_policy["validation_result"], "staleness_policy.validation_result")


def _validate_cleanup_policy(cleanup_policy: Dict[str, Any]) -> None:
    _require_fields(cleanup_policy, ["required_for_write", "scope", "verification"], "cleanup_policy")
    if not isinstance(cleanup_policy["required_for_write"], bool):
        raise CheckpointValidationError("cleanup_policy.required_for_write must be boolean")
    _require_non_empty_string(cleanup_policy["scope"], "cleanup_policy.scope")
    _require_non_empty_string(cleanup_policy["verification"], "cleanup_policy.verification")


def _validate_failure_attribution(failure_attribution: Dict[str, Any]) -> None:
    _require_fields(
        failure_attribution,
        ["layer", "failure_type", "root_cause_id", "confidence", "evidence_refs", "impact_scope", "action_taken", "next_step"],
        "failure_attribution",
    )
    if failure_attribution["layer"] not in ALLOWED_FAILURE_LAYERS:
        raise CheckpointValidationError("invalid failure_attribution.layer")
    if failure_attribution["failure_type"] not in ALLOWED_FAILURE_TYPES:
        raise CheckpointValidationError("invalid failure_attribution.failure_type")
    _require_non_empty_string(failure_attribution["root_cause_id"], "failure_attribution.root_cause_id")
    if not isinstance(failure_attribution["confidence"], (int, float)) or not (0 <= failure_attribution["confidence"] <= 1):
        raise CheckpointValidationError("failure_attribution.confidence must be between 0 and 1")
    _require_string_list(failure_attribution["evidence_refs"], "failure_attribution.evidence_refs")
    for key in ["impact_scope", "action_taken", "next_step"]:
        _require_non_empty_string(failure_attribution[key], f"failure_attribution.{key}")


def _requires_cleanup(execution_context: Dict[str, Any]) -> bool:
    run_mode = str(execution_context.get("run_mode", "")).strip()
    if run_mode and run_mode != "read-only":
        return True
    allowed_actions = set(_ensure_list(execution_context.get("allowed_actions")))
    return bool(allowed_actions & MUTATING_ACTIONS)


def validate_checkpoint(checkpoint: Dict[str, Any]) -> None:
    _require_map(checkpoint, "checkpoint")
    _require_fields(
        checkpoint,
        [
            "checkpoint_id",
            "schema_version",
            "stage",
            "name",
            "status",
            "risk_level",
            "source_baseline",
            "execution_context",
            "depends_on",
            "validate",
            "evidence",
            "governance",
            "promotion_gate",
            "staleness_policy",
        ],
        "checkpoint",
    )
    _require_non_empty_string(checkpoint["schema_version"], "schema_version")
    _require_non_empty_string(checkpoint["name"], "name")
    if checkpoint["status"] not in ALLOWED_STATUS:
        raise CheckpointValidationError(f"status must be one of {sorted(ALLOWED_STATUS)}")
    if checkpoint["risk_level"] not in ALLOWED_RISK_LEVELS:
        raise CheckpointValidationError(f"risk_level must be one of {sorted(ALLOWED_RISK_LEVELS)}")
    _validate_stage_and_id(checkpoint)
    _validate_source_baseline(_require_map(checkpoint["source_baseline"], "source_baseline"))
    _validate_execution_context(_require_map(checkpoint["execution_context"], "execution_context"))
    _validate_depends_on(checkpoint["depends_on"])
    _validate_steps(checkpoint.get("steps"))
    _validate_validate(_require_map(checkpoint["validate"], "validate"))
    _validate_evidence(_require_map(checkpoint["evidence"], "evidence"))
    _validate_governance(_require_map(checkpoint["governance"], "governance"))
    _validate_promotion_gate(_require_map(checkpoint["promotion_gate"], "promotion_gate"))
    _validate_staleness_policy(_require_map(checkpoint["staleness_policy"], "staleness_policy"))

    if _requires_cleanup(_require_map(checkpoint["execution_context"], "execution_context")):
        cleanup_policy = checkpoint.get("cleanup_policy")
        if cleanup_policy is None:
            raise CheckpointValidationError("cleanup_policy required for write checkpoints")
        _validate_cleanup_policy(_require_map(cleanup_policy, "cleanup_policy"))
        if cleanup_policy["required_for_write"] is not True:
            raise CheckpointValidationError("cleanup_policy.required_for_write must be true for write checkpoints")
    elif checkpoint.get("cleanup_policy") is not None:
        _validate_cleanup_policy(_require_map(checkpoint["cleanup_policy"], "cleanup_policy"))

    if checkpoint["status"] in {"failed", "degraded", "blocked"}:
        failure_attribution = checkpoint.get("failure_attribution")
        if failure_attribution is None:
            raise CheckpointValidationError("failure_attribution required for failed/degraded/blocked checkpoints")
        _validate_failure_attribution(_require_map(failure_attribution, "failure_attribution"))


def normalize_artifact_refs(refs: Any) -> List[Dict[str, Any]]:
    normalized = []
    for ref in _ensure_list(refs):
        item = _require_map(ref, "artifact_ref")
        stable = {}
        for key in ["type", "path", "packet_id", "report_id", "screenshot_path", "trace_path", "json_path", "ref_id"]:
            if key in item:
                stable[key] = item[key]
        if "path" not in stable and "screenshot_path" not in stable and "trace_path" not in stable and "json_path" not in stable:
            raise CheckpointValidationError("artifact refs must contain a stable path-like key")
        normalized.append(stable)
    return normalized


def _derive_required_fix_points(checkpoint: Dict[str, Any], review_notes: Dict[str, Any]) -> List[str]:
    if review_notes.get("required_fix_points"):
        return list(_ensure_list(review_notes["required_fix_points"]))
    if checkpoint.get("failure_attribution"):
        failure = checkpoint["failure_attribution"]
        return [failure.get("next_step", "review failure")]
    return [f"保持 {checkpoint['checkpoint_id']} 的 schema 与证据结构不变"]


def _derive_next_action(checkpoint: Dict[str, Any], review_notes: Dict[str, Any]) -> str:
    if review_notes.get("next_action"):
        return review_notes["next_action"]
    status = checkpoint["status"]
    if status == "passed":
        return "review"
    if status == "degraded":
        return "fallback_playwright"
    if status == "blocked":
        return "escalate_human"
    return "revise_prompt"


def _status_to_decision(checkpoint: Dict[str, Any]) -> str:
    status = checkpoint["status"]
    if status == "passed":
        return "approved"
    if status == "degraded":
        return "approved-with-caveats"
    if status == "blocked":
        return "blocked"
    return "needs-fix"


def build_ui_test_packet(checkpoint: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    review_notes = review_notes or {}
    validate_checkpoint(checkpoint)
    artifact_refs = normalize_artifact_refs(checkpoint["evidence"]["artifacts"])
    if checkpoint.get("steps"):
        artifact_refs.extend(
            normalize_artifact_refs(
                [
                    {"type": "step_evidence", "path": ref}
                    for step in checkpoint["steps"]
                    for ref in _ensure_list(step.get("evidence_refs"))
                ]
            )
        )
    packet = {
        "packet_id": _stable_id("ui_test", checkpoint),
        "schema_version": checkpoint["schema_version"],
        "objective": checkpoint["name"],
        "scope": {
            "in_scope": [checkpoint["stage"], checkpoint["name"]],
            "out_of_scope": ["production writes", "delete", "publish", "deploy", "external transport"],
        },
        "safety": {
            "read_only": checkpoint["execution_context"]["run_mode"] == "read-only",
            "forbidden_actions": checkpoint["execution_context"]["forbidden_actions"],
        },
        "steps": deepcopy(checkpoint.get("steps", [])),
        "artifact_refs": artifact_refs,
        "failure_history": [deepcopy(checkpoint["failure_attribution"])] if checkpoint.get("failure_attribution") else [],
        "retry_history": _ensure_list(review_notes.get("retry_history")),
        "required_fix_points": _derive_required_fix_points(checkpoint, review_notes),
        "next_action": _derive_next_action(checkpoint, review_notes),
    }
    return packet


def build_handoff_packet(checkpoint: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    review_notes = review_notes or {}
    validate_checkpoint(checkpoint)
    packet = {
        "handoff_id": _stable_id("handoff", checkpoint),
        "source_packet_id": checkpoint["checkpoint_id"],
        "parent_packet_id": checkpoint.get("parent_checkpoint_id") or checkpoint["checkpoint_id"],
        "handoff_stage": checkpoint["stage"],
        "decision_status": review_notes.get("decision_status", _status_to_decision(checkpoint)),
        "failure_history": [deepcopy(checkpoint["failure_attribution"])] if checkpoint.get("failure_attribution") else [],
        "retry_history": _ensure_list(review_notes.get("retry_history")),
        "required_fix_points": _derive_required_fix_points(checkpoint, review_notes),
        "artifact_refs": normalize_artifact_refs(checkpoint["evidence"]["artifacts"]),
        "next_action": _derive_next_action(checkpoint, review_notes),
    }
    return packet


def build_rag_packet(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    validate_checkpoint(checkpoint)
    return {
        "packet_id": _stable_id("rag", checkpoint),
        "source_checkpoint_id": checkpoint["checkpoint_id"],
        "schema_version": checkpoint["schema_version"],
        "source_baseline": deepcopy(checkpoint["source_baseline"]),
        "execution_context": deepcopy(checkpoint["execution_context"]),
        "depends_on": deepcopy(checkpoint["depends_on"]),
        "validate": deepcopy(checkpoint["validate"]),
        "evidence": deepcopy(checkpoint["evidence"]),
        "governance": deepcopy(checkpoint["governance"]),
        "promotion_gate": deepcopy(checkpoint["promotion_gate"]),
        "staleness_policy": deepcopy(checkpoint["staleness_policy"]),
        "failure_attribution": deepcopy(checkpoint.get("failure_attribution")),
    }


def build_checkpoint_bundle(checkpoint: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    review_notes = review_notes or {}
    validate_checkpoint(checkpoint)
    normalized = deepcopy(checkpoint)
    ui_packet = build_ui_test_packet(normalized, review_notes)
    handoff_packet = build_handoff_packet(normalized, review_notes)
    rag_packet = build_rag_packet(normalized)
    artifact_refs = normalize_artifact_refs(normalized["evidence"]["artifacts"])
    bundle = {
        "bundle_id": _stable_id("checkpoint_bundle", normalized),
        "checkpoint": normalized,
        "ui_test_packet": ui_packet,
        "handoff_packet": handoff_packet,
        "rag_packet": rag_packet,
        "artifact_refs": artifact_refs,
        "summary": {
            "checkpoint_id": normalized["checkpoint_id"],
            "stage": normalized["stage"],
            "status": normalized["status"],
            "next_action": handoff_packet["next_action"],
        },
    }
    return bundle


def load_json(path: Path) -> Dict[str, Any] | List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_validate(input_path: Path) -> None:
    payload = load_json(input_path)
    checkpoints = payload if isinstance(payload, list) else [payload]
    for checkpoint in checkpoints:
        validate_checkpoint(checkpoint)


def _run_bundle(input_path: Path, output_path: Path) -> None:
    payload = load_json(input_path)
    checkpoints = payload if isinstance(payload, list) else [payload]
    bundles = [build_checkpoint_bundle(checkpoint) for checkpoint in checkpoints]
    save_json(output_path, bundles if isinstance(payload, list) else bundles[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Checkpoint schema validator and bundle builder")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate checkpoint JSON")
    validate_parser.add_argument("--input", type=Path, required=True)

    bundle_parser = subparsers.add_parser("bundle", help="build downstream checkpoint bundle")
    bundle_parser.add_argument("--input", type=Path, required=True)
    bundle_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "validate":
        _run_validate(args.input)
    elif args.command == "bundle":
        _run_bundle(args.input, args.output)


if __name__ == "__main__":
    main()
