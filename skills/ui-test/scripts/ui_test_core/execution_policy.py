"""Execution authorization separate from risk classification."""

from __future__ import annotations

import hashlib
import json
from typing import Any


HARD_WRITE_ACTIONS = {"fill", "submit", "update", "delete", "approve", "publish"}
RISK_ORDER = {"r0-read-only": 0, "r1-read-only-authenticated": 1, "r2-ui-write-test": 2, "r3-high-impact": 3}


def policy_fingerprint(policy: dict[str, Any]) -> str:
    payload = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def decide_execution(step: dict[str, Any], policy: dict[str, Any] | None, *, environment: str, channel: str = "ui") -> dict[str, Any]:
    policy = policy or {}
    action = step.get("action")
    risk = step.get("risk_level")
    if risk not in RISK_ORDER:
        return {"allowed": False, "code": "E_RISK_UNKNOWN", "blocking": True}
    if environment == "production":
        return {"allowed": False, "code": "E_POLICY_PRODUCTION_WRITE_BLOCK", "blocking": True}
    if risk == "r3-high-impact":
        return {"allowed": False, "code": "E_POLICY_R3_BLOCK", "blocking": True}
    if channel == "api" and action in HARD_WRITE_ACTIONS:
        return {"allowed": False, "code": "E_POLICY_API_WRITE_BLOCK", "blocking": True}
    if policy.get("secret_boundary") == "detected":
        return {"allowed": False, "code": "E_SECRET_DETECTED", "blocking": True}
    if action in set(policy.get("deny_actions", [])):
        return {"allowed": False, "code": "E_POLICY_DENIED_ACTION", "blocking": True}
    allowed_actions = set(policy.get("allow_actions", []))
    if allowed_actions and action not in allowed_actions:
        return {"allowed": False, "code": "E_POLICY_ACTION_NOT_ALLOWED", "blocking": True}
    if action in HARD_WRITE_ACTIONS and risk == "r2-ui-write-test":
        if channel != "ui":
            return {"allowed": False, "code": "E_POLICY_UI_ONLY_WRITE_REQUIRED", "blocking": True}
        if policy.get("task_authorization") not in {"approved", True}:
            return {"allowed": False, "code": "E_POLICY_WRITE_AUTH_REQUIRED", "blocking": True}
    return {
        "allowed": True,
        "code": "OK",
        "blocking": False,
        "execution_mode": "ui-write" if action in HARD_WRITE_ACTIONS else "read-or-navigation",
        "policy_fingerprint": policy_fingerprint(policy),
    }


def evaluate_packet_policy(packet: dict[str, Any], policy: dict[str, Any] | None = None, *, channel: str = "ui") -> dict[str, Any]:
    environment = packet.get("scope", {}).get("environment", "")
    decisions = [
        {"step_id": step.get("step_id"), **decide_execution(step, policy, environment=environment, channel=channel)}
        for step in packet.get("steps", [])
        if isinstance(step, dict)
    ]
    blockers = [item for item in decisions if not item.get("allowed")]
    return {"allowed": not blockers, "code": "OK" if not blockers else blockers[0]["code"], "decisions": decisions}
