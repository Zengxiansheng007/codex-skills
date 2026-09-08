#!/usr/bin/env python3
"""Deterministic tests for research skill validator."""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate_research_skill.py"
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
def run_validate(folder, require_cr=False):
    cmd = [sys.executable, str(VALIDATOR), str(folder)]
    if require_cr: cmd.append("--require-change-records")
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode in {0, 1}, p.stderr
    return json.loads(p.stdout)
def has_rule(report, rule):
    return any(item["rule"] == rule for item in report["findings"])
def main():
    self_report = run_validate(ROOT)
    assert self_report["summary"]["P0"] == 0, self_report
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    light_ref = ROOT / "references" / "strong-gate-and-light-path.md"
    assert light_ref.exists(), light_ref
    assert "Every research invocation must enter the strong-gate flow by default." in skill_text
    assert "user confirms the downgrade" in skill_text
    assert "light research is an explicit exception" in skill_text.lower()
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "good-skill"
        write(good / "SKILL.md", "---\nname: good-skill\ndescription: Research a topic and produce reports. Use when asked to investigate, gather evidence, or validate source coverage.\n---\n# Good Skill\n## Operating Rules\n- Keep it concise.\n## Workflow\n1. Read.\n## Validation\nRun checks.\n## Escalation\nAsk before external access.\n")
        r = run_validate(good)
        assert r["summary"]["P0"] == 0, r
    print("ok: research-skill tests passed")
    return 0
if __name__ == "__main__": raise SystemExit(main())
