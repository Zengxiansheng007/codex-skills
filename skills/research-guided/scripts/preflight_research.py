#!/usr/bin/env python3
"""Preflight contract and runtime for public research (FR-RR-003).

Verifies before any live research attempt:
1. Claude executable exists (executable resolved).
2. CLI capability (claude --version or equivalent).
3. Fresh session declaration (not a stale session).
4. MCP schema visibility (tools are registered and visible).
5. Tool count > 0.
6. Exact registry match (no unregistered tools requested).
7. Canary evidence present and passed.
8. Zero permission denials.
9. Permission mode is not plan.

Live research must fail closed when any of these checks fail.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

REGISTRY_PATH = SKILL_ROOT / "schemas" / "public-research-tool-registry.json"
RESEARCH_RESULT_SCHEMA = SKILL_ROOT / "schemas" / "research-result.schema.json"
FAILURE_CLASSIFICATION = SKILL_ROOT / "schemas" / "failure-classification.json"

PASSING_RESULT_CODES = {"PASS", "PASSED", "OK", "ALL_PASS", "ALL_TESTS_PASSED"}

PLAN_MODES = {"plan"}
ALLOWED_MODES = {"acceptEdits", "auto", "default", "dontAsk"}


@dataclass
class PreflightResult:
    check: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_registry() -> dict:
    """Load the tool registry JSON."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "toolNames" not in data or not isinstance(data["toolNames"], list):
        raise ValueError("Registry missing toolNames array")
    return data


def get_registry_tool_names() -> list[str]:
    """Return the approved MCP tool names from the registry."""
    return load_registry()["toolNames"]


def check_executable(claude_path: Optional[str] = None) -> PreflightResult:
    """FR-RR-003a: Verify executable exists."""
    exe = claude_path or shutil.which("claude") or shutil.which("claude.exe")
    if not exe:
        exe = os.environ.get("LOCALAPPDATA", "")
        if exe:
            candidate = Path(exe) / "Programs" / "ClaudeCode" / "claude.exe"
            if candidate.is_file():
                exe = str(candidate)
            else:
                exe = None
    if not exe or not Path(exe).exists():
        return PreflightResult("executable", False, f"claude executable not found: {exe}")
    return PreflightResult("executable", True, f"claude executable found: {exe}")


def check_cli_capability(claude_path: Optional[str] = None) -> PreflightResult:
    """FR-RR-003b: Check CLI capability (version check)."""
    exe = claude_path or shutil.which("claude") or shutil.which("claude.exe")
    if not exe:
        return PreflightResult("cli_capability", False, "no executable to check")
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            return PreflightResult("cli_capability", True, f"CLI version check passed: {result.stdout.strip()[:100]}")
        return PreflightResult("cli_capability", False, f"CLI version check failed: exit {result.returncode}")
    except Exception as exc:
        return PreflightResult("cli_capability", False, f"CLI capability check error: {type(exc).__name__}: {exc}")


def check_session_freshness(session_id: Optional[str] = None, session_started_at: Optional[str] = None) -> PreflightResult:
    """FR-RR-003c: Fresh session declaration."""
    if not session_id:
        return PreflightResult("session_freshness", False, "session_id not declared")
    if not session_started_at:
        return PreflightResult("session_freshness", False, "session_started_at not declared")
    if len(session_id) < 4:
        return PreflightResult("session_freshness", False, "session_id too short")
    return PreflightResult("session_freshness", True, f"session fresh: {session_id}")


def check_mcp_schema_visibility(visible_tools: list[str]) -> PreflightResult:
    """FR-RR-003d: MCP schema visibility."""
    if not visible_tools:
        return PreflightResult("mcp_schema_visibility", False, "no MCP tools visible")
    registry_names = set(get_registry_tool_names())
    for tool in visible_tools:
        if tool in registry_names:
            return PreflightResult("mcp_schema_visibility", True, f"MCP schema visible: {tool}")
    return PreflightResult("mcp_schema_visibility", False, f"no registry tools visible in: {visible_tools}")


def check_tool_count(visible_tools: list[str]) -> PreflightResult:
    """FR-RR-003e: Tool count > 0."""
    count = len(visible_tools)
    if count == 0:
        return PreflightResult("tool_count", False, "tool count is zero")
    return PreflightResult("tool_count", True, f"tool count: {count}")


def check_exact_registry_match(requested_tools: list[str]) -> PreflightResult:
    """FR-RR-003f: Exact registry match."""
    registry_names = set(get_registry_tool_names())
    requested_set = set(requested_tools) if requested_tools else set()
    if not requested_set:
        return PreflightResult("exact_registry_match", False, "no tools requested")
    unregistered = requested_set - registry_names
    if unregistered:
        return PreflightResult("exact_registry_match", False, f"unregistered tools: {sorted(unregistered)}")
    return PreflightResult("exact_registry_match", True, "all requested tools match registry")


def check_canary_evidence(canary: Optional[dict] = None) -> PreflightResult:
    """FR-RR-003g: Canary evidence present and passed."""
    if not canary:
        return PreflightResult("canary_evidence", False, "canary evidence missing")
    if not isinstance(canary, dict):
        return PreflightResult("canary_evidence", False, "canary evidence not a dict")
    canary_passed = canary.get("canaryPassed")
    if canary_passed is None:
        return PreflightResult("canary_evidence", False, "canaryPassed field missing")
    if not canary_passed:
        return PreflightResult("canary_evidence", False, f"canary failed: {canary.get('canaryDetail', 'no detail')}")
    return PreflightResult("canary_evidence", True, "canary passed")


def check_permission_denials(denial_count: int = 0) -> PreflightResult:
    """FR-RR-003h: Zero permission denials."""
    if denial_count != 0:
        return PreflightResult("permission_denials", False, f"permission denials: {denial_count}")
    return PreflightResult("permission_denials", True, "zero permission denials")


def check_permission_mode(mode: str) -> PreflightResult:
    """FR-RR-001: Live research rejects permission mode plan."""
    if mode in PLAN_MODES:
        return PreflightResult("permission_mode", False, f"plan mode blocked: {mode}")
    if mode not in ALLOWED_MODES:
        return PreflightResult("permission_mode", False, f"unsupported mode: {mode}")
    return PreflightResult("permission_mode", True, f"permission mode ok: {mode}")


def run_full_preflight(
    claude_path: Optional[str] = None,
    permission_mode: str = "default",
    session_id: Optional[str] = None,
    session_started_at: Optional[str] = None,
    visible_tools: Optional[list[str]] = None,
    requested_tools: Optional[list[str]] = None,
    canary: Optional[dict] = None,
    permission_denials: int = 0,
    skip_cli: bool = False,
) -> dict:
    """Run all preflight checks and return a combined result."""
    visible_tools = visible_tools or []
    requested_tools = requested_tools or []
    results: list[PreflightResult] = []

    results.append(check_permission_mode(permission_mode))
    results.append(check_executable(claude_path))
    if not skip_cli:
        results.append(check_cli_capability(claude_path))
    results.append(check_session_freshness(session_id, session_started_at))
    results.append(check_mcp_schema_visibility(visible_tools))
    results.append(check_tool_count(visible_tools))
    results.append(check_exact_registry_match(requested_tools))
    results.append(check_canary_evidence(canary))
    results.append(check_permission_denials(permission_denials))

    all_passed = all(r.passed for r in results)
    failures = [r for r in results if not r.passed]

    return {
        "allPassed": all_passed,
        "results": [r.to_dict() for r in results],
        "failures": [r.to_dict() for r in failures],
        "failureCount": len(failures),
        "registryTools": get_registry_tool_names(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for public research")
    parser.add_argument("--claude-path", default=None)
    parser.add_argument("--permission-mode", default="default")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--session-started-at", default=None)
    parser.add_argument("--visible-tools", nargs="*", default=[])
    parser.add_argument("--requested-tools", nargs="*", default=[])
    parser.add_argument("--canary-json", default=None, help="JSON string for canary evidence")
    parser.add_argument("--canary-json-file", default=None, help="UTF-8 JSON file for canary evidence")  # Avoid shell argv JSON escaping on Windows.
    parser.add_argument("--permission-denials", type=int, default=0)
    parser.add_argument("--skip-cli", action="store_true")
    parser.add_argument("--json", dest="json_output", default=None)
    args = parser.parse_args()

    canary = None
    if args.canary_json_file:
        try:
            canary = json.loads(Path(args.canary_json_file).read_text(encoding="utf-8"))  # Preserve structured evidence outside argv.
        except Exception as exc:
            canary = {"canaryPassed": False, "canaryDetail": f"invalid canary JSON file: {type(exc).__name__}"}
    if args.canary_json:
        try:
            canary = json.loads(args.canary_json)
        except json.JSONDecodeError:
            canary = {"canaryPassed": False, "canaryDetail": "invalid canary JSON"}

    result = run_full_preflight(
        claude_path=args.claude_path,
        permission_mode=args.permission_mode,
        session_id=args.session_id,
        session_started_at=args.session_started_at,
        visible_tools=args.visible_tools,
        requested_tools=args.requested_tools,
        canary=canary,
        permission_denials=args.permission_denials,
        skip_cli=args.skip_cli,
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(output, encoding="utf-8")
    print(output)
    return 0 if result["allPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
