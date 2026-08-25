#!/usr/bin/env python3
"""Validate ui-test-execution-report skill and generated artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SECRET_RE = re.compile(
    r"(password\s*[:=]\s*['\"][^'\"]+|authorization\s*[:=]\s*['\"][^'\"]+|cookie\s*[:=]\s*['\"][^'\"]+|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)


def finding(severity: str, rule: str, message: str, path: Path | None = None) -> dict[str, str]:
    item = {"severity": severity, "rule": rule, "message": message}
    if path:
        item["path"] = str(path)
    return item


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_skill(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    required = [
        root / "SKILL.md",
        root / "agents" / "openai.yaml",
        root / "references" / "report-contract.md",
        root / "scripts" / "generate_report.py",
        root / "assets" / "sample-run.json",
        root / "docs" / "requirement-anchor.json",
        root / "docs" / "development-plan.md",
        root / "docs" / "test-plan.md",
    ]
    for path in required:
        if not path.exists():
            findings.append(finding("P0", "missing-required-file", f"missing {path.name}", path))
    skill = root / "SKILL.md"
    if skill.exists():
        text = read_text(skill)
        if "name: ui-test-execution-report" not in text:
            findings.append(finding("P0", "frontmatter-name", "SKILL.md name must match folder", skill))
        for ref in ("references/report-contract.md", "scripts/generate_report.py", "scripts/validate_execution_report_skill.py"):
            if ref not in text:
                findings.append(finding("P1", "missing-skill-reference", f"SKILL.md must reference {ref}", skill))
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".py", ".yaml", ".html"}:
            text = read_text(path)
            if SECRET_RE.search(text):
                findings.append(finding("P0", "secret-pattern", "possible live secret found", path))
    return findings


def find_report(root: Path) -> Path | None:
    matches = list((root / "human-html").rglob("report.html"))
    return matches[0] if matches else None


def validate_generated(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    report = find_report(root)
    if not report:
        return [finding("P0", "generated-report-missing", "report.html not found", root)]
    text = read_text(report)
    screenshot_count = text.count("截图缩略图（点击放大）")
    api_count = text.count("点击查看 JSON")
    if screenshot_count < 6:
        findings.append(finding("P0", "embedded-screenshot-count", f"expected at least 6 embedded screenshots, got {screenshot_count}", report))
    if api_count < 4:
        findings.append(finding("P0", "embedded-api-json-count", f"expected at least 4 embedded API JSON blocks, got {api_count}", report))
    for marker in ("附件索引（治理用）", "接口汇总索引（治理用）", "第 4 章"):
        if marker not in text:
            findings.append(finding("P1", "generated-marker-missing", f"missing marker {marker}", report))
    for legacy in ("完整截图墙", "旧版独立证据展示区", "证据与 JSON</th>"):
        if legacy in text:
            findings.append(finding("P1", "legacy-evidence-wall", f"legacy evidence wall marker remains: {legacy}", report))
    if SECRET_RE.search(text):
        findings.append(finding("P0", "generated-secret-pattern", "generated HTML contains possible live secret", report))
    evidence = list((root / "agent-readable").rglob("evidence-index.json"))
    summary = list((root / "agent-readable").rglob("execution-summary.json"))
    run_results = list((root / "agent-readable").rglob("run-result.json"))
    if not evidence:
        findings.append(finding("P0", "evidence-index-missing", "evidence-index.json not found", root))
    else:
        data = json.loads(read_text(evidence[0]))
        if data.get("layout_contract") != "step-table-embedded-evidence":
            findings.append(finding("P1", "layout-contract-missing", "layout_contract must be step-table-embedded-evidence", evidence[0]))
    if not summary:
        findings.append(finding("P0", "execution-summary-missing", "execution-summary.json not found", root))
    else:
        data = json.loads(read_text(summary[0]))
        if data.get("ui_screenshot_count", 0) < 6 or data.get("api_assertion_count", 0) < 4:
            findings.append(finding("P1", "summary-counts-invalid", "summary evidence counts are below sample expectations", summary[0]))
    if not run_results:
        findings.append(finding("P0", "canonical-run-result-missing", "run-result.json not found", root))
    else:
        canonical = json.loads(read_text(run_results[0]))
        if canonical.get("schema_version") != "ui-test.run-result.v2":
            findings.append(finding("P0", "canonical-run-result-invalid", "run-result.json is not the canonical RunResult schema", run_results[0]))
        if summary and json.loads(read_text(summary[0])).get("status") != canonical.get("overall_status"):
            findings.append(finding("P0", "result-source-conflict", "execution-summary status differs from canonical RunResult", summary[0]))
        if summary and json.loads(read_text(summary[0])).get("source_run_result_hash") != canonical.get("run_result_hash"):
            findings.append(finding("P0", "result-hash-conflict", "execution-summary hash differs from canonical RunResult", summary[0]))
    return findings


def summarize(findings: list[dict[str, str]]) -> dict[str, Any]:
    summary = {"P0": 0, "P1": 0, "P2": 0}
    for item in findings:
        if item["severity"] in summary:
            summary[item["severity"]] += 1
    return {
        "status": "passed" if summary["P0"] == 0 and summary["P1"] == 0 else "failed",
        "summary": summary,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_folder", type=Path)
    parser.add_argument("--generated-root", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    findings = validate_skill(args.skill_folder)
    if args.generated_root:
        findings.extend(validate_generated(args.generated_root))
    report = summarize(findings)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(output, encoding="utf-8")
    print(output)
    return 1 if report["summary"]["P0"] or report["summary"]["P1"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
