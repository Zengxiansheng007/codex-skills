#!/usr/bin/env python3
"""Deterministic tests for the research repair (AC-RR-001).

Tests positive and negative cases for:
- FR-RR-001: live research rejects permission mode plan
- FR-RR-002: one registry owns the four approved MCP tool names
- FR-RR-003: preflight verifies all conditions
- FR-RR-004: research output is pure UTF-8 JSON validated by schema and semantic gates
- FR-RR-005: format retries and content reinforcement are separate and bounded
- FR-RR-006: stable failure classes propagate
"""
from __future__ import annotations
import hashlib, json, sys, tempfile, os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

# Add scripts dir to path for imports
sys.path.insert(0, str(SCRIPT_DIR))

import preflight_research
import validate_research_result
import live_mode_guard
import check_tool_drift

REGISTRY_TOOLS = [
    "mcp__exa__web_search_exa",
    "mcp__exa__web_fetch_exa",
    "mcp__firecrawl__firecrawl_search",
    "mcp__firecrawl__firecrawl_scrape",
]

SCHEMA_HASH = hashlib.sha256((SKILL_ROOT / "schemas" / "research-result.schema.json").read_bytes()).hexdigest()


def add_strict_fields(data, mode="provider-native"):
    """Fill the strict fields required by the research-result schema.

    ``mode`` selects the explicit compatibility profile (FR-ADP-001):
    ``provider-native`` (default) keeps the existing native regression fixtures
    green; ``adapter-validated`` adds the ledger reference and adapter
    validation evidence required for the two-stage adapter path.
    """
    base = {
        "researchId": "R-TEST-001",
        "requirementAnchor": "ANCHOR-TEST",
        "roundId": "ROUND-1",
        "skillsUsed": ["research-executor"],
        "scope": {"topic": "test"},
        "queries": [{"query": "test"}],
        "claimSourceMap": {"claim-1": ["https://example.com/1"]},
        "coverageMatrix": [{"requirement": "FR-TEST", "covered": True}],
        "contradictions": [],
        "p0p1Gaps": [],
        "followupQueryMatrix": [],
        "limitations": [],
        "selfValidation": {"schemaValid": True},
        "completionClaim": "complete",
        "schemaVersion": "2020-12",
        "schemaSha256": SCHEMA_HASH,
        "schemaEnforcementMode": mode,
        "providerNativeSchema": mode == "provider-native",
    }
    base.update(data)
    if mode == "adapter-validated":
        base.setdefault("evidenceLedgerRef", {
            "ledgerId": "LEDGER-TEST-001",
            "ledgerSha256": "0" * 64,
        })
        base.setdefault("adapterValidation", {
            "localSchemaValid": True,
            "semanticGatesPassed": True,
            "formatAttempts": 1,
            "evidenceHashStable": True,
            "reinforcementRounds": 0,
        })
    return base


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected}, got {actual}")


def assert_true(value, msg=""):
    if not value:
        raise AssertionError(f"{msg}: expected True, got {value}")


def assert_false(value, msg=""):
    if value:
        raise AssertionError(f"{msg}: expected False, got {value}")


def test_registry_load():
    """FR-RR-002: One registry owns the four approved MCP tool names."""
    names = preflight_research.get_registry_tool_names()
    assert_eq(len(names), 4, "registry should have exactly 4 tools")
    for tool in REGISTRY_TOOLS:
        assert_true(tool in names, f"registry should contain {tool}")
    print("  PASS: registry has exactly 4 approved tools")


def test_preflight_plan_mode_blocked():
    """FR-RR-001: Live research rejects permission mode plan."""
    result = preflight_research.run_full_preflight(
        permission_mode="plan",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "plan mode should fail preflight")
    mode_check = [r for r in result["results"] if r["check"] == "permission_mode"]
    assert_true(len(mode_check) > 0, "should have permission_mode check")
    assert_false(mode_check[0]["passed"], "plan mode should be blocked")
    print("  PASS: plan mode is blocked by preflight")


def test_preflight_unregistered_tool():
    """FR-RR-003: Preflight detects unregistered tool."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS + ["mcp__" + "evil__hack"],
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "unregistered tool should fail")
    registry_check = [r for r in result["results"] if r["check"] == "exact_registry_match"]
    assert_true(len(registry_check) > 0, "should have exact_registry_match check")
    assert_false(registry_check[0]["passed"], "unregistered tool should fail")
    print("  PASS: unregistered tool detected by preflight")


def test_preflight_missing_canary():
    """FR-RR-003: Preflight detects missing canary."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary=None,
        skip_cli=True,
    )
    assert_false(result["allPassed"], "missing canary should fail")
    canary_check = [r for r in result["results"] if r["check"] == "canary_evidence"]
    assert_false(canary_check[0]["passed"], "missing canary should fail")
    print("  PASS: missing canary detected by preflight")


def test_preflight_failed_canary():
    """FR-RR-003: Preflight detects failed canary."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": False, "canaryDetail": "canary failed"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "failed canary should fail")
    print("  PASS: failed canary detected by preflight")


def test_preflight_permission_denials():
    """FR-RR-003: Preflight detects nonzero permission denials."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        permission_denials=2,
        skip_cli=True,
    )
    assert_false(result["allPassed"], "nonzero denials should fail")
    print("  PASS: permission denials detected by preflight")


def test_preflight_stale_session():
    """FR-RR-003: Preflight detects stale session."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id=None,
        session_started_at=None,
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "stale session should fail")
    print("  PASS: stale session detected by preflight")


def test_preflight_tool_count_zero():
    """FR-RR-003: Preflight detects zero tool count."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=[],
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "zero tool count should fail")
    print("  PASS: zero tool count detected by preflight")


def test_preflight_mcp_schema_absent():
    """FR-RR-003: Preflight detects absent MCP schema."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=["some_other_tool"],
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        skip_cli=True,
    )
    assert_false(result["allPassed"], "absent MCP schema should fail")
    print("  PASS: MCP schema absent detected by preflight")


def test_preflight_all_pass():
    """FR-RR-003: Preflight passes with all conditions met."""
    result = preflight_research.run_full_preflight(
        permission_mode="default",
        session_id="test-session-001",
        session_started_at="2026-08-25T10:00:00Z",
        visible_tools=REGISTRY_TOOLS,
        requested_tools=REGISTRY_TOOLS,
        canary={"canaryPassed": True, "canaryDetail": "ok"},
        permission_denials=0,
        skip_cli=True,
    )
    assert_true(result["allPassed"], f"all checks should pass, failures: {result['failures']}")
    print("  PASS: preflight passes with all conditions met")


def test_live_mode_guard_plan_blocked():
    """FR-RR-001: Live mode guard rejects plan."""
    result = live_mode_guard.check_live_mode("plan")
    assert_false(result.allowed, "plan should be blocked")
    assert_eq(result.reason, "plan-mode-blocked", "should report plan-mode-blocked")
    print("  PASS: live mode guard blocks plan")


def test_live_mode_guard_ok():
    """FR-RR-001: Live mode guard allows valid mode."""
    result = live_mode_guard.check_live_mode("default")
    assert_true(result.allowed, "default should be allowed")
    print("  PASS: live mode guard allows default")


def test_format_retries_bounded():
    """FR-RR-005: Format retries are bounded at 3."""
    ok = live_mode_guard.check_format_retries(3)
    assert_true(ok.allowed, "3 retries should be allowed")
    over = live_mode_guard.check_format_retries(4)
    assert_false(over.allowed, "4 retries should be blocked")
    print("  PASS: format retries bounded at 3")


def test_reinforcement_bounded():
    """FR-RR-005: Reinforcement rounds are bounded at 1."""
    ok = live_mode_guard.check_reinforcement_rounds(1)
    assert_true(ok.allowed, "1 round should be allowed")
    over = live_mode_guard.check_reinforcement_rounds(2)
    assert_false(over.allowed, "2 rounds should be blocked")
    print("  PASS: reinforcement rounds bounded at 1")


def test_tool_scope():
    """FR-RR-002: Tool scope check."""
    ok = live_mode_guard.check_tool_scope(REGISTRY_TOOLS)
    assert_true(ok.allowed, "registry tools should pass")
    bad = live_mode_guard.check_tool_scope(REGISTRY_TOOLS + ["mcp__" + "evil__hack"])
    assert_false(bad.allowed, "unregistered tool should fail")
    print("  PASS: tool scope check works")


def test_validate_valid_result():
    """FR-RR-004: Valid research result passes validation."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [
            {"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True, "toolUsed": "mcp__exa__web_search_exa"}
        ],
        "claims": [
            {"text": "A claim", "sourceUrl": "https://example.com/1", "sourceTitle": "Example"}
        ],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "accepted", f"valid result should pass: {result}")
    assert_eq(result["summary"]["P0"], 0, "no P0 findings")
    print("  PASS: valid research result passes validation")


def test_validate_plan_mode():
    """FR-RR-004: Plan mode in result is rejected."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "plan",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "rejected", "plan mode should be rejected")
    assert_true(result["summary"]["P0"] > 0, "should have P0 findings")
    print("  PASS: plan mode in result is rejected")


def test_validate_not_json():
    """FR-RR-004: Non-JSON output is rejected."""
    result = validate_research_result.validate("This is not JSON.")
    assert_eq(result["status"], "rejected", "non-JSON should be rejected")
    assert_false(result["isJson"], "should report not JSON")
    print("  PASS: non-JSON output rejected")


def test_validate_bom_detected():
    """FR-RR-004: BOM-prefixed JSON is rejected."""
    result_data = {"resultType": "research-result", "mode": "live", "sessionFresh": True, "permissionMode": "default", "toolRegistryMatch": True, "toolCount": 4, "mcpSchemaVisible": True, "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"}, "permissionDenials": 0, "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}], "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}], "gaps": [], "evidenceComplete": True, "formatRetries": 0, "reinforcementRounds": 0, "failureClass": None}
    raw = "﻿" + json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "rejected", "BOM should be rejected")
    print("  PASS: BOM-prefixed JSON rejected")


def test_validate_unverified_complete():
    """FR-RR-004: Unverified sources claimed complete is rejected."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": False}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "rejected", "unverified complete should be rejected")
    print("  PASS: unverified sources claimed complete rejected")


def test_validate_open_p0p1_complete():
    """Completion is rejected while P0/P1 coverage gaps remain open."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 1,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "p0p1Gaps": [{"severity": "P1", "description": "Coverage remains open."}],
        "gaps": [{"severity": "P1", "description": "Coverage remains open."}],
        "evidenceComplete": True,
        "completionClaim": "complete",
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "rejected", "open P0/P1 gaps must block complete")
    assert_true(any(f["rule"] == "completion-with-open-p0p1-gaps" for f in result["findings"]), "gap completion finding missing")
    print("  PASS: open P0/P1 gaps block completion")


def test_validate_invalid_source_mapping():
    """FR-RR-004: Invalid source mappings are rejected."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/nonexistent"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_eq(result["status"], "rejected", "invalid source mapping should be rejected")
    print("  PASS: invalid source mappings rejected")


def test_validate_format_retries_exceeded():
    """FR-RR-005: Format retries exceeding limit is flagged."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 5,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_true(result["summary"]["P1"] > 0, "exceeded format retries should be P1")
    print("  PASS: format retries exceeding limit flagged")


def test_validate_reinforcement_exceeded():
    """FR-RR-005: Reinforcement rounds exceeding limit is flagged."""
    result_data = {
        "resultType": "research-result",
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": "ok"},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 3,
        "failureClass": None,
    }
    raw = json.dumps(add_strict_fields(result_data), ensure_ascii=False)
    result = validate_research_result.validate(raw)
    assert_true(result["summary"]["P1"] > 0, "exceeded reinforcement should be P1")
    print("  PASS: reinforcement rounds exceeding limit flagged")


def test_tool_drift_check():
    """FR-RR-002: Tool drift detection."""
    findings = check_tool_drift.check_all()
    p0 = sum(1 for f in findings if f.severity == "P0")
    assert_eq(p0, 0, f"no P0 drift findings expected, got: {findings}")
    print("  PASS: no P0 tool drift detected")


def test_failure_classification():
    """FR-RR-006 / FR-ADP-008: stable failure classes exist (including adapter set)."""
    fc_path = SKILL_ROOT / "schemas" / "failure-classification.json"
    fc = json.loads(fc_path.read_text(encoding="utf-8"))
    classes = fc.get("classes", [])
    expected = {
        "plan-mode-blocked", "unregistered-tool-requested", "mcp-schema-absent",
        "tool-count-zero", "stale-session", "canary-missing", "canary-failed",
        "permission-denials-nonzero", "output-not-json", "source-mappings-invalid",
        "unverified-sources-claimed-complete", "format-retry-limit-exceeded",
        "reinforcement-limit-exceeded", "claude-unavailable", "timeout",
        "internal-error",
        # FR-ADP-001/002/003/004/006/008 adapter-validated failure classes.
        "structured-output-empty", "silent-native-downgrade",
        "evidence-ledger-missing", "evidence-hash-unstable",
        "unsupported-fact-introduced", "serialization-tool-access",
        "adapter-validation-failed", "format-attempt-exhaustion",
    }
    actual = {c["name"] for c in classes}
    missing = expected - actual
    assert_eq(len(missing), 0, f"missing failure classes: {missing}")
    print("  PASS: all expected failure classes exist (native + adapter)")


def main() -> int:
    tests = [
        ("Registry", test_registry_load),
        ("Preflight plan blocked", test_preflight_plan_mode_blocked),
        ("Preflight unregistered tool", test_preflight_unregistered_tool),
        ("Preflight missing canary", test_preflight_missing_canary),
        ("Preflight failed canary", test_preflight_failed_canary),
        ("Preflight permission denials", test_preflight_permission_denials),
        ("Preflight stale session", test_preflight_stale_session),
        ("Preflight tool count zero", test_preflight_tool_count_zero),
        ("Preflight MCP schema absent", test_preflight_mcp_schema_absent),
        ("Preflight all pass", test_preflight_all_pass),
        ("Live guard plan blocked", test_live_mode_guard_plan_blocked),
        ("Live guard ok", test_live_mode_guard_ok),
        ("Format retries bounded", test_format_retries_bounded),
        ("Reinforcement bounded", test_reinforcement_bounded),
        ("Tool scope", test_tool_scope),
        ("Validate valid result", test_validate_valid_result),
        ("Validate plan mode", test_validate_plan_mode),
        ("Validate not JSON", test_validate_not_json),
        ("Validate BOM detected", test_validate_bom_detected),
        ("Validate unverified complete", test_validate_unverified_complete),
        ("Validate open P0/P1 complete", test_validate_open_p0p1_complete),
        ("Validate invalid source mapping", test_validate_invalid_source_mapping),
        ("Validate format retries exceeded", test_validate_format_retries_exceeded),
        ("Validate reinforcement exceeded", test_validate_reinforcement_exceeded),
        ("Tool drift check", test_tool_drift_check),
        ("Failure classification", test_failure_classification),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL: {name}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ERROR: {name}: {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
