#!/usr/bin/env python3
"""Deterministic tests for validate_handoff.py."""

from __future__ import annotations

from pathlib import Path

from validate_handoff import validate_text


ROOT = Path(__file__).resolve().parents[1]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_valid_fixture() -> None:
    text = (ROOT / "assets" / "forward-tests" / "valid-handoff.md").read_text(encoding="utf-8")
    report = validate_text(text)
    assert_true(report["summary"]["P0"] == 0, "valid fixture should not have P0 findings")
    assert_true(report["summary"]["P1"] == 0, "valid fixture should not have P1 findings")


def test_missing_sections_fails() -> None:
    text = (ROOT / "assets" / "forward-tests" / "invalid-handoff-missing-section.md").read_text(encoding="utf-8")
    report = validate_text(text)
    assert_true(report["summary"]["P1"] > 0, "missing sections should produce P1 findings")


def test_secret_detection() -> None:
    secret = "sk-" + ("A" * 24)
    text = (ROOT / "assets" / "forward-tests" / "valid-handoff.md").read_text(encoding="utf-8")
    report = validate_text(text + "\n" + secret + "\n")
    assert_true(report["summary"]["P0"] > 0, "secret-like values should produce P0 findings")


def test_placeholder_warning() -> None:
    text = (ROOT / "assets" / "forward-tests" / "valid-handoff.md").read_text(encoding="utf-8")
    report = validate_text(text + "\n<task-name>\n")
    assert_true(report["summary"]["P2"] > 0, "template placeholders should produce P2 findings")


def main() -> int:
    tests = [
        test_valid_fixture,
        test_missing_sections_fails,
        test_secret_detection,
        test_placeholder_warning,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
