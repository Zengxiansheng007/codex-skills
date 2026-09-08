#!/usr/bin/env python3
"""CLI live/dry mode guard for public research (FR-RR-001, FR-RR-005).

Ensures:
1. Live research rejects permission mode plan.
2. Dry-run mode never spawns Claude.
3. Format retries and content reinforcement are separate and bounded.
4. Format repair may retry serialization at most 3 times without new retrieval.
5. Content gaps allow at most 1 reinforcement round.
"""
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REGISTRY_PATH = SKILL_ROOT / "schemas" / "public-research-tool-registry.json"

PLAN_MODES = {"plan"}
ALLOWED_MODES = {"acceptEdits", "auto", "default", "dontAsk"}
MAX_FORMAT_RETRIES = 3
MAX_REINFORCEMENT_ROUNDS = 1


@dataclass
class GuardResult:
    allowed: bool
    mode: str
    reason: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_registry() -> list[str]:
    """Return approved tool names from the registry."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("toolNames", [])


def check_live_mode(permission_mode: str) -> GuardResult:
    """FR-RR-001: Live research rejects permission mode plan."""
    if permission_mode in PLAN_MODES:
        return GuardResult(False, "live", "plan-mode-blocked", f"permission mode '{permission_mode}' cannot execute tools in live research")
    if permission_mode not in ALLOWED_MODES:
        return GuardResult(False, "live", "invalid-mode", f"permission mode '{permission_mode}' is not in allowed set")
    return GuardResult(True, "live", "ok", f"live mode allowed with permission mode '{permission_mode}'")


def check_dry_mode() -> GuardResult:
    """Dry-run mode never spawns Claude."""
    return GuardResult(True, "dry-run", "ok", "dry-run mode does not spawn Claude")


def check_format_retries(retries: int) -> GuardResult:
    """FR-RR-005: Format repair may retry at most 3 times without new retrieval."""
    if retries > MAX_FORMAT_RETRIES:
        return GuardResult(False, "format-retry", "format-retry-limit-exceeded", f"format retries {retries} exceed max {MAX_FORMAT_RETRIES}")
    return GuardResult(True, "format-retry", "ok", f"format retries {retries} within limit")


def check_reinforcement_rounds(rounds: int) -> GuardResult:
    """FR-RR-005: Content gaps allow at most 1 reinforcement round."""
    if rounds > MAX_REINFORCEMENT_ROUNDS:
        return GuardResult(False, "reinforcement", "reinforcement-limit-exceeded", f"reinforcement rounds {rounds} exceed max {MAX_REINFORCEMENT_ROUNDS}")
    return GuardResult(True, "reinforcement", "ok", f"reinforcement rounds {rounds} within limit")


def check_tool_scope(requested_tools: list[str]) -> GuardResult:
    """FR-RR-002: Verify requested tools match the registry."""
    registry = set(load_registry())
    requested = set(requested_tools)
    if not requested:
        return GuardResult(False, "tool-scope", "no-tools", "no tools requested")
    unregistered = requested - registry
    if unregistered:
        return GuardResult(False, "tool-scope", "unregistered-tool", f"unregistered tools: {sorted(unregistered)}")
    return GuardResult(True, "tool-scope", "ok", "all tools match registry")


def evaluate(
    mode: str,
    permission_mode: str = "default",
    format_retries: int = 0,
    reinforcement_rounds: int = 0,
    requested_tools: Optional[list[str]] = None,
) -> dict:
    """Evaluate all guard conditions and return combined result."""
    requested_tools = requested_tools or []
    results: list[GuardResult] = []

    if mode == "live":
        results.append(check_live_mode(permission_mode))
    elif mode == "dry-run":
        results.append(check_dry_mode())
    else:
        results.append(GuardResult(False, mode, "invalid-mode", f"unknown mode: {mode}"))

    results.append(check_tool_scope(requested_tools))
    results.append(check_format_retries(format_retries))
    results.append(check_reinforcement_rounds(reinforcement_rounds))

    all_allowed = all(r.allowed for r in results)
    failures = [r for r in results if not r.allowed]

    return {
        "allowed": all_allowed,
        "mode": mode,
        "results": [r.to_dict() for r in results],
        "failures": [r.to_dict() for r in failures],
        "maxFormatRetries": MAX_FORMAT_RETRIES,
        "maxReinforcementRounds": MAX_REINFORCEMENT_ROUNDS,
        "registryTools": load_registry(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI live/dry mode guard")
    parser.add_argument("--mode", required=True, choices=["live", "dry-run"])
    parser.add_argument("--permission-mode", default="default")
    parser.add_argument("--format-retries", type=int, default=0)
    parser.add_argument("--reinforcement-rounds", type=int, default=0)
    parser.add_argument("--requested-tools", nargs="*", default=[])
    parser.add_argument("--json", dest="json_output", default=None)
    args = parser.parse_args()

    result = evaluate(
        mode=args.mode,
        permission_mode=args.permission_mode,
        format_retries=args.format_retries,
        reinforcement_rounds=args.reinforcement_rounds,
        requested_tools=args.requested_tools,
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(output, encoding="utf-8")
    print(output)
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
