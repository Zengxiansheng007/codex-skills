"""Risk classification helpers and optional risk projection."""

from __future__ import annotations

from typing import Any


RISK_ORDER = {"r0-read-only": 0, "r1-read-only-authenticated": 1, "r2-ui-write-test": 2, "r3-high-impact": 3}
READ_ONLY_ACTIONS = {"login", "navigate", "module-ready", "click", "select", "check", "query", "assert", "explore", "verify", "screenshot", "observe-network"}
WRITE_ACTIONS = {"fill", "submit", "update", "delete", "approve", "publish"}


def validate_action_risk(action: str, risk_level: str, environment: str) -> dict[str, Any]:
    if risk_level not in RISK_ORDER:
        return {"allowed": False, "code": "E_RISK_UNKNOWN"}
    if environment == "production" or risk_level == "r3-high-impact":
        return {"allowed": False, "code": "E_WRITE_BLOCKED", "reason": "production/R3 is fail-closed"}
    if risk_level in {"r0-read-only", "r1-read-only-authenticated"} and action in WRITE_ACTIONS:
        return {"allowed": False, "code": "E_RISK_ACTION_CONFLICT", "reason": "write actions must be classified as R2 or R3"}
    if action not in READ_ONLY_ACTIONS | WRITE_ACTIONS:
        return {"allowed": False, "code": "E_ACTION_UNKNOWN"}
    if risk_level == "r2-ui-write-test" and action in {"submit", "update", "delete", "approve", "publish"}:
        return {"allowed": True, "code": "OK", "execution_mode": "ui-only", "requires_write_gate": True}
    return {"allowed": True, "code": "OK", "execution_mode": "read-only", "requires_write_gate": False}


def effective_risk_level(steps: list[dict[str, Any]], fallback: str | None = None) -> str | None:
    risks = [step.get("risk_level") for step in steps if step.get("risk_level") in RISK_ORDER]
    if not risks:
        return fallback if fallback in RISK_ORDER else None
    return max(risks, key=lambda item: RISK_ORDER[item])


def split_by_risk(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Return optional governance projections for mixed-risk steps without mutating input."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for step in packet.get("steps", []):
        groups.setdefault(step.get("risk_level", packet.get("risk_level")), []).append(step)
    if len(groups) <= 1:
        return [dict(packet)]
    children = []
    for risk, steps in sorted(groups.items(), key=lambda item: RISK_ORDER.get(item[0], 99)):
        child = dict(packet)
        child["packet_id"] = f"{packet['packet_id']}:{risk}"
        child["risk_level"] = risk
        child["scope"] = dict(packet["scope"], risk_level=risk)
        child["steps"] = steps
        child["lineage"] = dict(packet["lineage"], parent_packet_id=packet["packet_id"])
        children.append(child)
    return children
