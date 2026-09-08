from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scholar_result_adapter import build_payload, main


LEDGER_SHA = "a" * 64


def accepted(*, scholarly: bool = True) -> dict:
    source = {
        "url": "https://doi.org/10.1000/example" if scholarly else "https://example.com/reference",
        "title": "Example source",
        "retrievedAt": "2026-08-29T00:00:00Z",
        "verified": True,
        "toolUsed": "mcp__exa__web_search_exa",
    }
    if scholarly:
        source.update({"doi": "10.1000/example", "authors": ["A. Researcher"], "year": 2025})
    return {
        "resultType": "research-result",
        "researchId": "RR-1",
        "roundId": "round-2",
        "completionClaim": "complete",
        "evidenceComplete": True,
        "adapterValidation": {"localSchemaValid": True, "semanticGatesPassed": True},
        "evidenceLedgerRef": {"ledgerId": "LEDGER-1", "ledgerSha256": LEDGER_SHA},
        "queries": [{"query": "q", "round": 2}],
        "scope": {"objective": "objective"},
        "sources": [source],
        "gaps": [],
        "p0p1Gaps": [],
    }


class AdapterTest(unittest.TestCase):
    def test_maps_doi_source_to_baseline_shape(self) -> None:
        data = build_payload(accepted())
        self.assertEqual(data["status"], "ready")
        payload = data["payloads"][0]
        self.assertEqual(payload["source"], "governed-research")
        self.assertEqual(payload["round"], 2)
        self.assertEqual(payload["papers"][0]["id"], "doi:10.1000/example")
        self.assertEqual(payload["papers"][0]["governance"]["ledgerSha256"], LEDGER_SHA)

    def test_web_only_source_is_not_fabricated(self) -> None:
        data = build_payload(accepted(scholarly=False))
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["failureClass"], "no-compatible-scholarly-records")
        self.assertEqual(len(data["excludedSources"]), 1)

    def test_incomplete_research_blocks_before_mapping(self) -> None:
        result = accepted()
        result["completionClaim"] = "partial"
        data = build_payload(result)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["payloads"], [])
        self.assertIn("result-not-complete", {item["code"] for item in data["findings"]})

    def test_open_p1_gap_blocks(self) -> None:
        result = accepted()
        result["gaps"] = [{"severity": "P1", "description": "missing source"}]
        self.assertEqual(build_payload(result)["status"], "blocked")

    def test_failure_class_blocks(self) -> None:
        result = accepted()
        result["failureClass"] = "timeout"
        self.assertEqual(build_payload(result)["status"], "blocked")

    def test_partial_retrieval_blocks(self) -> None:
        result = accepted()
        result["retrievalStatus"] = "partial"
        self.assertEqual(build_payload(result)["status"], "blocked")

    def test_ledger_hash_mismatch_blocks(self) -> None:
        result = accepted()
        data = build_payload(result, expected_ledger_sha256="b" * 64)
        self.assertEqual(data["status"], "blocked")
        self.assertIn("ledger-hash-mismatch", {item["code"] for item in data["findings"]})

    def test_claim_outside_source_set_blocks(self) -> None:
        result = accepted()
        result["claims"] = [{"text": "unsupported", "sourceUrl": "https://example.com/not-in-sources"}]
        data = build_payload(result)
        self.assertEqual(data["status"], "blocked")
        self.assertIn("claim-source-outside-result", {item["code"] for item in data["findings"]})

    def test_claim_source_outside_ledger_blocks(self) -> None:
        result = accepted()
        result["claims"] = [{"text": "unsupported", "sourceUrl": "https://example.com/not-in-ledger"}]
        data = build_payload(result)
        self.assertEqual(data["status"], "blocked")

    def test_openalex_identity_uses_baseline_field_name(self) -> None:
        result = accepted()
        result["sources"][0].pop("doi")
        result["sources"][0]["openalexId"] = "W123"
        result["sources"][0]["url"] = "https://openalex.org/W123"
        data = build_payload(result)
        self.assertEqual(data["payloads"][0]["papers"][0]["id"], "openalex:W123")
        self.assertEqual(data["payloads"][0]["papers"][0]["openalex_id"], "W123")

    def test_duplicate_identity_is_deduplicated(self) -> None:
        result = accepted()
        result["sources"].append(copy.deepcopy(result["sources"][0]))
        data = build_payload(result)
        self.assertEqual(len(data["payloads"][0]["papers"]), 1)

    def test_cli_writes_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "result.json"
            output = root / "adapter.json"
            source.write_text(json.dumps(accepted(), ensure_ascii=False), encoding="utf-8")
            self.assertEqual(main(["--result", str(source), "--output", str(output)]), 0)
            raw = output.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(json.loads(raw.decode("utf-8"))["status"], "ready")


if __name__ == "__main__":
    unittest.main()
