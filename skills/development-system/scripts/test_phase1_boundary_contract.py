import json
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_REFERENCE_TERMS = [
    "Mandatory Workspace-Copy-First Triggers",
    "multi-file change",
    "high-risk change",
    "global Skill edit",
    "single-file behavior change",
    "Direct Edit Exception",
    "Approval Boundary Template",
    "Final State Decision Table",
]


def assert_contains(text, term, label):
    if term not in text:
        raise AssertionError(f"{label} missing required term: {term}")


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT

    skill_md = (root / "SKILL.md").read_text(encoding="utf-8")
    assert_contains(skill_md, "phase1-boundary-contract.md", "SKILL.md")
    assert_contains(skill_md, "single-file behavior change", "SKILL.md")

    boundary_ref = root / "references" / "phase1-boundary-contract.md"
    if not boundary_ref.exists():
        raise AssertionError("missing references/phase1-boundary-contract.md")
    boundary_text = boundary_ref.read_text(encoding="utf-8")
    for term in REQUIRED_REFERENCE_TERMS:
        assert_contains(boundary_text, term, "phase1-boundary-contract.md")

    behavior_fixture = root / "assets" / "fixtures" / "router-single-file-behavior-change.json"
    if not behavior_fixture.exists():
        raise AssertionError("missing assets/fixtures/router-single-file-behavior-change.json")
    data = json.loads(behavior_fixture.read_text(encoding="utf-8"))
    if data.get("expectedRoute") != "local-global-skill-edit-loop":
        raise AssertionError("single-file behavior change fixture must route to local-global-skill-edit-loop")
    if data.get("manualApprovalRequired") is not True:
        raise AssertionError("single-file behavior change fixture must require manual approval")
    markers = " ".join(data.get("requiredObservableMarkers", []))
    for term in ["workspace-copy-first", "single-file behavior change", "global deployment approval"]:
        assert_contains(markers, term, "single-file behavior change fixture markers")

    validator_text = (root / "scripts" / "validate_development_system.py").read_text(encoding="utf-8")
    for term in [
        "references/phase1-boundary-contract.md",
        "assets/fixtures/router-single-file-behavior-change.json",
        "single-file behavior change",
        "Mandatory Workspace-Copy-First Triggers",
    ]:
        assert_contains(validator_text, term, "validate_development_system.py")

    print("PHASE1_BOUNDARY_CONTRACT_OK")


if __name__ == "__main__":
    raise SystemExit(main())
