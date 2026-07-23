#!/usr/bin/env python3
"""Validate the router's deterministic fixture contract without model calls."""
import json
import re
import sys
from pathlib import Path

EXPECTED_ACCEPTANCE = {f"AT-{number:02d}" for number in range(1, 13)}
EXPECTED_IDS = {f"TR-{number:02d}" for number in range(1, 14)}
STATES = {"new-task", "ordinary-execution", "clarification-pending", "safety-approval-pending", "full-grill-active", "target-change"}
REQUIRED_CASE_FIELDS = {"id", "acceptanceIds", "requirementIds", "sessionState", "input", "expectedMode", "requiredObservableMarkers", "forbiddenBehaviors"}
SENSITIVE = [
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"A[K]IA[0-9A-Z]{16}"),
    re.compile(r"(?i)(password|token|secret)\s*[:=]\s*[^\s]{8,}"),
    re.compile(r"(?i)(authorization|cookie)\s*[:=]"),
]


def add_error(errors, message):
    errors.append(message)


def main(path_text):
    path = Path(path_text)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [f"cannot read fixture suite: {exc}"]}, ensure_ascii=False, indent=2))
        return 1
    errors = []
    if payload.get("schemaVersion") != 1:
        add_error(errors, "schemaVersion must equal 1")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        add_error(errors, "cases must be an array")
        cases = []
    ids, acceptance_ids = set(), set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            add_error(errors, f"{prefix} must be an object")
            continue
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            add_error(errors, f"{prefix} missing fields: {', '.join(sorted(missing))}")
        case_id = case.get("id")
        if case_id in ids:
            add_error(errors, f"duplicate id: {case_id}")
        ids.add(case_id)
        if case.get("sessionState") not in STATES:
            add_error(errors, f"{case_id} has invalid sessionState")
        if not isinstance(case.get("acceptanceIds"), list) or not isinstance(case.get("requirementIds"), list):
            add_error(errors, f"{case_id} acceptanceIds and requirementIds must be arrays")
        else:
            acceptance_ids.update(case["acceptanceIds"])
            if any(not value.startswith("FR-") for value in case["requirementIds"]):
                add_error(errors, f"{case_id} has invalid requirement ID")
        if not case.get("requiredObservableMarkers") or not case.get("forbiddenBehaviors"):
            add_error(errors, f"{case_id} requires observable and forbidden markers")
        rendered = json.dumps(case, ensure_ascii=False)
        if any(pattern.search(rendered) for pattern in SENSITIVE):
            add_error(errors, f"{case_id} contains a sensitive-data pattern")
    if ids != EXPECTED_IDS:
        add_error(errors, f"fixture IDs must be {sorted(EXPECTED_IDS)}")
    if acceptance_ids != EXPECTED_ACCEPTANCE:
        add_error(errors, f"acceptance IDs must be {sorted(EXPECTED_ACCEPTANCE)}")
    result = {"ok": not errors, "caseCount": len(cases), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_fixture_suite.py <fixture-suite.json>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
