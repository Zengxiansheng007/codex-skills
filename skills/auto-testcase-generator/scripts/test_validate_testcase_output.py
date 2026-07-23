#!/usr/bin/env python3
"""Self-tests for validate_testcase_output.py using bundled fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_testcase_output.py"
FIXTURES = ROOT / "assets" / "fixtures"


def run_case(markdown: str, trace: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--markdown",
            str(FIXTURES / markdown),
            "--trace",
            str(FIXTURES / trace),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    valid = run_case("valid-testcases.md", "valid-trace.json")
    if valid.returncode != 0:
        print(valid.stdout)
        print(valid.stderr)
        return 1

    invalid = run_case("invalid-testcases.md", "invalid-trace.json")
    if invalid.returncode == 0:
        print("invalid fixture unexpectedly passed")
        print(invalid.stdout)
        return 1

    print("self-test: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
