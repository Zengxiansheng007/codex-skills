#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_research_decision_gate.py"


def run_fixture(name):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(ROOT / "assets" / "fixtures" / name)],
        capture_output=True,
        text=True,
    )


def main():
    valid = run_fixture("valid-decision-gate-report.html")
    if valid.returncode != 0:
        raise AssertionError(f"valid fixture failed:\n{valid.stdout}\n{valid.stderr}")

    invalid = run_fixture("invalid-decision-gate-accepted-open-p0.html")
    if invalid.returncode == 0:
        raise AssertionError("invalid fixture unexpectedly passed")

    print("ok: decision gate validator fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
