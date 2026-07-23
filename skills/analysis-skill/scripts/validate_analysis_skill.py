#!/usr/bin/env python3
"""Minimal deterministic validator for analysis-skill package structure."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    skill = root / "SKILL.md"
    errors: list[str] = []
    if not skill.exists():
        errors.append("missing SKILL.md")
    else:
        text = skill.read_text(encoding="utf-8")
        blocks = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not blocks:
            errors.append("invalid frontmatter fence")
        else:
            data = yaml.safe_load(blocks.group(1))
            if not isinstance(data, dict) or set(data) != {"name", "description"}:
                errors.append("frontmatter must contain only name and description")
            elif data["name"] != "analysis-skill":
                errors.append("frontmatter name must equal analysis-skill")
            elif not isinstance(data["description"], str) or len(data["description"].strip()) < 30:
                errors.append("description is missing or too vague")
        for target in re.findall(r"\((references/[^)]+)\)", text):
            if not (root / target).exists():
                errors.append(f"missing referenced resource: {target}")
        if "--purpose" not in text:
            errors.append("SKILL.md must document --purpose")
        if "designAnalysis" not in text or "logicDesign" not in text:
            errors.append("SKILL.md must describe redesign analysis outputs")
    for required in [
        "agents/openai.yaml",
        "references/analysis-contract.md",
        "references/design-runtime-logic.md",
        "references/risk-and-decision.md",
        "references/execution-adapters.md",
        "scripts/analyze_skill.py",
        "scripts/fetch_github_snapshot.py",
        "scripts/run_third_party_checks.py",
        "scripts/sandbox_runner.py",
        "scripts/llm_review.py",
        "scripts/test_analyze_skill.py",
    ]:
        if not (root / required).exists():
            errors.append(f"missing required file: {required}")
    analyzer = root / "scripts" / "analyze_skill.py"
    if analyzer.exists():
        analyzer_text = analyzer.read_text(encoding="utf-8")
        for required_field in [
            "analysisPurpose",
            "securityAnalysis",
            "designAnalysis",
            "runtimeModel",
            "logicDesign",
            "redesignBacklog",
            "evalRecommendations",
        ]:
            if required_field not in analyzer_text:
                errors.append(f"analyzer missing field support: {required_field}")
        if "--purpose" not in analyzer_text:
            errors.append("analyzer missing --purpose CLI option")
    if errors:
        print("validation failed:")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print(f"ok: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
