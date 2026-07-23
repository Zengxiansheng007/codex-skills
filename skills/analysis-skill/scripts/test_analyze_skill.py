#!/usr/bin/env python3
"""Deterministic tests for the R0 analyzer using safe fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ANALYZER = ROOT / "scripts" / "analyze_skill.py"
GITHUB_SNAPSHOT = ROOT / "scripts" / "fetch_github_snapshot.py"
THIRD_PARTY = ROOT / "scripts" / "run_third_party_checks.py"
SANDBOX = ROOT / "scripts" / "sandbox_runner.py"
LLM_REVIEW = ROOT / "scripts" / "llm_review.py"
FIXTURES = ROOT / "assets" / "fixtures"


def run(source: Path, output: Path, expected_code: int = 0) -> dict:
    process = subprocess.run([sys.executable, str(ANALYZER), str(source), "--output", str(output), "--profile", "codex"], capture_output=True, text=True)
    assert process.returncode == expected_code, process.stderr or process.stdout
    if expected_code:
        return {}
    assert output.exists(), "HTML report missing"
    index = output.with_suffix(".json")
    assert index.exists(), "JSON index missing"
    return json.loads(index.read_text(encoding="utf-8"))


def has_rule(report: dict, rule_id: str) -> bool:
    return any(item["ruleId"] == rule_id for item in report["findings"])


def run_script(args: list[str], expected_code: int = 0) -> subprocess.CompletedProcess[str]:
    process = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    assert process.returncode == expected_code, process.stderr or process.stdout
    return process


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="analysis-skill-test-") as temp:
        output = Path(temp) / "safe.html"
        safe = run(FIXTURES / "safe-skill", output)
        assert safe["frontmatter"]["name"] == "safe-skill"
        assert safe["summary"]["P0"] == 0
        assert safe["decision"]["status"] == "sandbox-only"
        assert safe["analysisPurpose"] in {"adoption", "redesign", "adoption-and-redesign"}
        assert safe["securityAnalysis"]["decision"]["status"] == safe["decision"]["status"]
        assert safe["designAnalysis"]["problemSolved"]
        assert safe["runtimeModel"]["workflowStages"]
        assert safe["logicDesign"]["modules"]
        assert safe["resourceRoleMatrix"]
        assert safe["redesignBacklog"]
        assert len(safe["evalRecommendations"]) >= 5
        assert all(item.get("evidenceIds") for item in safe["findings"] if item["severity"] in {"P0", "P1"})
        html_text = output.read_text(encoding="utf-8")
        assert "Skill 静态与重设计分析报告" in html_text
        assert "逻辑设计" in html_text

        invalid = run(FIXTURES / "bad-yaml-skill", Path(temp) / "bad.html")
        assert has_rule(invalid, "FRONTMATTER-INVALID")
        assert invalid["summary"]["P0"] >= 1
        assert invalid["decision"]["status"] == "rerun"

        dangerous = run(FIXTURES / "dangerous-skill", Path(temp) / "danger.html")
        assert has_rule(dangerous, "RISK-DOWNLOAD-EXEC")
        assert dangerous["decision"]["status"] == "review-required"

        injection = run(FIXTURES / "injection-skill", Path(temp) / "injection.html")
        assert has_rule(injection, "RISK-PROMPT-INJECTION")
        assert any(item.get("evidenceIds") for item in injection["findings"] if item["ruleId"] == "RISK-PROMPT-INJECTION")

        bad_zip = Path(temp) / "unsafe.zip"
        with zipfile.ZipFile(bad_zip, "w") as archive:
            archive.writestr("../outside.txt", "harmless")
        run(bad_zip, Path(temp) / "zip.html", expected_code=1)

        blocked_snapshot = run_script(
            [str(GITHUB_SNAPSHOT), "octocat/Hello-World", "--ref", "main", "--output-dir", str(Path(temp) / "snapshots"), "--report", str(Path(temp) / "github.html")],
            expected_code=2,
        )
        assert "network access is disabled" in blocked_snapshot.stderr

        third_party = Path(temp) / "third-party.html"
        run_script([str(THIRD_PARTY), str(FIXTURES / "safe-skill"), "--output", str(third_party), "--scanner", str(Path(temp) / "missing-scanner.exe"), "--timeout", "1"])
        third_party_report = json.loads(third_party.with_suffix(".json").read_text(encoding="utf-8"))
        assert any(item["adapter"] == "cisco-ai-skill-scanner" and item["status"] == "unverified" for item in third_party_report["adapters"])

        sandbox = Path(temp) / "sandbox.html"
        run_script([str(SANDBOX), "--source", str(FIXTURES / "safe-skill"), "--output", str(sandbox), "--command-json", "[\"python\",\"--version\"]", "--dry-run"])
        sandbox_report = json.loads(sandbox.with_suffix(".json").read_text(encoding="utf-8"))
        assert sandbox_report["status"] == "dry-run"
        assert sandbox_report["network"] == "none"

        llm = Path(temp) / "llm.html"
        run_script([str(LLM_REVIEW), str(FIXTURES / "safe-skill"), "--output", str(llm), "--dry-run"])
        llm_report = json.loads(llm.with_suffix(".json").read_text(encoding="utf-8"))
        assert llm_report["status"] == "dry-run"
        assert llm_report["payloadPreview"]["skillMdChars"] > 0

        self_report = run(ROOT, Path(temp) / "self.html")
        missing_resources = [item for item in self_report["findings"] if item["ruleId"] == "RESOURCE-MISSING"]
        assert not any("--source" in item["message"] or "--output" in item["message"] for item in missing_resources)
        assert self_report["logicDesign"]["pipeline"]
    print("ok: analyzer tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
