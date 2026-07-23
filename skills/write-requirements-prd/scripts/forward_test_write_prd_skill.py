import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return path.read_text(encoding="utf-8")


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def assert_contains(text, needle, label):
    if needle not in text:
        fail(f"missing {label}: {needle}")


def assert_regex(text, pattern, label):
    if not re.search(pattern, text, re.MULTILINE):
        fail(f"missing {label}: {pattern}")


def main():
    skill = read(ROOT / "SKILL.md")
    routing = read(ROOT / "references" / "document-type-routing.md")
    contract = read(ROOT / "references" / "dev-test-plan-contract.md")
    checklist = read(ROOT / "references" / "review-checklist.md")
    framework = read(ROOT / "references" / "prd-framework.md")
    schema = read(ROOT / "references" / "agent-ready-output-schema.md")
    boundary = read(ROOT / "references" / "capability-boundary-map.md")
    governance = read(ROOT / "references" / "governance-diagnostics.md")
    agent_yaml = read(ROOT / "agents" / "openai.yaml")
    cases_path = ROOT / "assets" / "forward-tests" / "write-requirements-prd-forward-tests.json"
    cases = json.loads(read(cases_path))["cases"]

    assert_regex(skill, r"^---\s*\nname: write-requirements-prd\n.*?\n---", "frontmatter")
    for ref in [
        "references/prd-framework.md",
        "references/document-type-routing.md",
        "references/dev-test-plan-contract.md",
        "references/review-checklist.md",
        "references/agent-ready-output-schema.md",
        "references/capability-boundary-map.md",
        "references/governance-diagnostics.md",
    ]:
        assert_contains(skill, ref, "SKILL reference")

    assert_contains(skill, "If the user only asks for a brief explanation", "lightweight trigger boundary")
    assert_contains(skill, "apply reference priority", "reference priority")
    assert_contains(agent_yaml, "dev-test plans", "openai short description")
    assert_contains(agent_yaml, "classify this artifact type", "openai default prompt")
    assert_contains(routing, "lightweight explanation requests", "routing lightweight anti-overgeneration")
    assert_contains(contract, "Complete repair gate", "complete repair gate")
    assert_contains(checklist, "Complete Repair Review", "review checklist complete repair")
    assert_contains(framework, "RTM", "framework RTM")
    assert_contains(schema, "Required Top-level Fields", "agent-ready schema fields")
    assert_contains(boundary, "Handoff to ui-test", "capability boundary ui-test handoff")
    assert_contains(governance, "Change Impact Analysis", "governance change impact")

    routes = {
        "business PRD or feature requirement": routing,
        "permission matrix or data access rule": routing,
        "state machine or workflow rule": routing,
        "development and test plan PRD": routing + contract,
        "ui-automation requirement": schema + boundary + checklist,
        "lightweight explanation": skill,
    }

    for case in cases:
        route_text = routes.get(case["expectedRoute"])
        if not route_text:
            fail(f"{case['id']} has unknown route {case['expectedRoute']}")
        for ref in case["mustRead"]:
            assert_contains(skill, ref, f"{case['id']} mustRead reference")

        combined = "\n".join([
            skill,
            routing,
            contract,
            checklist,
            framework,
            schema,
            boundary,
            governance,
            agent_yaml,
        ])
        for term in case["mustInclude"]:
            if term == "direct answer":
                assert_contains(skill, "answer directly", f"{case['id']} direct answer rule")
            else:
                assert_contains(combined, term, f"{case['id']} mustInclude")

        for forbidden in case["mustNotInclude"]:
            if forbidden in combined:
                fail(f"{case['id']} forbidden term found in skill package: {forbidden}")

    secret_pattern = re.compile(
        r"sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|"
        r"(password|token|cookie|apiKey|secret)\s*[:=]\s*['\"]?[^\s'\"]{8,}",
        re.IGNORECASE,
    )
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".json", ".py"}:
            text = read(path)
            match = secret_pattern.search(text)
            if match:
                fail(f"possible secret in {path}: {match.group(0)}")

    print(f"PASS: {len(cases)} forward-test contracts validated")


if __name__ == "__main__":
    main()
