"""Deterministic PH-4 contract tests."""

import json
from pathlib import Path

from phase4_governance import build_backup_manifest, build_operations_report, evaluate_install_gate, validate_compatibility


ROOT = Path(__file__).resolve().parent.parent


def load(name):
    return json.loads((ROOT / "assets" / "fixtures" / name).read_text(encoding="utf-8"))


def main():
    errors = []
    positive = load("phase-story/ph4-promotion-positive.json")
    compatibility = validate_compatibility(positive["compatibility"])
    backup = build_backup_manifest(positive["backup"])
    positive["request"]["backupManifestHash"] = backup["manifestHash"]
    gate = evaluate_install_gate(positive["request"], positive["approval"], compatibility, backup, positive["now"])
    if not compatibility["compatible"] or not backup["valid"] or not gate["allowed"] or not gate["dryRunOnly"]:
        errors.append("positive PH-4 dry-run readiness rejected")
    for fixture_name, reason in (
        ("negative/NEG-PH4-001-missing-approval.json", "explicit-install-approval-missing"),
        ("negative/NEG-PH4-002-source-hash-drift.json", "install-approval-boundary-mismatch"),
        ("negative/NEG-PH4-003-missing-rollback.json", "compatibility-or-backup-not-ready"),
        ("negative/NEG-PH4-004-expired-approval.json", "install-approval-inactive-or-expired"),
    ):
        fixture = load(fixture_name)
        c = validate_compatibility(fixture["compatibility"])
        b = build_backup_manifest(fixture["backup"])
        fixture["request"]["backupManifestHash"] = b["manifestHash"]
        result = evaluate_install_gate(fixture["request"], fixture.get("approval"), c, b, fixture["now"])
        if result["allowed"] or result["reason"] != reason:
            errors.append(f"{fixture_name} did not fail closed: {result}")
    operations = build_operations_report(load("phase-story/ph4-operations-positive.json"))
    if not operations["reconstructible"] or operations["state"] != "running":
        errors.append("operations report is not reconstructible")
    if errors:
        print("PH4_GOVERNANCE_FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("PH4_GOVERNANCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

