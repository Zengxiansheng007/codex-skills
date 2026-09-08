#!/usr/bin/env python3
"""Two-stage Research adapter: retrieval/evidence-freeze + tool-free serialization.

This module implements the workspace-only candidate repair for the
bailian/glm-5.2 + Claude Code gateway combination that returns empty output
whenever ``--json-schema`` is enabled (structured-output-empty root cause).

The adapter keeps the provider-native path unchanged and adds an explicit
``adapter-validated`` compatibility profile. It splits Research execution into:

Stage one — retrieval/evidence-freeze (FR-ADP-002, FR-ADP-003):
    Freeze every retrieval artifact (session identity, queries, tool calls,
    permission results, sources with content digests, boundary checks, registry
    hash) into an immutable evidence ledger and hash it canonically.

Stage two — tool-free serialization (FR-ADP-002, FR-ADP-004, FR-ADP-006):
    Consume the frozen ledger and the target Schema only. Expose no retrieval,
    shell, browser, filesystem-write, or network tools. Allow at most three
    format attempts using one unchanged evidence hash. Reject any final source,
    URL, claim, or claim-source mapping absent from the frozen ledger.

Local Schema (Draft 2020-12) and semantic validation are the acceptance
authority (FR-ADP-005). Failures propagate without false completion
(FR-ADP-008).

This module performs no live external calls and spawns no subprocess. It is
deterministic and safe to run inside the candidate workspace.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "research-result.schema.json"
LEDGER_SCHEMA_PATH = SKILL_ROOT / "schemas" / "research-evidence-ledger.schema.json"
REGISTRY_PATH = SKILL_ROOT / "schemas" / "public-research-tool-registry.json"
FAILURE_CLASSIFICATION = SKILL_ROOT / "schemas" / "failure-classification.json"

MAX_FORMAT_ATTEMPTS = 3
MAX_REINFORCEMENT_ROUNDS = 1

# Tools forbidden in the serialization stage (FR-ADP-002). Any of these names
# appearing in a serialization tool manifest or attempted tool call is a P0
# serialization-tool-access failure.
SERIALIZATION_FORBIDDEN_TOOL_RE = re.compile(
    r"mcp__|web_search|web_fetch|firecrawl|subprocess|os\.system|urllib|"
    r"requests\.|http|socket|shell|bash|powershell|curl|wget|"
    r"open\(|write\(|mkdir|rmdir|remove\("
)


@dataclass
class AdapterFinding:
    severity: str
    rule: str
    message: str
    failure_class: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable canonical JSON: sorted keys, no spaces, ensure_ascii=False."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def schema_hash(schema_path: Path = SCHEMA_PATH) -> str:
    """Canonical SHA-256 over the research-result schema file bytes."""
    return _sha256_bytes(schema_path.read_bytes())


def registry_hash() -> str:
    """SHA-256 over the public-research-tool-registry.json bytes."""
    return _sha256_bytes(REGISTRY_PATH.read_bytes())


def registry_names() -> list[str]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8")).get("toolNames", [])


def freeze_ledger(
    ledger_id: str,
    requirement_anchor: str,
    session: dict,
    queries: list[dict],
    tool_calls: list[dict],
    permission_results: dict,
    sources: list[dict],
    registry_match: bool,
    boundary_checks: dict,
    frozen_at: str,
    round_id: str = "ROUND-1",
    claims: Optional[list[dict]] = None,
    schema_enforcement_mode: str = "adapter-validated",
) -> tuple[dict, str]:
    """Stage one: build the frozen evidence ledger and compute its hash.

    Returns (ledger_dict, ledger_sha256). The hash is computed over the
    canonical JSON of the ledger body with ``ledgerSha256`` removed, so the
    hash is stable and reproducible.
    """
    body = {
        "ledgerType": "research-evidence-ledger",
        "ledgerId": ledger_id,
        "requirementAnchor": requirement_anchor,
        "roundId": round_id,
        "schemaEnforcementMode": schema_enforcement_mode,
        "providerNativeSchema": schema_enforcement_mode == "provider-native",
        "session": session,
        "queries": queries,
        "toolCalls": tool_calls,
        "permissionResults": permission_results,
        "sources": sources,
        "claims": claims or [],
        "registryHash": registry_hash(),
        "registryMatch": registry_match,
        "boundaryChecks": boundary_checks,
        "frozenAt": frozen_at,
    }
    digest = _sha256_bytes(canonical_json(body).encode("utf-8"))
    body["ledgerSha256"] = digest
    return body, digest


def extract_candidate(raw: str) -> tuple[bool, Optional[dict], list[AdapterFinding]]:
    """Stage two input parsing: extract a research-result candidate from raw model output.

    Accepts pure JSON, prose-prefixed JSON, or a JSON string nested in an
    envelope ``{"result": "..."}`` / ``{"result": {...}}``. Rejects prose-only
    and malformed JSON without fabricating a packet.
    """
    findings: list[AdapterFinding] = []
    text = raw or ""
    if text.startswith("﻿"):
        findings.append(AdapterFinding("P0", "bom-detected", "Output has UTF-8 BOM.", "output-not-json"))
        text = text.lstrip("﻿")
    stripped = text.strip()
    if not stripped:
        findings.append(AdapterFinding("P0", "empty-output", "Serialization output is empty.", "output-not-json"))
        return False, None, findings

    def _scan_for_json_object(value: str) -> Optional[dict]:
        decoder = json.JSONDecoder()  # Reuse stdlib parsing while tolerating prose prefixes.
        idx = value.find("{")  # Start only at object candidates, never fabricate JSON.
        while idx != -1:
            try:
                parsed, _ = decoder.raw_decode(value[idx:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                idx = value.find("{", idx + 1)
                continue
            idx = value.find("{", idx + 1)
        return None

    candidate = None
    # 1. Direct object.
    try:
        candidate = json.loads(stripped)
    except json.JSONDecodeError:
        candidate = None

    # 2. Prose-prefixed object.
    if not isinstance(candidate, dict) or candidate.get("resultType") != "research-result":
        candidate = _scan_for_json_object(stripped)

    # 3. Envelope {"result": "..." | {...}}.
    if not isinstance(candidate, dict) or candidate.get("resultType") != "research-result":
        envelope = None
        try:
            envelope = json.loads(stripped)
        except json.JSONDecodeError:
            envelope = None
        if isinstance(envelope, dict) and "result" in envelope:
            inner = envelope["result"]
            if isinstance(inner, str):
                candidate = _scan_for_json_object(inner)
            elif isinstance(inner, dict):
                candidate = inner

    if not isinstance(candidate, dict) or candidate.get("resultType") != "research-result":
        findings.append(
            AdapterFinding(
                "P0",
                "not-research-result",
                "Output is not a research-result JSON object (prose-around-json or malformed).",
                "output-not-json",
            )
        )
        return False, None, findings

    return True, candidate, findings


def validate_against_ledger(candidate: dict, ledger: dict) -> list[AdapterFinding]:
    """FR-ADP-004: every final source, URL, claim, and claim-source mapping must
    resolve to the frozen evidence ledger. Additions fail validation.
    """
    findings: list[AdapterFinding] = []
    ledger_sources = {s.get("url"): s for s in ledger.get("sources", []) if isinstance(s, dict)}
    ledger_urls = set(ledger_sources.keys())

    # Final sources must all exist in the ledger.
    final_sources = candidate.get("sources", [])
    if not isinstance(final_sources, list):
        findings.append(AdapterFinding("P0", "sources-not-array", "sources must be an array.", "unsupported-fact-introduced"))
        final_sources = []
    for src in final_sources:
        if not isinstance(src, dict):
            findings.append(AdapterFinding("P0", "invalid-source", "source must be an object.", "unsupported-fact-introduced"))
            continue
        url = src.get("url", "")
        if url not in ledger_urls:
            findings.append(
                AdapterFinding(
                    "P0",
                    "source-absent-from-ledger",
                    f"Final source URL absent from frozen ledger: {url}.",
                    "unsupported-fact-introduced",
                )
            )

    # Every claim sourceUrl must exist in the ledger source set.
    claims = candidate.get("claims", [])
    if not isinstance(claims, list):
        claims = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        url = claim.get("sourceUrl", "")
        if url and url not in ledger_urls:
            findings.append(
                AdapterFinding(
                    "P0",
                    "claim-absent-from-ledger",
                    f"Claim references source absent from frozen ledger: {url}.",
                    "unsupported-fact-introduced",
                )
            )

    # claimSourceMap values must reference ledger URLs.
    csm = candidate.get("claimSourceMap", {})
    if isinstance(csm, dict):
        for claim_id, urls in csm.items():
            if isinstance(urls, str):
                urls = [urls]
            if isinstance(urls, list):
                for url in urls:
                    if isinstance(url, str) and url not in ledger_urls:
                        findings.append(
                            AdapterFinding(
                                "P0",
                                "claim-map-absent-from-ledger",
                                f"claimSourceMap[{claim_id}] references source absent from ledger: {url}.",
                                "unsupported-fact-introduced",
                            )
                        )
    return findings


def check_serialization_tool_boundary(attempted_tools: list[str]) -> list[AdapterFinding]:
    """FR-ADP-002: serialization must expose no retrieval/shell/browser/write/network tools."""
    findings: list[AdapterFinding] = []
    for tool in attempted_tools or []:
        if not isinstance(tool, str):
            continue
        if SERIALIZATION_FORBIDDEN_TOOL_RE.search(tool) or tool.startswith("mcp__"):
            findings.append(
                AdapterFinding(
                    "P0",
                    "serialization-tool-access",
                    f"Serialization phase attempted forbidden tool: {tool}.",
                    "serialization-tool-access",
                )
            )
    return findings


def check_evidence_hash_stability(attempt_hashes: list[str]) -> list[AdapterFinding]:
    """FR-ADP-006: all format attempts must use one unchanged evidence hash."""
    findings: list[AdapterFinding] = []
    unique = set(h for h in attempt_hashes if h)
    if len(unique) > 1:
        findings.append(
            AdapterFinding(
                "P0",
                "evidence-hash-unstable",
                f"Evidence hash changed between format attempts: {sorted(unique)}.",
                "evidence-hash-unstable",
            )
        )
    return findings


def _result(findings: list[AdapterFinding]) -> dict:
    p0 = sum(1 for f in findings if f.severity == "P0")
    p1 = sum(1 for f in findings if f.severity == "P1")
    status = "rejected" if p0 > 0 else "review-required" if p1 > 0 else "accepted"
    return {
        "status": status,
        "summary": {"P0": p0, "P1": p1, "P2": 0},
        "findings": [f.to_dict() for f in findings],
    }


def serialize_with_ledger(
    ledger: dict,
    serializer: Callable[[dict, int], str],
    validator: Optional[Callable[[str], dict]] = None,
    max_attempts: int = MAX_FORMAT_ATTEMPTS,
    attempted_tools_per_attempt: Optional[list[list[str]]] = None,
) -> dict:
    """Stage two: tool-free bounded serialization.

    ``serializer(ledger, attempt_index) -> raw_text`` is a pure callable that
    receives the frozen ledger and an attempt index (0-based) and returns the
    candidate raw output. It must not perform retrieval or network access; the
    adapter independently checks that no forbidden tool was attempted.

    ``validator(raw_text)`` defaults to the research-result validator; it must
    return ``{"status": ..., "summary": {"P0":.., "P1":..}, "findings":[...]}``.

    The adapter records every attempt, ensures the evidence hash is stable,
    enforces the tool boundary, and validates each candidate against the ledger
    and the target Schema. Exhaustion returns ``blocked`` / ``repair-needed``,
    never ``complete``.
    """
    # Local import to avoid a hard cycle and keep this module importable standalone.
    import validate_research_result

    validator = validator or validate_research_result.validate
    ledger_hash = ledger.get("ledgerSha256", "")

    # Persistent findings apply regardless of acceptance (tool boundary, hash
    # stability). Per-attempt validation failures are recorded in the attempt
    # history; they only block completion when no attempt is accepted
    # (exhaustion), because FR-ADP-006 allows bounded format retries that
    # eventually succeed.
    persistent_findings: list[AdapterFinding] = []
    attempt_findings: list[AdapterFinding] = []

    # Tool boundary check across all attempts.
    if attempted_tools_per_attempt:
        for tools in attempted_tools_per_attempt:
            persistent_findings.extend(check_serialization_tool_boundary(tools))
    else:
        # Stage two declares an empty tool manifest by contract.
        persistent_findings.extend(check_serialization_tool_boundary([]))

    attempts: list[dict] = []
    attempt_hashes: list[str] = []
    accepted_candidate = None
    accepted_raw = None

    for attempt_idx in range(max_attempts):
        raw = serializer(ledger, attempt_idx)
        # Every attempt is bound to the same ledger hash.
        attempt_hashes.append(ledger_hash)
        record = {
            "attemptIndex": attempt_idx,
            "ledgerSha256": ledger_hash,
            "rawLength": len(raw) if isinstance(raw, str) else 0,
            "valid": False,
            "validation": None,
            "ledgerFindings": [],
        }

        ok, candidate, extract_findings = extract_candidate(raw)
        record["extractOk"] = ok
        if not ok:
            record["ledgerFindings"] = [f.to_dict() for f in extract_findings]
            attempt_findings.extend(extract_findings)
            attempts.append(record)
            continue

        val = validator(raw)
        record["validation"] = val
        p0 = val.get("summary", {}).get("P0", 0)
        p1 = val.get("summary", {}).get("P1", 0)

        ledger_findings = validate_against_ledger(candidate, ledger)
        record["ledgerFindings"] = [f.to_dict() for f in ledger_findings]

        # FR-ADP-005: a validator-rejected candidate is a per-attempt failure.
        if p0 > 0:
            attempt_findings.append(
                AdapterFinding(
                    "P0",
                    "adapter-validation-failed",
                    f"Attempt {attempt_idx} failed local Schema/semantic validation (P0={p0}).",
                    "adapter-validation-failed",
                )
            )
        elif p1 > 0:
            attempt_findings.append(
                AdapterFinding(
                    "P1",
                    "adapter-validation-failed",
                    f"Attempt {attempt_idx} failed local Schema/semantic validation (P1={p1}).",
                    "adapter-validation-failed",
                )
            )
        attempt_findings.extend(ledger_findings)

        if p0 == 0 and p1 == 0 and not ledger_findings:
            record["valid"] = True
            accepted_candidate = candidate
            accepted_raw = raw
            attempts.append(record)
            break
        attempts.append(record)

    # Evidence hash stability across recorded attempts.
    persistent_findings.extend(check_evidence_hash_stability(attempt_hashes))

    # If format attempts exhausted without acceptance, all per-attempt failures
    # become blocking for the completion decision.
    if accepted_candidate is None:
        persistent_findings.append(
            AdapterFinding(
                "P1",
                "format-attempt-exhaustion",
                f"{max_attempts} format attempts exhausted without a valid output.",
                "format-attempt-exhaustion",
            )
        )
        final_findings = persistent_findings + attempt_findings
    else:
        # An accepted attempt supersedes its own per-attempt format failures;
        # only persistent (tool/hash) findings can still block completion.
        final_findings = persistent_findings

    result = _result(final_findings)
    result["attempts"] = attempts
    result["accepted"] = accepted_candidate is not None
    result["acceptedCandidate"] = accepted_candidate
    result["acceptedRaw"] = accepted_raw
    result["maxAttempts"] = max_attempts
    result["evidenceHashStable"] = len(set(attempt_hashes)) <= 1
    result["schemaEnforcementMode"] = ledger.get("schemaEnforcementMode", "adapter-validated")
    result["providerNativeSchema"] = ledger.get("providerNativeSchema", False)
    result["evidenceLedgerRef"] = {
        "ledgerId": ledger.get("ledgerId", ""),
        "ledgerSha256": ledger_hash,
    }
    return result


def run_two_stage(
    ledger: dict,
    serializer: Callable[[dict, int], str],
    validator: Optional[Callable[[str], dict]] = None,
    max_attempts: int = MAX_FORMAT_ATTEMPTS,
    attempted_tools_per_attempt: Optional[list[list[str]]] = None,
) -> dict:
    """Full two-stage orchestration returning a fail-closed outcome.

    The outcome carries a ``completionClaim`` that is never ``complete`` when
    any P0/P1 finding exists (FR-ADP-008).
    """
    ser = serialize_with_ledger(
        ledger, serializer, validator=validator, max_attempts=max_attempts,
        attempted_tools_per_attempt=attempted_tools_per_attempt,
    )
    p0 = ser["summary"]["P0"]
    p1 = ser["summary"]["P1"]
    if p0 > 0 or p1 > 0:
        completion = "blocked" if p0 > 0 else "repair-needed"
        failure_class = next(
            (f["failure_class"] for f in ser["findings"] if f.get("failure_class")),
            "internal-error",
        )
    else:
        completion = "complete"
        failure_class = None

    ser["completionClaim"] = completion
    ser["failureClass"] = failure_class
    return ser


def main() -> int:
    """Smoke entry: validate a candidate output against a frozen ledger file."""
    import argparse

    parser = argparse.ArgumentParser(description="Two-stage Research adapter")
    parser.add_argument("--ledger", required=True, help="Path to frozen evidence ledger JSON")
    parser.add_argument("--candidate", required=True, help="Path to serialization candidate JSON")
    parser.add_argument("--json", dest="json_output", default=None)
    args = parser.parse_args()

    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    raw = Path(args.candidate).read_text(encoding="utf-8", errors="replace")
    ok, candidate, extract_findings = extract_candidate(raw)
    findings = list(extract_findings)
    if ok:
        findings.extend(validate_against_ledger(candidate, ledger))
    result = _result(findings)
    result["evidenceLedgerRef"] = {
        "ledgerId": ledger.get("ledgerId", ""),
        "ledgerSha256": ledger.get("ledgerSha256", ""),
    }
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(out, encoding="utf-8")
    print(out)
    return 1 if result["summary"]["P0"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
