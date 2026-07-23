#!/usr/bin/env python3
"""Validate Markdown and JSON artifacts produced by auto-testcase-generator."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CASE_RE = re.compile(r"^#{4,5}\s+tc-(P[0-3]):(.+)$", re.IGNORECASE)
STEP_RE = re.compile(r"^#{5,6}\s+(?:Step|步骤)\s*(\d+)[：:]\s*(.+)$", re.IGNORECASE)
EXPECTED_RE = re.compile(r"^\*\s+(?:Expected|预期)[：:]\s*(.+)$", re.IGNORECASE)
SOURCE_RE = re.compile(r"SRC-[A-Za-z0-9_-]+")
VAGUE_RE = re.compile(
    r"\b(enter page|click button|select content|submit form|check list|view list|locate data)\b",
    re.IGNORECASE,
)
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|password\s*[:=]|token\s*[:=]|cookie\s*[:=])",
    re.IGNORECASE,
)


def add(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if SECRET_RE.search(text):
        add(errors, f"{path}: possible secret or credential pattern")

    case_count = 0
    current_case: str | None = None
    current_case_line = 0
    current_case_has_source = False
    current_step = 0
    current_step_has_expected = True

    for idx, line in enumerate(lines, start=1):
        case_match = CASE_RE.match(line)
        if case_match:
            if current_case and not current_step_has_expected:
                add(errors, f"{path}:{idx - 1}: previous step in {current_case} has no Expected line")
            if current_case and not current_case_has_source:
                add(errors, f"{path}:{current_case_line}: {current_case} has no SRC-* evidence note")
            case_count += 1
            current_case = line.strip()
            current_case_line = idx
            current_case_has_source = False
            current_step = 0
            current_step_has_expected = True
            continue

        if current_case and SOURCE_RE.search(line):
            current_case_has_source = True

        step_match = STEP_RE.match(line)
        if step_match:
            if current_case is None:
                add(errors, f"{path}:{idx}: step appears before a test case")
            if not current_step_has_expected:
                add(errors, f"{path}:{idx - 1}: previous step in {current_case} has no Expected line")
            step_number = int(step_match.group(1))
            action = step_match.group(2).strip()
            if step_number != current_step + 1:
                add(errors, f"{path}:{idx}: step number should be {current_step + 1}, got {step_number}")
            if VAGUE_RE.search(action):
                add(errors, f"{path}:{idx}: vague step action: {action}")
            if len(action) < 12:
                add(errors, f"{path}:{idx}: step action is too short")
            current_step = step_number
            current_step_has_expected = False
            continue

        if current_case and EXPECTED_RE.match(line):
            current_step_has_expected = True

    if current_case and not current_step_has_expected:
        add(errors, f"{path}: final step in {current_case} has no Expected line")
    if current_case and not current_case_has_source:
        add(errors, f"{path}:{current_case_line}: {current_case} has no SRC-* evidence note")
    if case_count == 0:
        add(errors, f"{path}: no tc-P0/tc-P1/tc-P2/tc-P3 cases found")
    return errors


def require_type(errors: list[str], obj: dict[str, Any], key: str, expected: type, context: str) -> None:
    if key not in obj:
        add(errors, f"{context}: missing {key}")
    elif not isinstance(obj[key], expected):
        add(errors, f"{context}: {key} must be {expected.__name__}")


def validate_trace(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return [f"{path}: top-level JSON must be an object"]
    sources = data.get("sources")
    cases = data.get("cases")
    if not isinstance(sources, list):
        add(errors, f"{path}: sources must be a list")
        sources = []
    if not isinstance(cases, list):
        add(errors, f"{path}: cases must be a list")
        cases = []

    source_ids = set()
    for i, source in enumerate(sources):
        context = f"{path}:sources[{i}]"
        if not isinstance(source, dict):
            add(errors, f"{context}: source must be an object")
            continue
        require_type(errors, source, "sourceId", str, context)
        require_type(errors, source, "type", str, context)
        require_type(errors, source, "confidence", str, context)
        if isinstance(source.get("sourceId"), str):
            source_ids.add(source["sourceId"])

    case_ids = set()
    for i, case in enumerate(cases):
        context = f"{path}:cases[{i}]"
        if not isinstance(case, dict):
            add(errors, f"{context}: case must be an object")
            continue
        for key in ("caseId", "title", "priority", "oracle", "confidence", "changeStatus"):
            require_type(errors, case, key, str, context)
        if case.get("priority") not in {"P0", "P1", "P2", "P3"}:
            add(errors, f"{context}: priority must be P0/P1/P2/P3")
        if isinstance(case.get("caseId"), str):
            if case["caseId"] in case_ids:
                add(errors, f"{context}: duplicate caseId {case['caseId']}")
            case_ids.add(case["caseId"])
        module_path = case.get("modulePath")
        if not isinstance(module_path, list) or not module_path or not all(isinstance(x, str) and x for x in module_path):
            add(errors, f"{context}: modulePath must be a non-empty string list")
        case_sources = case.get("sourceIds")
        if not isinstance(case_sources, list) or not case_sources:
            add(errors, f"{context}: sourceIds must be a non-empty list")
        else:
            for source_id in case_sources:
                if source_id not in source_ids:
                    add(errors, f"{context}: unknown sourceId {source_id}")
        steps = case.get("steps")
        if not isinstance(steps, list) or not steps:
            add(errors, f"{context}: steps must be a non-empty list")
        else:
            for step_index, step in enumerate(steps):
                step_context = f"{context}.steps[{step_index}]"
                if not isinstance(step, dict):
                    add(errors, f"{step_context}: step must be an object")
                    continue
                require_type(errors, step, "action", str, step_context)
                require_type(errors, step, "expected", str, step_context)
                if isinstance(step.get("action"), str) and VAGUE_RE.search(step["action"]):
                    add(errors, f"{step_context}: vague action: {step['action']}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    if not args.markdown.exists():
        add(errors, f"{args.markdown}: file not found")
    else:
        errors.extend(validate_markdown(args.markdown))
    if not args.trace.exists():
        add(errors, f"{args.trace}: file not found")
    else:
        try:
            errors.extend(validate_trace(args.trace))
        except json.JSONDecodeError as exc:
            add(errors, f"{args.trace}: invalid JSON: {exc}")

    if errors:
        print("validation: failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("validation: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
