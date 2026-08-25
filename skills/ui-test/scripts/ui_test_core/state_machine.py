"""Explicit lifecycle transitions for the UI-Test control plane."""

from __future__ import annotations

LEGAL = {
    "requirements-review": {"plan", "blocked"},
    "plan": {"preflight", "repair", "blocked"},
    "preflight": {"explore", "verify", "repair", "blocked"},
    "explore": {"verify", "repair", "blocked"},
    "verify": {"evidence", "repair", "blocked"},
    "evidence": {"review", "repair", "blocked"},
    "review": {"checkpoint", "learn", "report", "repair", "blocked"},
    "checkpoint": {"learn", "report", "repair", "blocked"},
    "learn": {"report", "repair", "blocked"},
    "report": {"done", "repair", "blocked"},
    "repair": {"rerun", "blocked"},
    "rerun": {"preflight", "explore", "verify", "evidence", "review", "checkpoint", "blocked"},
    "blocked": {"plan", "preflight", "explore", "verify", "evidence", "review", "checkpoint", "learn", "report"},
    "done": set(),
}


def transition(current: str, target: str, *, actor: str = "codex", completion_passed: bool = False, lineage_unchanged: bool = True) -> dict:
    if actor != "codex":
        return {"ok": False, "code": "E_STATE_ACTOR_FORBIDDEN", "state": current}
    if current not in LEGAL or target not in LEGAL:
        return {"ok": False, "code": "E_STATE_ILLEGAL", "state": current}
    if target not in LEGAL[current]:
        return {"ok": False, "code": "E_STATE_ILLEGAL", "state": current}
    if current == "blocked" and not lineage_unchanged:
        return {"ok": False, "code": "E_LINEAGE_MISMATCH", "state": current}
    if target == "done" and not completion_passed:
        return {"ok": False, "code": "E_COMPLETION_GATE", "state": current}
    return {"ok": True, "code": "OK", "state": target}
