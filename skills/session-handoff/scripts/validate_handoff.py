#!/usr/bin/env python3
"""Validate a session handoff document for structure, evidence, and safety."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_SECTIONS = [
    "## 1. Handoff Objective",
    "## 2. Current Status",
    "## 3. Completed Work",
    "## 4. Unfinished Work And Next Actions",
    "## 5. Key Decisions",
    "## 6. Important Files And Reports",
    "## 7. Risks, Blockers, And Forbidden Actions",
    "## 8. Suggested Skills",
    "## 9. Sensitive Information Handling",
    "## 10. Recovery Prompt For The Next Agent",
]

EVIDENCE_RE = re.compile(r"\[(?:V|R|\?)\]")
SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|"
    r"(?i:password|token|cookie|api[_-]?key|secret)\s*[:=]\s*\S+"
)
RECOVERY_RE = re.compile(r"Recovery Prompt|Read this handoff first", re.IGNORECASE)


@dataclass
class Finding:
    severity: str
    rule: str
    message: str
    fix: str


def add(findings: list[Finding], severity: str, rule: str, message: str, fix: str) -> None:
    findings.append(Finding(severity, rule, message, fix))


def validate_text(text: str) -> dict[str, object]:
    findings: list[Finding] = []

    if not text.lstrip().startswith("# Session Handoff:"):
        add(findings, "P1", "title", "Document must start with '# Session Handoff:'.", "Use the bundled handoff template.")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            add(findings, "P1", "required-section", f"Missing section: {section}", "Add the required section.")

    marker_count = len(EVIDENCE_RE.findall(text))
    if marker_count < 5:
        add(findings, "P1", "evidence-markers", "Too few evidence markers.", "Mark key claims with [V], [R], or [?].")

    if SECRET_RE.search(text):
        add(findings, "P0", "secret-pattern", "Potential secret or credential pattern detected.", "Redact the value and document how to re-request it.")

    if not RECOVERY_RE.search(text):
        add(findings, "P1", "recovery-prompt", "Recovery prompt is missing.", "Add a prompt for the next agent.")

    line_count = len(text.splitlines())
    if line_count > 500:
        add(findings, "P2", "too-long", f"Handoff is {line_count} lines long.", "Split into an index and child documents.")

    if "<task-name>" in text or "<path>" in text or "<handoff-path>" in text:
        add(findings, "P2", "template-placeholder", "Template placeholders remain.", "Replace placeholders with concrete values or mark unavailable.")

    counts = {severity: sum(1 for item in findings if item.severity == severity) for severity in ["P0", "P1", "P2"]}
    status = "rejected" if counts["P0"] else "review-required" if counts["P1"] else "accepted-with-constraints"
    return {
        "status": status,
        "summary": counts,
        "lineCount": line_count,
        "evidenceMarkerCount": marker_count,
        "findings": [asdict(item) for item in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a session handoff markdown file.")
    parser.add_argument("handoff_file", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    if not args.handoff_file.exists():
        report = {
            "status": "rejected",
            "summary": {"P0": 1, "P1": 0, "P2": 0},
            "findings": [
                asdict(
                    Finding(
                        "P0",
                        "file-missing",
                        f"Handoff file does not exist: {args.handoff_file}",
                        "Provide a valid handoff markdown file.",
                    )
                )
            ],
        }
    else:
        report = validate_text(args.handoff_file.read_text(encoding="utf-8", errors="replace"))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["P0"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
