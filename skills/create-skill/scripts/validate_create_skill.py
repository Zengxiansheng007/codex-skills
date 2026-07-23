#!/usr/bin/env python3
"""Validate a Codex Agent Skill package for structure, safety, and maintainability."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
RESOURCE_RE = re.compile(r"(?<![\w.-])((?:references|scripts|assets)/[A-Za-z0-9_./ -]+\.[A-Za-z0-9]+)")
SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|(?i:password|token|cookie)\s*[:=]\s*\S+"
)
DANGEROUS_PATTERNS = [
    r"\b" + "rm" + r"\s+-rf",
    "Remove" + r"-Item\b[^\n]*-Recurse[^\n]*-Force",
    "Invoke" + r"-WebRequest\b[^\n|]*\|\s*" + "Invoke" + r"-Expression",
    "curl" + r"\b[^\n|]*\|\s*(?:sh|bash)",
]
DANGEROUS_RE = re.compile(r"(?:%s)" % "|".join(DANGEROUS_PATTERNS), re.IGNORECASE)


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    message: str
    fix: str


def add(findings: list[Finding], severity: str, rule: str, file: Path | str, message: str, fix: str) -> None:
    findings.append(Finding(severity, rule, str(file), message, fix))


def parse_frontmatter(skill_file: Path, findings: list[Finding]) -> tuple[dict[str, Any] | None, str]:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        add(findings, "P0", "frontmatter-missing", skill_file, "SKILL.md is missing YAML frontmatter.", "Add name and description frontmatter.")
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        add(findings, "P0", "frontmatter-unclosed", skill_file, "YAML frontmatter is not closed.", "Close frontmatter with --- on its own line.")
        return None, text
    raw = text[4:end]
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as error:
        add(findings, "P0", "frontmatter-invalid", skill_file, f"YAML parse failed: {error}", "Fix YAML syntax.")
        return None, text
    if not isinstance(data, dict):
        add(findings, "P0", "frontmatter-object", skill_file, "Frontmatter must be a mapping.", "Use name and description keys.")
        return None, text
    extra = sorted(set(data) - {"name", "description"})
    if extra:
        add(findings, "P1", "frontmatter-extra-fields", skill_file, f"Extra frontmatter fields: {', '.join(extra)}.", "Remove unless target runtime explicitly supports them.")
    return data, text


def validate(root: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    skill_file = root / "SKILL.md"
    if not root.exists() or not root.is_dir():
        add(findings, "P0", "root-missing", root, "Skill folder does not exist.", "Provide a valid skill folder.")
        return result(root, None, findings)
    if not skill_file.exists():
        add(findings, "P0", "skill-md-missing", skill_file, "SKILL.md is required.", "Create SKILL.md.")
        return result(root, None, findings)

    frontmatter, text = parse_frontmatter(skill_file, findings)
    if frontmatter:
        name = frontmatter.get("name")
        description = frontmatter.get("description")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            add(findings, "P1", "name-format", skill_file, "name must be lowercase hyphen-case.", "Rename the skill and folder consistently.")
        elif name != root.name:
            add(findings, "P1", "name-folder-mismatch", skill_file, f"name '{name}' does not match folder '{root.name}'.", "Make frontmatter name match folder.")
        if not isinstance(description, str) or len(description.strip()) < 80:
            add(findings, "P1", "description-too-weak", skill_file, "description is missing or too short for reliable triggering.", "Name capability and specific trigger contexts.")
        elif not re.search(r"\bUse when\b|when asked|Use if|Use for", description, re.IGNORECASE):
            add(findings, "P2", "description-trigger-wording", skill_file, "description lacks explicit trigger wording.", "Add 'Use when...' style trigger phrases.")

    if "## Validation" not in text:
        add(findings, "P1", "validation-section-missing", skill_file, "Validation section is missing.", "Add commands or checks proving the skill works.")
    if "## Escalation" not in text and "## Safety" not in text:
        add(findings, "P1", "safety-section-missing", skill_file, "Safety or escalation section is missing.", "Document approval and refusal conditions.")
    if len(text.splitlines()) > 500:
        add(findings, "P2", "skill-md-sprawl", skill_file, "SKILL.md is over 500 lines.", "Move long rules or examples to references/.")

    all_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() not in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico"}
    ]
    for path in all_files:
        rel = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            if "SECRET_RE =" in line or "DANGEROUS_RE =" in line:
                continue
            if SECRET_RE.search(line):
                add(findings, "P0", "secret-pattern", rel, "Potential secret or credential pattern detected.", "Remove secret and rotate if real.")
                break
        for line in content.splitlines():
            if "DANGEROUS_RE =" in line:
                continue
            if DANGEROUS_RE.search(line):
                add(findings, "P0", "dangerous-command", rel, "Potential dangerous command pattern detected.", "Remove or gate behind explicit approval and sandboxing.")
                break

    for match in LINK_RE.finditer(text):
        target = match.group(1).split("#", 1)[0].strip()
        if not target or re.match(r"^(?:https?://|mailto:)", target):
            continue
        if not (root / target).exists():
            add(findings, "P1", "link-missing", skill_file, f"Linked resource is missing: {target}", "Fix or remove the link.")

    referenced: set[str] = set()
    for match in RESOURCE_RE.finditer(text):
        target = match.group(1).strip()
        referenced.add(target.split("/", 1)[0])
        if not (root / target).exists():
            add(findings, "P1", "resource-missing", skill_file, f"Referenced resource is missing: {target}", "Create it or update the path.")

    for folder in ["references", "scripts", "assets"]:
        candidate = root / folder
        if candidate.exists() and not any(str(path).startswith(str(candidate)) for path in all_files):
            add(findings, "P2", "empty-resource-folder", candidate, f"{folder}/ is empty.", "Remove empty resource folder.")
        if candidate.exists() and folder not in referenced and folder != "assets":
            add(findings, "P2", "resource-folder-unreferenced", candidate, f"{folder}/ is not mentioned from SKILL.md.", "Add a context pointer or remove the folder.")

    return result(root, frontmatter, findings)


def result(root: Path, frontmatter: dict[str, Any] | None, findings: list[Finding]) -> dict[str, Any]:
    counts = {severity: sum(1 for item in findings if item.severity == severity) for severity in ["P0", "P1", "P2"]}
    status = "rejected" if counts["P0"] else "review-required" if counts["P1"] else "accepted-with-constraints"
    return {
        "skillRoot": str(root.resolve()),
        "frontmatter": frontmatter,
        "summary": counts,
        "status": status,
        "findings": [asdict(item) for item in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Codex Agent Skill package")
    parser.add_argument("skill_folder", type=Path)
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)
    report = validate(args.skill_folder)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["P0"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
