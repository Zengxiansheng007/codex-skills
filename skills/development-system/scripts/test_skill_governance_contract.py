import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def assert_contains(text, term, label):
    if term not in text:
        raise AssertionError(f"{label} missing required term: {term}")


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT

    skill_md = (root / "SKILL.md").read_text(encoding="utf-8")
    assert_contains(skill_md, "## Safety And Escalation", "SKILL.md")

    index = (root / "change-records" / "index.md").read_text(encoding="utf-8")
    assert_contains(index, "## Latest Changes", "change-records/index.md")

    phase1_record = (
        root
        / "change-records"
        / "entries"
        / "2026"
        / "2026-08"
        / "CR-20260809-002-phase1-boundary-contract.md"
    ).read_text(encoding="utf-8")
    assert_contains(phase1_record, "## Impact Analysis", "CR-20260809-002")

    validator = (root / "scripts" / "validate_development_system.py").read_text(encoding="utf-8")
    for term in [
        "## Safety And Escalation",
        "## Latest Changes",
        "## Impact Analysis",
    ]:
        assert_contains(validator, term, "validate_development_system.py")

    print("SKILL_GOVERNANCE_CONTRACT_OK")


if __name__ == "__main__":
    raise SystemExit(main())
