"""Single control-plane route decision shared by current and legacy entrypoints."""

from __future__ import annotations

from typing import Any

from .packet_validator import validate_packet
from .problem_details import from_validation_errors


SUPPORTED_ROUTES = {
    "plan": "ui-test-plan",
    "explore": "ui-test-explore",
    "verify": "ui-test-verify",
    "evidence": "ui-test-evidence",
    "review": "ui-test-review",
    "checkpoint": "ui-test-checkpoint-runtime",
    "report": "ui-test-execution-report",
}


def route_packet(packet: dict[str, Any], source: str = "ui-test") -> dict[str, Any]:
    errors = validate_packet(packet)
    if errors:
        return {
            "ok": False,
            "route": None,
            "deprecated": source == "ui-test-system",
            "problem": from_validation_errors(errors).as_dict(),
        }
    state = packet["state"]
    route = SUPPORTED_ROUTES.get(state)
    if not route:
        return {
            "ok": False,
            "route": None,
            "deprecated": source == "ui-test-system",
            "problem": {
                "type": "https://codex.local/problems/e_state_route_unknown",
                "title": "No child route is registered for packet state",
                "status": 422,
                "code": "E_ROUTE_UNKNOWN",
            },
        }
    return {
        "ok": True,
        "route": route,
        "packet_schema_version": packet["schema_version"],
        "packet_id": packet["packet_id"],
        "deprecated": source == "ui-test-system",
        "replacement": "ui-test" if source == "ui-test-system" else None,
        "payload_forwarded": True,
    }


def legacy_route_decision(packet: dict[str, Any]) -> dict[str, Any]:
    decision = route_packet(packet, source="ui-test-system")
    decision["payload_forwarded"] = False
    decision["route"] = "ui-test"
    decision["status_code"] = "deprecated"
    return decision
