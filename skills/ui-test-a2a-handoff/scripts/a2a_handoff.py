from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple


ALLOWED_NEXT_ACTIONS = {
    "revise_prompt",
    "rerun_midscene",
    "fallback_playwright",
    "escalate_human",
    "review",
}

SENSITIVE_MARKERS = (
    "sk-",
    "bearer ",
    "token",
    "cookie",
    "password",
    "passwd",
    "secret",
    "Authorization:",
    "authorization",
)


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


def _reject_sensitive_refs(refs: List[Any]) -> None:
    for item in refs:
        text = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
        lowered = text.lower()
        for marker in SENSITIVE_MARKERS:
            if marker.lower() in lowered:
                raise ValueError(f"sensitive marker found in artifact_refs: {marker}")
        if len(text) > 1200:
            raise ValueError("artifact_refs item is too long; keep only stable references")


def validate_packet(packet: Dict[str, Any]) -> None:
    required = [
        "packet_id",
        "schema_version",
        "objective",
        "scope",
        "safety",
        "steps",
        "artifact_refs",
        "failure_history",
        "retry_history",
        "required_fix_points",
        "next_action",
    ]
    for key in required:
        if key not in packet:
            raise ValueError(f"missing required field: {key}")
    if not str(packet["packet_id"]).strip():
        raise ValueError("packet_id must not be empty")
    if not str(packet["schema_version"]).strip():
        raise ValueError("schema_version must not be empty")
    if not isinstance(packet["steps"], list):
        raise ValueError("steps must be a list")
    safety = packet["safety"]
    if not isinstance(safety, dict):
        raise ValueError("safety must be an object")
    if safety.get("read_only") is not True:
        raise ValueError("safety.read_only must be true")
    forbidden_actions = safety.get("forbidden_actions")
    if not isinstance(forbidden_actions, list) or not forbidden_actions:
        raise ValueError("safety.forbidden_actions must be a non-empty list")
    if packet["next_action"] not in ALLOWED_NEXT_ACTIONS:
        raise ValueError(f"invalid next_action: {packet['next_action']}")
    _reject_sensitive_refs(_ensure_list(packet["artifact_refs"]))
    if len(_ensure_list(packet["required_fix_points"])) == 0:
        raise ValueError("required_fix_points must not be empty")


def normalize_history(items: Any) -> List[Dict[str, Any]]:
    normalized = []
    for item in _ensure_list(items):
        if isinstance(item, dict):
            normalized.append(_canonical(item))
        else:
            normalized.append({"value": item})
    return normalized


def normalize_refs(refs: Any) -> List[Any]:
    refs_list = _ensure_list(refs)
    _reject_sensitive_refs(refs_list)
    stable = []
    for ref in refs_list:
        if isinstance(ref, dict):
            stable.append({k: ref[k] for k in sorted(ref) if k in {"packet_id", "file_path", "report_id", "screenshot_path", "trace_path", "json_path", "ref_id", "path", "type"}})
        else:
            stable.append(ref)
    return stable


def build_handoff_packet(source: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    validate_packet(source)
    review_notes = review_notes or {}
    handoff = {
        "handoff_id": _stable_id("handoff", source),
        "source_packet_id": source["packet_id"],
        "parent_packet_id": source.get("parent_packet_id") or source["packet_id"],
        "handoff_stage": "handoff",
        "decision_status": review_notes.get("decision_status", source.get("decision_status", "draft")),
        "failure_history": normalize_history(source.get("failure_history")),
        "retry_history": normalize_history(source.get("retry_history")),
        "required_fix_points": list(_ensure_list(source.get("required_fix_points"))),
        "artifact_refs": normalize_refs(source.get("artifact_refs")),
        "next_action": review_notes.get("next_action", source["next_action"]),
    }
    return handoff


def build_prompt_packet(source: Dict[str, Any], handoff_packet: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    review_notes = review_notes or {}
    prompt_goal = review_notes.get("prompt_goal") or source.get("objective")
    prompt = {
        "prompt_id": _stable_id("prompt", {"source": source, "handoff": handoff_packet}),
        "source_packet_id": source["packet_id"],
        "objective": source.get("objective"),
        "prompt_goal": prompt_goal,
        "constraints": {
            "read_only": True,
            "no_browser_execution": True,
            "preserve_history": True,
            "keep_artifact_refs_short": True,
        },
        "allowed_actions": review_notes.get("allowed_actions", ["revise_prompt", "rerun_midscene", "fallback_playwright", "review"]),
        "forbidden_actions": review_notes.get("forbidden_actions", ["remote_transport", "write_business_state", "embed_long_prose"]),
        "expected_verification": review_notes.get("expected_verification", [
            "Codex can resume from prompt_packet without rereading full upstream prose",
            "prompt changes are localized",
            "artifact_refs remain stable and short",
        ]),
        "revision_notes": review_notes.get("revision_notes", []),
    }
    if any(action not in ALLOWED_NEXT_ACTIONS for action in prompt["allowed_actions"]):
        raise ValueError("prompt allowed_actions contains invalid action")
    return prompt


def pack(source: Dict[str, Any], review_notes: Dict[str, Any] | None = None) -> Dict[str, Any]:
    handoff = build_handoff_packet(source, review_notes)
    prompt = build_prompt_packet(source, handoff, review_notes)
    return {
        "handoff_packet": handoff,
        "prompt_packet": prompt,
        "artifact_refs": handoff["artifact_refs"],
        "summary": {
            "source_packet_id": source["packet_id"],
            "handoff_id": handoff["handoff_id"],
            "prompt_id": prompt["prompt_id"],
            "next_action": handoff["next_action"],
        },
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--review-notes", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = load_json(args.source)
    review_notes = load_json(args.review_notes) if args.review_notes else None
    save_json(args.output, pack(source, review_notes))


if __name__ == "__main__":
    main()
