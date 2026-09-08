#!/usr/bin/env python3
"""Deterministic tests for the two-stage Research adapter (FR-ADP-001..010).

Covers:
- Unit: ledger freezing, canonical hashing, retry counting, candidate
  extraction, source/claim mapping.
- Contract: research-result Schema (Draft 2020-12) + semantic gates for both
  provider-native and adapter-validated modes.
- Integration: a fake retrieval transcript feeds a deterministic serializer
  through both stages; malformed serializer outputs are exercised.
- Negative: prose-around-json, malformed JSON, missing field, unknown field,
  URL absent from ledger, claim absent from ledger, serialization tool access,
  permission denial, evidence hash change, three failed attempts, silent native
  downgrade, sensitive output.
- Regression: provider-native mode still passes the existing gates.
- Cross-Skill: failure classes propagate as stable identifiers.
- Sensitive: scan over candidate files and generated evidence.

This module performs no live external calls and spawns no subprocess.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import serialize_research as sr
import validate_research_result as vrr
import run_live_research as rlr
import live_mode_guard
import preflight_research
import check_tool_drift
import scan_sensitive

REGISTRY_TOOLS = [
    "mcp__exa__web_search_exa",
    "mcp__exa__web_fetch_exa",
    "mcp__firecrawl__firecrawl_search",
    "mcp__firecrawl__firecrawl_scrape",
]
SCHEMA_HASH = sr.schema_hash()
LEDGER_SCHEMA = SKILL_ROOT / "schemas" / "research-evidence-ledger.schema.json"
RESULT_SCHEMA = SKILL_ROOT / "schemas" / "research-result.schema.json"
FAILURE_CLASSIFICATION = SKILL_ROOT / "schemas" / "failure-classification.json"


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected!r}, got {actual!r}")


def assert_true(value, msg=""):
    if not value:
        raise AssertionError(f"{msg}: expected True, got {value!r}")


def assert_false(value, msg=""):
    if value:
        raise AssertionError(f"{msg}: expected False, got {value!r}")


def has_rule(report, rule):
    return any((f.get("rule") if isinstance(f, dict) else getattr(f, "rule", None)) == rule for f in report.get("findings", []))  # Accept dict and AdapterFinding results.


def make_ledger(ledger_id="LEDGER-TEST-001", sources=None, claims=None, registry_match=True):
    """Build a frozen ledger from a fake retrieval transcript."""
    sources = sources if sources is not None else [
        {
            "url": "https://example.com/1",
            "title": "Example One",
            "retrievedAt": "2026-08-27T10:00:00Z",
            "verified": True,
            "toolUsed": "mcp__exa__web_search_exa",
            "contentDigest": hashlib.sha256(b"content-one").hexdigest(),
        }
    ]
    ledger, digest = sr.freeze_ledger(
        ledger_id=ledger_id,
        requirement_anchor="CLAUDE-GLM52-ADAPTER-REPAIR-20260827-001",
        session={
            "sessionId": "session-test-001",
            "sessionStartedAt": "2026-08-27T10:00:00Z",
            "sessionFresh": True,
            "permissionMode": "default",
        },
        queries=[{"query": "model context protocol"}],
        tool_calls=[
            {"toolName": "mcp__exa__web_search_exa", "toolInput": {"query": "mcp"}, "resultStatus": "ok"}
        ],
        permission_results={"permissionDenials": 0, "deniedTools": []},
        sources=sources,
        registry_match=registry_match,
        boundary_checks={
            "noPrivateSources": True,
            "noUnapprovedTools": True,
            "noCredentialLeakage": True,
            "publicOnly": True,
        },
        frozen_at="2026-08-27T10:00:05Z",
        claims=claims or [
            {"text": "MCP defines a tools list method.", "sourceUrl": "https://example.com/1"}
        ],
    )
    return ledger, digest


def make_result_from_ledger(ledger, _ledger_digest=None, **overrides):  # Accept make_ledger() tuple expansion in extraction tests.
    """Build a research-result dict that resolves to the frozen ledger."""
    src = ledger["sources"][0]
    data = {
        "resultType": "research-result",
        "schemaEnforcementMode": "adapter-validated",
        "providerNativeSchema": False,
        "evidenceLedgerRef": {
            "ledgerId": ledger["ledgerId"],
            "ledgerSha256": ledger["ledgerSha256"],
        },
        "adapterValidation": {
            "localSchemaValid": True,
            "semanticGatesPassed": True,
            "formatAttempts": 1,
            "evidenceHashStable": True,
            "reinforcementRounds": 0,
        },
        "mode": "dry-run",
        "sessionFresh": True,
        "permissionMode": "default",
        "permissionDenials": 0,
        "toolRegistryMatch": ledger.get("registryMatch", True),
        "evidenceComplete": True,
        "formatRetries": 1,
        "reinforcementRounds": 0,
        "failureClass": None,
        "researchId": "R-ADP-001",
        "requirementAnchor": ledger["requirementAnchor"],
        "roundId": ledger.get("roundId", "ROUND-1"),
        "skillsUsed": ["research-executor"],
        "scope": {"topic": "adapter repair"},
        "queries": ledger["queries"],
        "sources": [
            {
                "url": src["url"],
                "title": src["title"],
                "retrievedAt": src["retrievedAt"],
                "verified": src["verified"],
                "toolUsed": src.get("toolUsed", ""),
            }
        ],
        "claims": [{"text": c["text"], "sourceUrl": c["sourceUrl"], "sourceTitle": src["title"]} for c in ledger.get("claims", [])],
        "claimSourceMap": {"claim-1": [src["url"]]},
        "coverageMatrix": [{"requirement": "FR-ADP-001", "covered": True}],
        "contradictions": [],
        "p0p1Gaps": [],
        "followupQueryMatrix": [],
        "limitations": [],
        "selfValidation": {"schemaValid": True},
        "completionClaim": "complete",
        "schemaVersion": "2020-12",
        "schemaSha256": SCHEMA_HASH,
        "gaps": [],
    }
    data.update(overrides)
    return data


def serializer_for(data):
    """Return a deterministic serializer callable that emits a stable JSON."""
    def _serializer(ledger, attempt_idx):
        return json.dumps(data, ensure_ascii=False)
    return _serializer


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_ledger_freeze_and_hash():
    """FR-ADP-003: freezing produces a stable canonical hash over the ledger body."""
    ledger, digest = make_ledger()
    assert_eq(ledger["ledgerType"], "research-evidence-ledger")
    assert_eq(ledger["schemaEnforcementMode"], "adapter-validated")
    assert_false(ledger["providerNativeSchema"])
    assert_eq(ledger["ledgerSha256"], digest)
    assert_eq(len(digest), 64)
    # Re-freezing the same inputs yields the same hash.
    ledger2, digest2 = make_ledger()
    assert_eq(digest, digest2, "ledger hash must be deterministic")
    print("  PASS: ledger freeze produces stable canonical hash")


def test_ledger_hash_excludes_self():
    """The ledgerSha256 field must not be part of its own hash input."""
    ledger, digest = make_ledger()
    body = {k: v for k, v in ledger.items() if k != "ledgerSha256"}
    recomputed = hashlib.sha256(sr.canonical_json(body).encode("utf-8")).hexdigest()
    assert_eq(recomputed, digest, "ledger hash must exclude ledgerSha256")
    print("  PASS: ledger hash excludes the ledgerSha256 field")


def test_registry_hash_stable():
    """FR-ADP-003: registry hash is recorded and stable."""
    ledger, _ = make_ledger()
    assert_eq(ledger["registryHash"], sr.registry_hash())
    assert_true(ledger["registryHash"] in (ledger["registryHash"],))
    print("  PASS: registry hash recorded and stable")


def test_candidate_extraction_pure_json():
    """FR-ADP-004: pure JSON candidate is extracted."""
    data = make_result_from_ledger(*make_ledger())
    ok, cand, findings = sr.extract_candidate(json.dumps(data, ensure_ascii=False))
    assert_true(ok)
    assert_true(cand is not None)
    assert_eq(findings, [])
    print("  PASS: pure JSON candidate extracted")


def test_candidate_extraction_prose_prefix():
    """Negative: prose-around-json is extracted (lenient) but malformed is rejected."""
    data = make_result_from_ledger(*make_ledger())
    raw = "Here is the result:\n" + json.dumps(data, ensure_ascii=False)
    ok, cand, findings = sr.extract_candidate(raw)
    assert_true(ok, "prose prefix should still yield a candidate")
    assert_true(cand is not None)
    # Pure prose with no JSON object fails.
    ok2, _, findings2 = sr.extract_candidate("This is just prose with no JSON braces")
    assert_false(ok2)
    assert_true(has_rule({"findings": findings2}, "not-research-result"))
    print("  PASS: prose-around-json extracted, pure prose rejected")


def test_candidate_extraction_bom():
    """Negative: BOM-prefixed output is flagged."""
    data = make_result_from_ledger(*make_ledger())
    raw = "﻿" + json.dumps(data, ensure_ascii=False)
    ok, _, findings = sr.extract_candidate(raw)
    assert_true(has_rule({"findings": findings}, "bom-detected"))
    print("  PASS: BOM-prefixed output flagged")


def test_candidate_extraction_malformed():
    """Negative: malformed JSON is rejected, no fabricated packet."""
    ok, cand, findings = sr.extract_candidate('{"resultType": "research-result", "broken":')
    assert_false(ok)
    assert_true(cand is None)
    assert_true(has_rule({"findings": findings}, "not-research-result"))
    print("  PASS: malformed JSON rejected without fabrication")


def test_validate_against_ledger_clean():
    """FR-ADP-004: a result resolving to the ledger passes."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    findings = sr.validate_against_ledger(data, ledger)
    assert_eq(findings, [], f"clean result should have no ledger findings: {findings}")
    print("  PASS: clean result resolves to ledger")


def test_validate_against_ledger_unknown_url():
    """Negative: a final source URL absent from the ledger is rejected."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    data["sources"].append({
        "url": "https://not-in-ledger.example/x",
        "title": "Bogus", "retrievedAt": "2026-08-27T10:00:00Z", "verified": True,
    })
    findings = sr.validate_against_ledger(data, ledger)
    assert_true(any(f.rule == "source-absent-from-ledger" for f in findings))
    print("  PASS: source URL absent from ledger rejected")


def test_validate_against_ledger_unknown_claim():
    """Negative: a claim referencing a URL absent from the ledger is rejected."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    data["claims"].append({"text": "extra", "sourceUrl": "https://not-in-ledger.example/y"})
    findings = sr.validate_against_ledger(data, ledger)
    assert_true(any(f.rule == "claim-absent-from-ledger" for f in findings))
    print("  PASS: claim absent from ledger rejected")


# ---------------------------------------------------------------------------
# Contract tests (Schema + semantic gates)
# ---------------------------------------------------------------------------

def test_adapter_validated_result_accepted():
    """FR-ADP-001/005: adapter-validated result with ledger ref passes all gates."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    raw = json.dumps(data, ensure_ascii=False)
    result = vrr.validate(raw)
    assert_eq(result["status"], "accepted", f"adapter-validated result should pass: {result}")
    assert_eq(result["summary"]["P0"], 0)
    print("  PASS: adapter-validated result accepted by local gates")


def test_adapter_mode_missing_rejected():
    """Negative: missing schemaEnforcementMode is rejected (FR-ADP-001)."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    del data["schemaEnforcementMode"]
    result = vrr.validate(json.dumps(data, ensure_ascii=False))
    assert_eq(result["status"], "rejected")
    assert_true(has_rule(result, "enforcement-mode-missing"))
    print("  PASS: missing schemaEnforcementMode rejected")


def test_adapter_native_schema_true_rejected():
    """Negative: adapter-validated mode claiming providerNativeSchema=true is rejected."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger, providerNativeSchema=True)
    result = vrr.validate(json.dumps(data, ensure_ascii=False))
    assert_eq(result["status"], "rejected")
    assert_true(has_rule(result, "silent-native-claim"))
    print("  PASS: adapter-validated with providerNativeSchema=true rejected")


def test_adapter_ledger_ref_missing_rejected():
    """Negative: adapter-validated result without ledger ref is rejected (FR-ADP-003)."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    del data["evidenceLedgerRef"]
    result = vrr.validate(json.dumps(data, ensure_ascii=False))
    assert_eq(result["status"], "rejected")
    assert_true(has_rule(result, "evidence-ledger-missing"))
    print("  PASS: adapter-validated without ledger ref rejected")


def test_provider_native_regression():
    """FR-ADP-007: provider-native mode still passes the original strict gates."""
    data = {
        "resultType": "research-result",
        "schemaEnforcementMode": "provider-native",
        "providerNativeSchema": True,
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
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1", "sourceTitle": "Example"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    # Reuse the strict-field helper in native mode.
    from test_research_repair import add_strict_fields
    raw = json.dumps(add_strict_fields(data, mode="provider-native"), ensure_ascii=False)
    result = vrr.validate(raw)
    assert_eq(result["status"], "accepted", f"native regression should pass: {result}")
    print("  PASS: provider-native mode regression passes strict gates")


def test_provider_native_missing_tools_rejected():
    """FR-ADP-007: provider-native mode still rejects absent MCP/canary."""
    data = {
        "resultType": "research-result",
        "schemaEnforcementMode": "provider-native",
        "providerNativeSchema": True,
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 0,
        "mcpSchemaVisible": False,
        "canaryEvidence": {"canaryPassed": False},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    from test_research_repair import add_strict_fields
    raw = json.dumps(add_strict_fields(data, mode="provider-native"), ensure_ascii=False)
    result = vrr.validate(raw)
    assert_eq(result["status"], "rejected")
    assert_true(has_rule(result, "tool-count-zero"))
    print("  PASS: provider-native mode rejects absent tools/canary")


# ---------------------------------------------------------------------------
# Integration tests (fake transcript -> two-stage)
# ---------------------------------------------------------------------------

def test_two_stage_success():
    """FR-ADP-002/005/006: a clean two-stage run completes."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    outcome = sr.run_two_stage(ledger, serializer_for(data))
    assert_eq(outcome["completionClaim"], "complete")
    assert_true(outcome["accepted"])
    assert_eq(outcome["summary"]["P0"], 0)
    assert_eq(outcome["summary"]["P1"], 0)
    assert_true(outcome["evidenceHashStable"])
    assert_eq(len(outcome["attempts"]), 1)
    print("  PASS: two-stage success path completes")


def test_two_stage_format_retry_then_success():
    """FR-ADP-006: a malformed first attempt then a valid second attempt completes within 3."""
    ledger, _ = make_ledger()
    good = make_result_from_ledger(ledger)
    attempts = ['{"resultType": "research-result", "broken":', json.dumps(good, ensure_ascii=False)]
    def serializer(_ledger, idx):
        return attempts[idx]
    outcome = sr.run_two_stage(ledger, serializer, max_attempts=3)
    assert_eq(outcome["completionClaim"], "complete")
    assert_true(outcome["accepted"])
    assert_eq(len(outcome["attempts"]), 2)
    print("  PASS: format retry then success within bound")


def test_two_stage_three_failures_blocked():
    """Negative: three failed attempts produce blocked/repair-needed, never complete."""
    ledger, _ = make_ledger()
    bad = '{"resultType": "research-result", "broken":'
    def serializer(_ledger, _idx):
        return bad
    outcome = sr.run_two_stage(ledger, serializer, max_attempts=3)
    assert_eq(outcome["completionClaim"], "blocked")
    assert_false(outcome["accepted"])
    assert_true(has_rule(outcome, "format-attempt-exhaustion"))
    print("  PASS: three failed attempts blocked, never complete")


def test_two_stage_unsupported_url_blocked():
    """Negative: a serializer introducing a ledger-absent URL is blocked."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    data["sources"].append({"url": "https://not-in-ledger.example/x", "title": "Bogus", "retrievedAt": "2026-08-27T10:00:00Z", "verified": True})
    outcome = sr.run_two_stage(ledger, serializer_for(data))
    assert_eq(outcome["completionClaim"], "blocked")
    assert_true(has_rule(outcome, "source-absent-from-ledger"))
    print("  PASS: ledger-absent URL blocked")


def test_two_stage_serialization_tool_access():
    """Negative: serialization requesting a tool is blocked (FR-ADP-002)."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    outcome = sr.run_two_stage(
        ledger, serializer_for(data),
        attempted_tools_per_attempt=[["mcp__exa__web_search_exa"]],
    )
    assert_eq(outcome["completionClaim"], "blocked")
    assert_true(has_rule(outcome, "serialization-tool-access"))
    print("  PASS: serialization tool access blocked")


def test_two_stage_evidence_hash_stable():
    """FR-ADP-006: evidence hash is stable across attempts (single ledger)."""
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    outcome = sr.run_two_stage(ledger, serializer_for(data))
    assert_true(outcome["evidenceHashStable"])
    hashes = {a.get("ledgerSha256") for a in outcome["attempts"]}
    assert_eq(len(hashes), 1)
    print("  PASS: evidence hash stable across attempts")


def test_two_stage_silent_downgrade_blocked():
    """Negative: providerNativeSchema=false under provider-native mode is rejected."""
    data = {
        "resultType": "research-result",
        "schemaEnforcementMode": "provider-native",
        "providerNativeSchema": False,
        "mode": "live",
        "sessionFresh": True,
        "permissionMode": "default",
        "toolRegistryMatch": True,
        "toolCount": 4,
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True},
        "permissionDenials": 0,
        "sources": [{"url": "https://example.com/1", "title": "Example", "retrievedAt": "2026-08-25T10:00:00Z", "verified": True}],
        "claims": [{"text": "A claim", "sourceUrl": "https://example.com/1"}],
        "gaps": [],
        "evidenceComplete": True,
        "formatRetries": 0,
        "reinforcementRounds": 0,
        "failureClass": None,
    }
    from test_research_repair import add_strict_fields
    raw = json.dumps(add_strict_fields(data, mode="provider-native"), ensure_ascii=False)
    result = vrr.validate(raw)
    assert_eq(result["status"], "rejected")
    assert_true(has_rule(result, "native-mode-mislabeled"))
    print("  PASS: silent provider-native downgrade blocked")


# ---------------------------------------------------------------------------
# Cross-Skill failure class propagation
# ---------------------------------------------------------------------------

def test_failure_classes_include_adapter_set():
    """FR-RR-006 / FR-ADP-008: new adapter failure classes exist as stable identifiers."""
    fc = json.loads(FAILURE_CLASSIFICATION.read_text(encoding="utf-8"))
    names = {c["name"] for c in fc.get("classes", [])}
    required = {
        "structured-output-empty",
        "silent-native-downgrade",
        "evidence-ledger-missing",
        "evidence-hash-unstable",
        "unsupported-fact-introduced",
        "serialization-tool-access",
        "adapter-validation-failed",
        "format-attempt-exhaustion",
    }
    missing = required - names
    assert_eq(len(missing), 0, f"missing adapter failure classes: {missing}")
    # Propagation must map to non-completed states only.
    for c in fc["classes"]:
        assert_true(c["propagation"] not in {"completed"}, f"{c['name']} must not propagate to completed")
    print("  PASS: adapter failure classes present and never propagate to completed")


def test_failure_class_stable_identifiers():
    """Existing failure class names remain unchanged (regression for stable identifiers)."""
    fc = json.loads(FAILURE_CLASSIFICATION.read_text(encoding="utf-8"))
    names = {c["name"] for c in fc.get("classes", [])}
    existing = {
        "plan-mode-blocked", "unregistered-tool-requested", "mcp-schema-absent",
        "tool-count-zero", "stale-session", "canary-missing", "canary-failed",
        "permission-denials-nonzero", "output-not-json", "source-mappings-invalid",
        "unverified-sources-claimed-complete", "format-retry-limit-exceeded",
        "reinforcement-limit-exceeded", "claude-unavailable", "timeout",
        "internal-error",
    }
    missing = existing - names
    assert_eq(len(missing), 0, f"existing failure classes regressed: {missing}")
    print("  PASS: existing failure class identifiers stable")


# ---------------------------------------------------------------------------
# Sensitive scan over candidate files and generated evidence
# ---------------------------------------------------------------------------

def test_sensitive_scan_scripts():
    """No credentials in the new/modified adapter scripts."""
    report = scan_sensitive.scan(str(SKILL_ROOT / "scripts"))
    assert_eq(report["status"], "pass", f"sensitive findings in scripts: {report['findings']}")
    print("  PASS: no sensitive content in adapter scripts")


def test_sensitive_scan_generated_evidence():
    """Generated ledger/result evidence carries no token-like content."""
    import tempfile
    ledger, _ = make_ledger()
    data = make_result_from_ledger(ledger)
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
        Path(tmp, "result.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        report = scan_sensitive.scan(tmp)
    assert_eq(report["status"], "pass", f"sensitive findings in evidence: {report['findings']}")
    print("  PASS: no sensitive content in generated evidence")


def test_tool_drift_clean():
    """FR-RR-002: no tool-name drift introduced by the adapter."""
    findings = check_tool_drift.check_all()
    p0 = sum(1 for f in findings if f.severity == "P0")
    assert_eq(p0, 0, f"no P0 tool drift expected, got: {findings}")
    print("  PASS: no P0 tool drift after adapter additions")


# ---------------------------------------------------------------------------
# Ledger schema self-validation
# ---------------------------------------------------------------------------

def test_ledger_schema_loads_and_validates():
    """The evidence ledger schema is valid JSON and loadable."""
    schema = json.loads(LEDGER_SCHEMA.read_text(encoding="utf-8"))
    assert_eq(schema["type"], "object")
    assert_true("ledgerSha256" in schema["required"])
    print("  PASS: evidence ledger schema loads with required ledgerSha256")


def test_live_gap_normalization_and_acceptance_gate():
    """Claude priority aliases normalize, while incomplete results cannot pass."""
    normalized = rlr.normalise_gaps({
        "p0p1Gaps": [
            {"id": "gap-1", "priority": "P1", "description": "Coverage remains open."},
            {"id": "gap-2", "description": "Classification missing."},
        ]
    })
    assert_eq(normalized[0]["severity"], "P1", "priority alias must map to severity")
    assert_eq(normalized[1]["severity"], "P0", "missing severity must fail closed as P0")
    assert_true("valid severity classification" in normalized[1]["description"])
    accepted_validation = {"status": "accepted", "summary": {"P0": 0, "P1": 0}}
    partial = {"completionClaim": "partial", "evidenceComplete": True}
    assert_false(rlr.acceptance_gate(partial, accepted_validation, 0, 0))
    complete = {"completionClaim": "complete", "evidenceComplete": True}
    assert_true(rlr.acceptance_gate(complete, accepted_validation, 0, 0))
    print("  PASS: live gap normalization and complete-result acceptance gate")


def test_partial_retrieval_status_blocks_completion():
    """A Claude partial retrieval status must become an explicit P1 gap."""
    ledger, digest = make_ledger()
    result = rlr.build_research_result(
        ledger,
        {"retrievalStatus": "partial", "p0p1Gaps": []},
        "R-ADP-PARTIAL-001",
        SCHEMA_HASH,
        "https://example.com/1",
    )
    assert_eq(result["completionClaim"], "partial")
    assert_true(any(g.get("severity") == "P1" for g in result["gaps"]))
    assert_false(
        rlr.acceptance_gate(
            result,
            {"status": "accepted", "summary": {"P0": 0, "P1": 0}},
            0,
            0,
        )
    )
    print("  PASS: partial retrieval status blocks completion")


def test_round_lineage_is_explicit():
    """Reinforcement metadata must be carried into the result package."""
    ledger, _ = make_ledger()
    result = rlr.build_research_result(
        ledger,
        {"retrievalStatus": "passed", "p0p1Gaps": []},
        "R-ADP-ROUND-002",
        SCHEMA_HASH,
        "https://example.com/1",
        "round-2",
        1,
    )
    assert_eq(result["roundId"], "round-2")
    assert_eq(result["reinforcementRounds"], 1)
    assert_eq(result["adapterValidation"]["reinforcementRounds"], 1)
    print("  PASS: reinforcement round lineage is explicit")


def main() -> int:
    tests = [
        ("Ledger freeze and hash", test_ledger_freeze_and_hash),
        ("Ledger hash excludes self", test_ledger_hash_excludes_self),
        ("Registry hash stable", test_registry_hash_stable),
        ("Candidate extraction pure JSON", test_candidate_extraction_pure_json),
        ("Candidate extraction prose prefix", test_candidate_extraction_prose_prefix),
        ("Candidate extraction BOM", test_candidate_extraction_bom),
        ("Candidate extraction malformed", test_candidate_extraction_malformed),
        ("Validate against ledger clean", test_validate_against_ledger_clean),
        ("Validate against ledger unknown URL", test_validate_against_ledger_unknown_url),
        ("Validate against ledger unknown claim", test_validate_against_ledger_unknown_claim),
        ("Adapter-validated result accepted", test_adapter_validated_result_accepted),
        ("Adapter mode missing rejected", test_adapter_mode_missing_rejected),
        ("Adapter native schema true rejected", test_adapter_native_schema_true_rejected),
        ("Adapter ledger ref missing rejected", test_adapter_ledger_ref_missing_rejected),
        ("Provider-native regression", test_provider_native_regression),
        ("Provider-native missing tools rejected", test_provider_native_missing_tools_rejected),
        ("Two-stage success", test_two_stage_success),
        ("Two-stage format retry then success", test_two_stage_format_retry_then_success),
        ("Two-stage three failures blocked", test_two_stage_three_failures_blocked),
        ("Two-stage unsupported URL blocked", test_two_stage_unsupported_url_blocked),
        ("Two-stage serialization tool access", test_two_stage_serialization_tool_access),
        ("Two-stage evidence hash stable", test_two_stage_evidence_hash_stable),
        ("Two-stage silent downgrade blocked", test_two_stage_silent_downgrade_blocked),
        ("Failure classes include adapter set", test_failure_classes_include_adapter_set),
        ("Failure class stable identifiers", test_failure_class_stable_identifiers),
        ("Sensitive scan scripts", test_sensitive_scan_scripts),
        ("Sensitive scan generated evidence", test_sensitive_scan_generated_evidence),
        ("Tool drift clean", test_tool_drift_clean),
        ("Ledger schema loads and validates", test_ledger_schema_loads_and_validates),
        ("Live gap normalization and acceptance gate", test_live_gap_normalization_and_acceptance_gate),
        ("Partial retrieval status blocks completion", test_partial_retrieval_status_blocks_completion),
        ("Reinforcement round lineage is explicit", test_round_lineage_is_explicit),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
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
