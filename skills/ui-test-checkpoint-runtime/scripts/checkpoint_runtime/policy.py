from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import READONLY_ACTIONS, RISK_ALLOWLIST_V1, WRITE_ACTIONS


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def action_is_forbidden(action: str | None, forbidden_actions: list[str] | None = None) -> bool:
    if not action:
        return False
    forbidden = {item.lower() for item in (forbidden_actions or [])} | WRITE_ACTIONS
    lowered = action.lower()
    return lowered in forbidden or any(token in lowered for token in forbidden) or lowered not in READONLY_ACTIONS


def risk_allowed(risk_level: str | None) -> bool:
    return risk_level in RISK_ALLOWLIST_V1


def auth_is_expired(auth_ref: dict[str, Any], now: datetime | None = None) -> bool:
    expires_at = parse_time(auth_ref.get("expires_at"))
    if expires_at is None:
        return True
    current = now or datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= current


def reportable_auth_ref(auth_ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "auth_ref_id": auth_ref.get("auth_ref_id"),
        "system_id": auth_ref.get("system_id"),
        "role_account_type": auth_ref.get("role_account_type"),
        "expires_at": auth_ref.get("expires_at"),
        "contains_secret": bool(auth_ref.get("contains_secret")),
        "reportable": bool(auth_ref.get("reportable")),
        "rag_allowed": bool(auth_ref.get("rag_allowed")),
        "provenance": auth_ref.get("provenance"),
        "freshness": auth_ref.get("freshness"),
    }


def assert_auth_reportable_boundary(auth_ref: dict[str, Any]) -> None:
    if auth_ref.get("reportable") is not False or auth_ref.get("rag_allowed") is not False:
        raise ValueError("auth_ref must not be reportable or rag_allowed")
