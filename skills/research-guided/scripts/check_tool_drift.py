#!/usr/bin/env python3
"""Check for tool name drift across SKILL.md, references, prompts, manifests, and runtime configuration.

The single JSON registry owns the four approved MCP tool names. This script
detects any drift where a different set of tool names appears in other files.
"""
from __future__ import annotations
import argparse, json, re, sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REGISTRY_PATH = SKILL_ROOT / "schemas" / "public-research-tool-registry.json"

MCP_TOOL_RE = re.compile(r"mcp__\w+__\w+")


@dataclass
class DriftFinding:
    file: str
    tools_found: list
    missing: list
    extra: list
    severity: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_registry_names() -> set[str]:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("toolNames", []))


def find_tools_in_text(text: str) -> set[str]:
    """Find all mcp__ tool references in text."""
    return set(MCP_TOOL_RE.findall(text))


def check_file(path: Path, registry_names: set[str]) -> list[DriftFinding]:
    """Check a single file for tool name drift."""
    findings: list[DriftFinding] = []
    if not path.exists() or not path.is_file():
        return findings
    rel = path.relative_to(SKILL_ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    found = find_tools_in_text(text)
    if not found:
        return findings

    missing = sorted(registry_names - found)
    extra = sorted(found - registry_names)

    if extra:
        findings.append(DriftFinding(rel, sorted(found), missing, extra, "P0",
            f"Unregistered tool names found: {extra}"))
    elif missing:
        findings.append(DriftFinding(rel, sorted(found), missing, extra, "P1",
            f"Registry tools missing from this file: {missing}"))

    return findings


def check_all() -> list[DriftFinding]:
    """Check all relevant files for tool name drift."""
    registry_names = load_registry_names()
    findings: list[DriftFinding] = []

    # Check SKILL.md
    findings.extend(check_file(SKILL_ROOT / "SKILL.md", registry_names))

    # Check references
    ref_dir = SKILL_ROOT / "references"
    if ref_dir.is_dir():
        for p in ref_dir.glob("*.md"):
            findings.extend(check_file(p, registry_names))

    # Check schemas (except the registry itself)
    schema_dir = SKILL_ROOT / "schemas"
    if schema_dir.is_dir():
        for p in schema_dir.glob("*.json"):
            if p.name == "public-research-tool-registry.json":
                continue
            findings.extend(check_file(p, registry_names))

    # Check scripts
    script_dir = SKILL_ROOT / "scripts"
    if script_dir.is_dir():
        for p in script_dir.glob("*.py"):
            findings.extend(check_file(p, registry_names))

    # Check agents
    agents_dir = SKILL_ROOT / "agents"
    if agents_dir.is_dir():
        for p in agents_dir.glob("*"):
            findings.extend(check_file(p, registry_names))

    # Check install_structure.py
    findings.extend(check_file(SKILL_ROOT / "install_structure.py", registry_names))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check tool name drift")
    parser.add_argument("--json", dest="json_output", default=None)
    args = parser.parse_args()

    findings = check_all()
    p0 = sum(1 for f in findings if f.severity == "P0")
    p1 = sum(1 for f in findings if f.severity == "P1")
    status = "rejected" if p0 > 0 else "review-required" if p1 > 0 else "accepted"

    result = {
        "status": status,
        "summary": {"P0": p0, "P1": p1, "P2": 0},
        "findings": [f.to_dict() for f in findings],
        "registryTools": sorted(load_registry_names()),
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(output, encoding="utf-8")
    print(output)
    return 1 if p0 > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
