#!/usr/bin/env python3
"""Deterministic tests for create-skill validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate_create_skill.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_validate(folder: Path) -> dict:
    process = subprocess.run([sys.executable, str(VALIDATOR), str(folder)], capture_output=True, text=True)
    assert process.returncode in {0, 1}, process.stderr
    return json.loads(process.stdout)


def has_rule(report: dict, rule: str) -> bool:
    return any(item["rule"] == rule for item in report["findings"])


def main() -> int:
    self_report = run_validate(ROOT)
    assert self_report["summary"]["P0"] == 0, self_report
    assert self_report["status"] in {"accepted-with-constraints", "review-required"}

    with tempfile.TemporaryDirectory(prefix="create-skill-test-") as tempdir:
        temp = Path(tempdir)

        good = temp / "good-skill"
        write(
            good / "SKILL.md",
            """---
name: good-skill
description: Create concise example reports from supplied notes. Use when asked to turn notes into a structured report, validate report shape, or package a reusable reporting workflow.
---

# Good Skill

## Operating Rules

- Keep reports concise.

## Workflow

1. Read the notes.
2. Produce the report.

## Validation

Run the report shape check.

## Escalation

Ask before writing outside the output directory.
""",
        )
        good_report = run_validate(good)
        assert good_report["summary"]["P0"] == 0, good_report

        bad = temp / "bad-skill"
        secret = "pass" + "word=abc123"
        destructive = "Remove" + "-Item C:\\temp -Recurse -Force"
        write(
            bad / "SKILL.md",
            f"""---
name: bad
description: Helps.
extra: nope
---

# Bad Skill

Run this with {secret} and then {destructive}.
""",
        )
        bad_report = run_validate(bad)
        assert has_rule(bad_report, "name-folder-mismatch")
        assert has_rule(bad_report, "frontmatter-extra-fields")
        assert has_rule(bad_report, "description-too-weak")
        assert has_rule(bad_report, "secret-pattern")
        assert has_rule(bad_report, "dangerous-command")
        assert bad_report["summary"]["P0"] >= 2

        missing_ref = temp / "missing-ref"
        write(
            missing_ref / "SKILL.md",
            """---
name: missing-ref
description: Review skill resources and validate links. Use when asked to check references, scripts, assets, or package shape in an existing skill.
---

# Missing Ref

Read [the guide](references/guide.md).

## Validation

Validate links.

## Escalation

Ask before external access.
""",
        )
        missing_report = run_validate(missing_ref)
        assert has_rule(missing_report, "link-missing")
    print("ok: create-skill tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
