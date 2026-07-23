#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_packager.py"


def run(args):
    result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout


def make_sample_skill(base):
    skill = base / "sample-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "agents").mkdir()
    (skill / "SKILL.md").write_text(
        """---
name: sample-skill
description: >-
  Sample skill for packaging and migration.
---

# Sample Skill

Read `references/rules.md` when validating.
""",
        encoding="utf-8",
    )
    (skill / "references" / "rules.md").write_text("# Rules\n", encoding="utf-8")
    (skill / "agents" / "openai.yaml").write_text("name: sample-skill\nsummary: sample\n", encoding="utf-8")
    return skill


def make_named_skill(base, name, body):
    skill = base / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"""---
name: {name}
description: Sample skill for secret-scan regression.
---

# {name}

{body}
""",
        encoding="utf-8",
    )
    return skill


def main():
    temp = Path(tempfile.mkdtemp(prefix="skill-packager-test-"))
    try:
        source = make_sample_skill(temp)
        out = temp / "out"
        data = json.loads(run(["package", "--source", str(source), "--out", str(out), "--target", "workbuddy", "--dry-run"]))
        wb = out / "package-work" / "workbuddy" / "sample-skill"
        if not (wb / "SKILL.md").exists():
            raise AssertionError("missing workbuddy SKILL.md")
        if (wb / "agents").exists():
            raise AssertionError("workbuddy package should exclude agents/")
        findings = json.loads(run(["validate-workbuddy", "--skill", str(wb)]))
        if findings:
            raise AssertionError(f"unexpected workbuddy findings: {findings}")
        if not Path(data["workbuddyZip"]).exists():
            raise AssertionError("missing workbuddy zip")
        dry = json.loads(run(["deploy", "--package", str(wb), "--dest", str(temp / "skills"), "--backup-dir", str(temp / "backup"), "--dry-run"]))
        if not dry["dryRun"]:
            raise AssertionError("deploy dry-run not marked")

        router = make_named_skill(temp, "task-understanding-router", "No secrets here.")
        router_out = temp / "router-out"
        run(["package", "--source", str(router), "--out", str(router_out), "--target", "workbuddy", "--dry-run"])

        blocked_body = "Suspicious token: " + "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        blocked_skill = make_named_skill(temp, "blocked-skill", blocked_body)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "package", "--source", str(blocked_skill), "--out", str(temp / "blocked-out"), "--target", "workbuddy", "--dry-run"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            raise AssertionError("standalone sk token should still be blocked")
        print("PASS: skill-packager tests")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
