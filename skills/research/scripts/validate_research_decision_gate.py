#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


VALID_STATUSES = {"accepted", "caveated", "rejected", "rerun", "partial", "blocked"}
VALID_COVERAGE = {"sufficient", "caveated", "insufficient", "blocked"}
CRITICAL = {"P0", "P1"}


def extract_block(text, block_id):
    pattern = re.compile(
        rf'<script\s+type=["\']application/json["\']\s+id=["\']{re.escape(block_id)}["\']\s*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing JSON block: {block_id}")
    return json.loads(match.group(1).strip())


def require_fields(obj, fields, label):
    missing = [field for field in fields if field not in obj]
    if missing:
        raise AssertionError(f"{label} missing required field(s): {', '.join(missing)}")


def main():
    if len(sys.argv) != 2:
        print("usage: validate_research_decision_gate.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    run_status = extract_block(text, "run-status")
    metadata = extract_block(text, "research-metadata")
    try:
        gate = extract_block(text, "research-decision-gate")
    except AssertionError:
        high_impact = bool(metadata.get("highImpact") or metadata.get("impactLevel") in {"high", "critical"})
        if high_impact:
            raise
        print(f"ok: {path} (no research-decision-gate; optional for non-high-impact report)")
        return 0

    require_fields(
        gate,
        [
            "schemaVersion",
            "depth",
            "mode",
            "recommendationStatus",
            "rerunResearchRequired",
            "riskAcceptanceRequired",
            "openCriticalFindings",
            "coverageMatrix",
            "grillFindingCoverage",
        ],
        "research-decision-gate",
    )

    recommendation = gate["recommendationStatus"]
    if recommendation not in VALID_STATUSES:
        raise AssertionError(f"invalid recommendationStatus: {recommendation}")

    p0_open = int(run_status.get("p0OpenCount", 0) or 0)
    p1_open = int(run_status.get("p1OpenCount", 0) or 0)
    critical_open = [
        item for item in gate["openCriticalFindings"]
        if item.get("severity") in CRITICAL and item.get("status") != "accepted-risk"
    ]
    weak_critical_coverage = [
        item for item in gate["coverageMatrix"]
        if item.get("severity", "P0") in CRITICAL
        and item.get("coverageStatus") in {"insufficient", "blocked"}
    ]
    weak_grill_coverage = [
        item for item in gate["grillFindingCoverage"]
        if item.get("severity") in CRITICAL
        and item.get("coverageStatus") in {"insufficient", "blocked"}
    ]

    for idx, item in enumerate(gate["coverageMatrix"]):
        require_fields(
            item,
            ["objectType", "objectId", "coverageStatus", "evidenceIds", "confidenceRationale", "limitations"],
            f"coverageMatrix[{idx}]",
        )
        if item["coverageStatus"] not in VALID_COVERAGE:
            raise AssertionError(f"invalid coverageStatus: {item['coverageStatus']}")
        if item["coverageStatus"] in {"sufficient", "caveated"} and not item["evidenceIds"]:
            raise AssertionError(f"coverageMatrix[{idx}] has usable status but no evidenceIds")
        if not item["confidenceRationale"].strip():
            raise AssertionError(f"coverageMatrix[{idx}] has empty confidenceRationale")

    for idx, item in enumerate(gate["grillFindingCoverage"]):
        require_fields(
            item,
            ["findingId", "severity", "blockedDecision", "coverageStatus", "evidenceIds", "rerunResearchRequired"],
            f"grillFindingCoverage[{idx}]",
        )
        if item["coverageStatus"] not in VALID_COVERAGE:
            raise AssertionError(f"invalid grill coverageStatus: {item['coverageStatus']}")
        if item["severity"] in CRITICAL and item["coverageStatus"] == "insufficient" and not item["rerunResearchRequired"]:
            raise AssertionError(f"grillFindingCoverage[{idx}] must rerun research when insufficient")

    if recommendation == "accepted":
        if p0_open or p1_open or critical_open or weak_critical_coverage or weak_grill_coverage:
            raise AssertionError("accepted recommendation cannot have open or weak P0/P1 coverage")
        if gate["rerunResearchRequired"] or gate["riskAcceptanceRequired"]:
            raise AssertionError("accepted recommendation cannot require rerun or risk acceptance")

    if recommendation in {"partial", "blocked", "rerun"}:
        if not (gate["rerunResearchRequired"] or gate["riskAcceptanceRequired"] or critical_open or p0_open or p1_open):
            raise AssertionError(f"{recommendation} must explain rerun, risk, or open critical findings")

    print(f"ok: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
