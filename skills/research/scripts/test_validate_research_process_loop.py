#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESS_VALIDATOR = ROOT / "scripts" / "validate_research_process_loop.py"
HTML_VALIDATOR = ROOT / "scripts" / "validate_research_html.py"
GATE_VALIDATOR = ROOT / "scripts" / "validate_research_decision_gate.py"


def run(script, name):
    return subprocess.run(
        [sys.executable, str(script), str(ROOT / "assets" / "fixtures" / name)],
        capture_output=True,
        text=True,
    )


def assert_pass(script, name):
    result = run(script, name)
    if result.returncode != 0:
        raise AssertionError(f"{script.name} should pass {name}:\n{result.stdout}\n{result.stderr}")


def assert_fail(script, name):
    result = run(script, name)
    if result.returncode == 0:
        raise AssertionError(f"{script.name} should fail {name}:\n{result.stdout}\n{result.stderr}")


def main():
    assert_pass(PROCESS_VALIDATOR, "valid-strict-loop-report.html")
    assert_pass(HTML_VALIDATOR, "valid-strict-loop-report.html")
    assert_pass(GATE_VALIDATOR, "valid-strict-loop-report.html")

    assert_fail(PROCESS_VALIDATOR, "invalid-strict-loop-missing-blocks.html")
    assert_fail(HTML_VALIDATOR, "invalid-strict-loop-missing-blocks.html")
    assert_fail(GATE_VALIDATOR, "invalid-strict-loop-missing-blocks.html")

    assert_fail(PROCESS_VALIDATOR, "invalid-strict-loop-fake-closure.html")
    assert_fail(HTML_VALIDATOR, "invalid-strict-loop-fake-closure.html")
    assert_fail(GATE_VALIDATOR, "invalid-strict-loop-fake-closure.html")

    assert_pass(PROCESS_VALIDATOR, "valid-decision-gate-report.html")
    print("ok: research process loop validator fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
