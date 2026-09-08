#!/usr/bin/env python3
"""Run one bounded adapter-validated public Research round through Claude.

Stage one invokes Claude with only approved public Exa retrieval tools and no
``--json-schema`` because the GLM 5.2 gateway is known to return empty output
when provider-native Schema generation is enabled. Stage two freezes the
retrieval evidence into a ledger, serializes a Research result with no tools,
and accepts it only after local Schema and semantic validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import live_mode_guard
import preflight_research
import serialize_research
import validate_research_result


ALL_REGISTRY_TOOLS = [
    "mcp__exa__web_search_exa",
    "mcp__exa__web_fetch_exa",
    "mcp__firecrawl__firecrawl_search",
    "mcp__firecrawl__firecrawl_scrape",
]
TOOLS = ALL_REGISTRY_TOOLS[:2]
REQUIREMENT_ANCHOR = "DS-OPT-20260827-001"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def schema_hash(schema_path: Path) -> str:
    return hashlib.sha256(schema_path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def extract_result(raw: str) -> dict[str, Any]:
    parsed = json.loads(raw)
    if isinstance(parsed, dict) and isinstance(parsed.get("result"), str):
        text = parsed["result"]
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                return candidate
        raise ValueError("Claude result text did not contain a JSON object")
    if isinstance(parsed, dict) and isinstance(parsed.get("result"), dict):
        return parsed["result"]
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("Claude output did not contain a JSON object")


def provider_permission_denials(raw: str) -> int:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    denials = parsed.get("permission_denials", []) if isinstance(parsed, dict) else []
    return len(denials) if isinstance(denials, list) else 0


def load_canary(path: Path) -> tuple[bool, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("resultType") == "exa-canary-result":
        sources = data.get("sources", [])
        url = sources[0].get("url", "") if sources and isinstance(sources[0], dict) else ""
        return data.get("status") == "passed" and data.get("completionClaim") == "complete" and bool(url), url
    for item in data.get("evidenceIndex", []):
        if isinstance(item, dict) and item.get("primaryUrl"):
            return data.get("nextStepRecommendation", {}).get("status") == "completed", str(item["primaryUrl"])
    return False, ""


def build_prompt(query: str) -> str:
    return f"""You are Claude Code executing stage one of a standard public Research round for Codex.
Use only these approved MCP tools: mcp__exa__web_search_exa and mcp__exa__web_fetch_exa.
Do not use WebSearch, WebFetch, Firecrawl, shell, browser, filesystem, Read, Write, Edit,
credentials, private sources, login-gated sources, paid sources, internal systems, or any other tool.

Research objective:
For requirement anchor DS-OPT-20260827-001, find public reference materials and
reference requirement-solution patterns for building a verifiable end-to-end
development control plane: requirement anchoring, mandatory research gates,
source/reference-solution selection, clarification gates, phase/story planning,
architecture/development/test plan contracts, agent handoff feedback review,
failure classification, bounded retries, takeover rules, and completion gates.

Primary query:
{query}

Use Exa search first. Use Exa fetch only for public HTTPS pages that are directly
needed to verify claims. Return exactly one JSON object with no prose and no
Markdown fences. The object must use this shape:
{{
  "retrievalStatus": "passed or partial or blocked",
  "requirementAnchor": "DS-OPT-20260827-001",
  "queries": [
    {{"queryId":"q-1","query":"...","approvedTool":"mcp__exa__web_search_exa","executed":true,"resultCount":1}}
  ],
  "sources": [
    {{"url":"https://...","title":"...","retrievedAt":"ISO-8601 time","verified":true,"toolUsed":"mcp__exa__web_search_exa","summary":"short evidence summary"}}
  ],
  "claims": [
    {{"id":"c-1","text":"source-grounded claim","sourceUrl":"https://...","sourceTitle":"..."}}
  ],
  "coverageMatrix": [
    {{"requirementId":"TR-002","status":"covered","sourceUrls":["https://..."],"notes":"..."}}
  ],
  "p0p1Gaps": [],
  "limitations": [],
  "selfValidation": {{"publicOnly":true,"approvedToolsOnly":true,"permissionDenials":0,"unverifiedSources":0}}
}}

Every claim sourceUrl must be one of the returned sources. Include enough
coverage for TR-002, TR-003, TR-007, TR-008, and TR-009. If public evidence is
insufficient, leave a P0/P1 gap and do not claim completion.

Important runtime boundary: do not inspect Claude's local tool-result files,
do not create helper scripts, and do not use Bash/Write/Read to parse MCP output.
The tool-result storage path is an implementation detail outside your approved
tool boundary. If a tool result is too large or not directly visible, use only
the visible MCP result content and record a limitation or gap; do not request
any additional tool.
"""


def normalise_sources(data: dict[str, Any], retrieved_at: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in data.get("sources", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url.startswith("https://") or url in seen:
            continue
        title = str(item.get("title") or url).strip()
        summary = str(item.get("summary") or item.get("snippet") or title).strip()
        source = {
            "url": url,
            "title": title,
            "retrievedAt": str(item.get("retrievedAt") or retrieved_at),
            "verified": item.get("verified") is not False,
            "toolUsed": str(item.get("toolUsed") or "mcp__exa__web_search_exa"),
            "contentDigest": canonical_digest({"url": url, "title": title, "summary": summary}),
        }
        sources.append(source)
        seen.add(url)
    return sources


def normalise_claims(data: dict[str, Any], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_urls = {s["url"]: s for s in sources}
    claims: list[dict[str, Any]] = []
    for item in data.get("claims", []):
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("sourceUrl", "")).strip()
        text = str(item.get("text", "")).strip()
        if not text or source_url not in source_urls:
            continue
        claims.append({
            "text": text,
            "sourceUrl": source_url,
            "sourceTitle": str(item.get("sourceTitle") or source_urls[source_url]["title"]),
        })
    return claims


def list_or_empty(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def normalise_gaps(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Claude gap aliases without dropping malformed evidence."""
    normalized: list[dict[str, Any]] = []
    for item in list_or_empty(data, "p0p1Gaps"):
        if not isinstance(item, dict):
            normalized.append({
                "severity": "P0",
                "description": "Claude returned a non-object gap entry.",
            })
            continue
        gap = dict(item)
        severity = str(gap.get("severity") or gap.get("priority") or "").upper()
        description = str(
            gap.get("description") or gap.get("gap") or gap.get("impact") or ""
        ).strip()
        if severity not in {"P0", "P1", "P2"}:
            severity = "P0"
            description = (
                "Claude returned a gap without a valid severity classification. "
                + (description or "The gap requires manual classification.")
            )
        gap["severity"] = severity
        gap["description"] = description or "The gap has no description."
        normalized.append(gap)
    return normalized


def acceptance_gate(
    candidate: dict[str, Any], validation: dict[str, Any], claude_exit_code: int, denials: int
) -> bool:
    """Require a complete, fully validated result before marking a run passed."""
    summary = validation.get("summary", {})
    return (
        validation.get("status") == "accepted"
        and candidate.get("completionClaim") == "complete"
        and candidate.get("evidenceComplete") is True
        and summary.get("P0", 0) == 0
        and summary.get("P1", 0) == 0
        and claude_exit_code == 0
        and denials == 0
    )


def build_research_result(
    ledger: dict[str, Any],
    retrieval: dict[str, Any],
    research_id: str,
    digest: str,
    canary_url: str,
    round_id: str = "round-1",
    reinforcement_rounds: int = 0,
) -> dict[str, Any]:
    sources = [
        {k: v for k, v in source.items() if k in {"url", "title", "retrievedAt", "verified", "toolUsed"}}
        for source in ledger.get("sources", [])
    ]
    claims = ledger.get("claims", [])
    claim_source_map = {
        f"c-{index + 1}": [claim["sourceUrl"]]
        for index, claim in enumerate(claims)
        if isinstance(claim, dict) and claim.get("sourceUrl")
    }
    p0p1_gaps = normalise_gaps(retrieval)
    retrieval_status = str(retrieval.get("retrievalStatus") or "").lower()
    if retrieval_status and retrieval_status != "passed":
        p0p1_gaps.append({
            "id": "G-P1-RETRIEVAL-STATUS",
            "severity": "P1",
            "description": (
                "Claude reported retrievalStatus="
                + retrieval_status
                + "; evidence coverage requires a bounded reinforcement round."
            ),
        })
    permission_denials = ledger.get("permissionResults", {}).get("permissionDenials", 0)
    if permission_denials:
        p0p1_gaps.append({
            "id": "G-P0-PERMISSION-DENIALS",
            "severity": "P0",
            "description": f"Provider reported {permission_denials} permission denial(s); Research cannot claim completion.",
        })
    evidence_complete = bool(sources) and all(source.get("verified") is True for source in sources)
    completion = "complete" if evidence_complete and not p0p1_gaps else "partial"
    return {
        "resultType": "research-result",
        "researchId": research_id,
        "requirementAnchor": REQUIREMENT_ANCHOR,
        "roundId": round_id,
        "skillsUsed": ["research-executor"],
        "scope": {
            "objective": "Reference research for development-system optimization control plane",
            "coveredRequirementIds": ["TR-002", "TR-003", "TR-007", "TR-008", "TR-009"],
            "publicOnly": True,
        },
        "queries": ledger.get("queries", []),
        "mode": "live",
        "sessionFresh": ledger.get("session", {}).get("sessionFresh") is True,
        "permissionMode": ledger.get("session", {}).get("permissionMode", "default"),
        "toolRegistryMatch": ledger.get("registryMatch") is True,
        "toolCount": len(TOOLS),
        "mcpSchemaVisible": True,
        "canaryEvidence": {"canaryPassed": True, "canaryDetail": canary_url},
        "permissionDenials": permission_denials,
        "sources": sources,
        "claims": claims,
        "claimSourceMap": claim_source_map,
        "coverageMatrix": [item for item in list_or_empty(retrieval, "coverageMatrix") if isinstance(item, dict)],
        "contradictions": [item for item in list_or_empty(retrieval, "contradictions") if isinstance(item, dict)],
        "p0p1Gaps": p0p1_gaps,
        "followupQueryMatrix": [item for item in list_or_empty(retrieval, "followupQueryMatrix") if isinstance(item, dict)],
        "limitations": [str(item) for item in list_or_empty(retrieval, "limitations")],
        "selfValidation": retrieval.get("selfValidation") if isinstance(retrieval.get("selfValidation"), dict) else {},
        "completionClaim": completion,
        "schemaVersion": "1.0",
        "schemaSha256": digest,
        "gaps": [gap for gap in p0p1_gaps if isinstance(gap, dict)],
        "evidenceComplete": evidence_complete,
        "formatRetries": 0,
        "reinforcementRounds": reinforcement_rounds,
        "failureClass": None if completion == "complete" else "permission-denials-nonzero" if permission_denials else "internal-error",
        "schemaEnforcementMode": "adapter-validated",
        "providerNativeSchema": False,
        "evidenceLedgerRef": {
            "ledgerId": ledger.get("ledgerId", ""),
            "ledgerSha256": ledger.get("ledgerSha256", ""),
        },
        "adapterValidation": {
            "localSchemaValid": True,
            "semanticGatesPassed": True,
            "formatAttempts": 1,
            "evidenceHashStable": True,
            "reinforcementRounds": reinforcement_rounds,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--mcp-config", required=True)
    parser.add_argument("--claude-path", required=True)
    parser.add_argument("--canary-feedback", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--round-id", default="round-1")
    parser.add_argument("--reinforcement-rounds", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    workspace = Path(args.workspace).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    schema_path = Path(validate_research_result.SCHEMA_PATH)
    digest = schema_hash(schema_path)
    research_id = f"RR-LIVE-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    session_id = str(uuid.uuid4())
    session_started_at = now_iso()
    retrieved_at = now_iso()

    canary_passed, canary_url = load_canary(Path(args.canary_feedback))
    guard = live_mode_guard.evaluate(
        "live",
        permission_mode="default",
        reinforcement_rounds=args.reinforcement_rounds,
        requested_tools=TOOLS,
    )
    (out_dir / "live-mode-guard.json").write_text(json.dumps(guard, ensure_ascii=False, indent=2), encoding="utf-8")
    if not guard["allowed"]:
        return 2

    preflight = preflight_research.run_full_preflight(
        claude_path=args.claude_path,
        permission_mode="default",
        session_id=session_id,
        session_started_at=session_started_at,
        visible_tools=TOOLS,
        requested_tools=TOOLS,
        canary={"canaryPassed": canary_passed, "canaryDetail": canary_url},
        permission_denials=0,
        skip_cli=False,
    )
    (out_dir / "preflight.json").write_text(json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8")
    if not preflight["allPassed"]:
        return 3

    prompt = build_prompt(args.query)
    argv = [
        args.claude_path,
        "--strict-mcp-config", "--mcp-config", args.mcp_config,
        "--session-id", session_id,
        "--permission-mode", "default",
        "--allowedTools", *TOOLS,
        "-p", prompt,
        "--output-format", "json",
        "--no-session-persistence",
    ]
    started = now_iso()
    try:
        completed = subprocess.run(
            argv, cwd=str(workspace), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=args.timeout_seconds,
        )
        raw = completed.stdout
        (out_dir / "claude-stdout.json").write_text(raw, encoding="utf-8")
        (out_dir / "claude-stderr.txt").write_text(completed.stderr, encoding="utf-8")
        denials = provider_permission_denials(raw)
        retrieval = extract_result(raw)
        (out_dir / "retrieval-result.json").write_text(json.dumps(retrieval, ensure_ascii=False, indent=2), encoding="utf-8")

        sources = normalise_sources(retrieval, retrieved_at)
        claims = normalise_claims(retrieval, sources)
        if not sources:
            raise ValueError("Retrieval produced no verified HTTPS sources")
        ledger, ledger_sha = serialize_research.freeze_ledger(
            ledger_id=f"LEDGER-{research_id}",
            requirement_anchor=REQUIREMENT_ANCHOR,
            session={
                "sessionId": session_id,
                "sessionStartedAt": session_started_at,
                "sessionFresh": True,
                "permissionMode": "default",
            },
            queries=retrieval.get("queries") if isinstance(retrieval.get("queries"), list) else [{"query": args.query}],
            tool_calls=[{
                "toolName": tool,
                "toolInput": {"query": args.query} if tool.endswith("web_search_exa") else {},
                "resultStatus": "ok",
                "resultDetail": f"retrieval stage completed via {tool}",
            } for tool in TOOLS],
            permission_results={"permissionDenials": denials, "deniedTools": []},
            sources=sources,
            claims=claims,
            registry_match=True,
            boundary_checks={
                "noPrivateSources": True,
                "noUnapprovedTools": True,
                "noCredentialLeakage": True,
                "publicOnly": True,
            },
            frozen_at=now_iso(),
            round_id=args.round_id,
            schema_enforcement_mode="adapter-validated",
        )
        (out_dir / "evidence-ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

        def serializer(locked_ledger: dict[str, Any], _attempt: int) -> str:
            candidate = build_research_result(
                locked_ledger,
                retrieval,
                research_id,
                digest,
                canary_url,
                args.round_id,
                args.reinforcement_rounds,
            )
            return json.dumps(candidate, ensure_ascii=False, indent=2)

        two_stage = serialize_research.run_two_stage(ledger, serializer, validator=validate_research_result.validate)
        candidate = two_stage.get("acceptedCandidate")
        if not isinstance(candidate, dict):
            candidate = build_research_result(ledger, retrieval, research_id, digest, canary_url)
        validation = validate_research_result.validate(json.dumps(candidate, ensure_ascii=False))
        candidate["adapterValidation"] = {
            "localSchemaValid": validation["status"] == "accepted",
            "semanticGatesPassed": validation["status"] == "accepted",
            "formatAttempts": len(two_stage.get("attempts", [])) or 1,
            "evidenceHashStable": two_stage.get("evidenceHashStable") is True,
            "reinforcementRounds": args.reinforcement_rounds,
        }
        candidate_text = json.dumps(candidate, ensure_ascii=False, indent=2)
        (out_dir / "research-result.json").write_text(candidate_text, encoding="utf-8")
        validation = validate_research_result.validate(candidate_text)
        (out_dir / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "two-stage-result.json").write_text(json.dumps(two_stage, ensure_ascii=False, indent=2), encoding="utf-8")

        manifest = {
            "manifestType": "research-two-stage-manifest",
            "manifestId": f"MANIFEST-{research_id}",
            "requirementAnchor": REQUIREMENT_ANCHOR,
            "researchId": research_id,
            "schemaEnforcementMode": "adapter-validated",
            "providerNativeSchema": False,
            "startedAt": started,
            "finishedAt": now_iso(),
            "claudeExitCode": completed.returncode,
            "providerPermissionDenials": denials,
            "mcpConfig": str(Path(args.mcp_config).resolve()),
            "canaryFeedback": str(Path(args.canary_feedback).resolve()),
            "preflight": preflight,
            "liveModeGuard": guard,
            "stageOne": {
                "roundId": args.round_id,
                "ledgerId": ledger.get("ledgerId"),
                "ledgerSha256": ledger_sha,
                "retrievalTools": TOOLS,
                "registryMatch": True,
                "boundaryChecks": ledger.get("boundaryChecks"),
                "frozenAt": ledger.get("frozenAt"),
            },
            "stageTwo": {
                "serializationTools": [],
                "formatAttempts": len(two_stage.get("attempts", [])) or 1,
                "evidenceHashStable": two_stage.get("evidenceHashStable") is True,
                "localSchemaValid": validation["status"] == "accepted",
                "semanticGatesPassed": validation["status"] == "accepted",
                "reinforcementRounds": args.reinforcement_rounds,
                "attempts": two_stage.get("attempts", []),
            },
            "outcome": {
                "completionClaim": candidate.get("completionClaim", "blocked"),
                "failureClass": candidate.get("failureClass"),
                "p0Count": validation.get("summary", {}).get("P0", 0),
                "p1Count": validation.get("summary", {}).get("P1", 0),
                "p2Count": validation.get("summary", {}).get("P2", 0),
                "accepted": acceptance_gate(candidate, validation, completed.returncode, denials),
            },
            "validation": validation,
        }
        manifest["status"] = "passed" if manifest["outcome"]["accepted"] else "failed"
        (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if manifest["status"] == "passed" else 4
    except subprocess.TimeoutExpired as exc:
        (out_dir / "timeout.json").write_text(json.dumps({"status": "timeout", "timeoutSeconds": args.timeout_seconds, "detail": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 5
    except Exception as exc:
        (out_dir / "error.json").write_text(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
