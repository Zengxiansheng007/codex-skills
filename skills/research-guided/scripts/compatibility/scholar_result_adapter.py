#!/usr/bin/env python3
"""Convert an accepted governance Research result to scholar ingest payloads.

The adapter is deliberately conservative: a web source without an explicit
scholarly identity is evidence for the governance layer, not a fabricated
paper for scholar-deep-research.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.I)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)


def _envelope(data: Any = None, *, error: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": error is None}
    if error is None:
        payload["data"] = data
    else:
        payload["error"] = error
    return payload


def _normalise_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    raw = raw.removeprefix("doi:").strip()
    match = DOI_RE.fullmatch(raw)
    return match.group(0).lower() if match else None


def _identity(source: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Return a baseline-compatible identity and the identity fields."""
    doi = _normalise_doi(source.get("doi"))
    if not doi:
        url = source.get("url")
        if isinstance(url, str) and "doi.org/" in url.lower():
            doi = _normalise_doi(url.split("doi.org/", 1)[1])
    if doi:
        return f"doi:{doi}", {"doi": doi}

    for keys, prefix, output_key in ((("openalexId", "openalex_id"), "openalex", "openalex_id"),
                                     (("arxivId", "arxiv_id"), "arxiv", "arxiv_id"),
                                     (("pmid",), "pmid", "pmid")):
        key = next((candidate for candidate in keys if source.get(candidate) is not None), keys[0])
        value = source.get(key)
        if value is not None and str(value).strip():
            clean = str(value).strip().rsplit("/", 1)[-1]
            return f"{prefix}:{clean}", {output_key: clean}
    return None


def _valid_result(result: dict[str, Any], expected_ledger_sha256: str | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if result.get("resultType") != "research-result":
        findings.append({"code": "result-type-invalid", "severity": "P0", "detail": "resultType must be research-result"})
    if result.get("completionClaim") != "complete":
        findings.append({"code": "result-not-complete", "severity": "P1", "detail": "only complete Research results may enter scholar state"})
    if result.get("evidenceComplete") is not True:
        findings.append({"code": "evidence-incomplete", "severity": "P1", "detail": "evidenceComplete must be true"})
    if result.get("failureClass"):
        findings.append({"code": "failure-class-present", "severity": "P1", "detail": "Research failureClass must be null before scholar ingest"})
    if isinstance(result.get("permissionDenials"), int) and result.get("permissionDenials", 0) > 0:
        findings.append({"code": "permission-denials-present", "severity": "P0", "detail": "permissionDenials must be zero before scholar ingest"})
    retrieval_status = str(result.get("retrievalStatus") or "passed").lower()
    if retrieval_status != "passed":
        findings.append({"code": "retrieval-not-passed", "severity": "P1", "detail": f"retrievalStatus={retrieval_status}"})
    adapter = result.get("adapterValidation") or {}
    if adapter.get("localSchemaValid") is not True or adapter.get("semanticGatesPassed") is not True:
        findings.append({"code": "local-validation-missing", "severity": "P0", "detail": "local Schema and semantic gates must both pass"})
    ledger = result.get("evidenceLedgerRef") or {}
    if not ledger.get("ledgerId") or not SHA256_RE.fullmatch(str(ledger.get("ledgerSha256", ""))):
        findings.append({"code": "ledger-reference-invalid", "severity": "P0", "detail": "valid frozen ledger reference is required"})
    if expected_ledger_sha256 is not None and str(ledger.get("ledgerSha256")) != expected_ledger_sha256:
        findings.append({"code": "ledger-hash-mismatch", "severity": "P0", "detail": "Research result ledger hash differs from the supplied frozen ledger"})
    for key in ("p0p1Gaps", "gaps"):
        for gap in result.get(key) or []:
            if isinstance(gap, dict) and str(gap.get("severity", "")).upper() in {"P0", "P1"}:
                findings.append({"code": "open-gap", "severity": str(gap.get("severity")).upper(), "detail": str(gap.get("description") or "open P0/P1 gap")})
    for source in result.get("sources") or []:
        if not isinstance(source, dict) or source.get("verified") is not True or not str(source.get("url", "")).startswith("https://"):
            findings.append({"code": "source-verification-invalid", "severity": "P0", "detail": "all Research sources must be verified HTTPS URLs"})
            break
    source_urls = {
        str(source.get("url")) for source in result.get("sources") or []
        if isinstance(source, dict) and source.get("url")
    }
    for claim in result.get("claims") or []:
        if isinstance(claim, dict) and claim.get("sourceUrl") not in source_urls:
            findings.append({"code": "claim-source-outside-result", "severity": "P0", "detail": "claim sourceUrl is absent from the Research source set"})
    claim_map = result.get("claimSourceMap") or {}
    if isinstance(claim_map, dict):
        for claim_id, urls in claim_map.items():
            if isinstance(urls, list) and any(str(url) not in source_urls for url in urls):
                findings.append({"code": "claim-map-outside-result", "severity": "P0", "detail": f"claimSourceMap[{claim_id}] references a source outside the Research source set"})
    return findings


def build_payload(
    result: dict[str, Any],
    expected_ledger_sha256: str | None = None,
    *,
    require_explicit_source_stream: bool = False,
) -> dict[str, Any]:
    findings = _valid_result(result, expected_ledger_sha256=expected_ledger_sha256)
    if any(item["severity"] in {"P0", "P1"} for item in findings):
        return {
            "status": "blocked",
            "failureClass": "research-result-not-accepted",
            "findings": findings,
            "payloads": [],
            "excludedSources": [],
        }

    scope = result.get("scope") if isinstance(result.get("scope"), dict) else {}
    query_items = result.get("queries") if isinstance(result.get("queries"), list) else []
    query_by_id = {
        str(item.get("queryId")): item for item in query_items
        if isinstance(item, dict) and item.get("queryId")
    }

    def query_context(source: dict[str, Any]) -> tuple[str, str, int]:
        linked = query_by_id.get(str(source.get("queryId"))) or {}
        if not linked and len(query_items) == 1 and isinstance(query_items[0], dict):
            linked = query_items[0]
        query = str(source.get("query") or linked.get("query") or scope.get("objective") or "governed public research")
        source_name = str(source.get("scholarSource") or source.get("sourceName") or linked.get("scholarSource") or linked.get("source") or "governed-research")
        round_value = source.get("round") if isinstance(source.get("round"), int) else linked.get("round")
        return source_name, query, round_value if isinstance(round_value, int) and round_value >= 1 else 1

    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    excluded: list[dict[str, str]] = []
    mapping_findings: list[dict[str, str]] = []
    for source in result.get("sources") or []:
        if not isinstance(source, dict):
            continue
        linked_query = query_by_id.get(str(source.get("queryId")))
        explicit_stream = source.get("scholarSource") or source.get("sourceName") or (linked_query or {}).get("scholarSource") or (linked_query or {}).get("source")
        if require_explicit_source_stream and not explicit_stream:
            mapping_findings.append({
                "code": "source-stream-mapping-missing",
                "severity": "P0",
                "detail": f"source requires explicit scholarly source stream and queryId: {source.get('url', '')}",
            })
            continue
        if require_explicit_source_stream and not source.get("queryId") and not linked_query:
            mapping_findings.append({
                "code": "source-query-mapping-missing",
                "severity": "P0",
                "detail": f"source requires queryId linked to a declared query: {source.get('url', '')}",
            })
            continue
        identity = _identity(source)
        if identity is None:
            excluded.append({"url": str(source.get("url", "")), "reason": "no-explicit-scholarly-identity"})
            continue
        pid, identity_fields = identity
        source_name, query, round_number = query_context(source)
        grouped.setdefault((source_name, query, round_number), []).append(source)

    payloads: list[dict[str, Any]] = []
    # The fixed baseline derives saturation from the last query per source;
    # ingest payloads must therefore be ordered by round before query text.
    for (source_name, query, round_number), grouped_sources in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][2], item[0][1])
    ):
        papers: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source in grouped_sources:
            identity = _identity(source)
            if identity is None:
                continue
            pid, identity_fields = identity
            if pid in seen:
                continue
            seen.add(pid)
            paper: dict[str, Any] = {
                "id": pid,
                "title": str(source.get("title") or pid),
                "authors": source.get("authors") if isinstance(source.get("authors"), list) else [],
                "year": source.get("year"),
                "venue": source.get("venue"),
                "abstract": source.get("abstract") or source.get("summary"),
                "citations": source.get("citations", 0),
                "url": source.get("url"),
                "pdf_url": source.get("pdfUrl"),
                "source": [source_name],
                "first_seen_round": round_number,
                "discovered_via": "governed_research",
                "governance": {
                    "researchId": result.get("researchId"),
                    "roundId": result.get("roundId"),
                    "ledgerSha256": (result.get("evidenceLedgerRef") or {}).get("ledgerSha256"),
                    "toolUsed": source.get("toolUsed"),
                    "scholarSource": source_name,
                },
            }
            paper.update(identity_fields)
            papers.append(paper)
        if papers:
            payloads.append({
                "source": source_name,
                "query": query,
                "round": round_number,
                "papers": papers,
            })

    if mapping_findings:
        return {
            "status": "blocked",
            "failureClass": "scholarly-source-mapping-invalid",
            "findings": mapping_findings,
            "payloads": [],
            "excludedSources": excluded,
        }

    if not payloads:
        return {
            "status": "blocked",
            "failureClass": "no-compatible-scholarly-records",
            "findings": [{"code": "no-compatible-scholarly-records", "severity": "P1", "detail": "web evidence cannot be fabricated into scholar paper records"}],
            "payloads": [],
            "excludedSources": excluded,
        }

    if require_explicit_source_stream and len({payload["source"] for payload in payloads}) < 3:
        return {
            "status": "blocked",
            "failureClass": "scholarly-source-breadth-insufficient",
            "findings": [{
                "code": "scholarly-source-breadth-insufficient",
                "severity": "P1",
                "detail": "live scholarly ingest requires at least three explicitly mapped source streams",
            }],
            "payloads": [],
            "excludedSources": excluded,
        }

    return {
        "status": "ready",
        "failureClass": None,
        "findings": findings,
        "payloads": payloads,
        "excludedSources": excluded,
        "provenance": {
            "researchId": result.get("researchId"),
            "roundId": result.get("roundId"),
            "ledgerId": (result.get("evidenceLedgerRef") or {}).get("ledgerId"),
            "ledgerSha256": (result.get("evidenceLedgerRef") or {}).get("ledgerSha256"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert accepted Research JSON to scholar ingest payload")
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = json.loads(args.result.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps(_envelope(error={"code": "input-invalid", "message": str(exc)}), ensure_ascii=False, indent=2))
        return 3
    if not isinstance(result, dict):
        print(json.dumps(_envelope(error={"code": "input-invalid", "message": "Research result must be a JSON object"}), ensure_ascii=False, indent=2))
        return 3
    data = build_payload(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(_envelope(data), ensure_ascii=False, indent=2))
    return 0 if data["status"] == "ready" else 4


if __name__ == "__main__":
    sys.exit(main())
