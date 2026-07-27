#!/usr/bin/env python3
import json
import re


STRICT_BLOCK_IDS = [
    "critique-loop-log",
    "source-review-findings",
    "followup-query-matrix",
    "p0p1-closure-matrix",
]


def extract_block(text, block_id):
    pattern = re.compile(
        rf'<script\s+type=["\']application/json["\']\s+id=["\']{re.escape(block_id)}["\']\s*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing JSON block: {block_id}")
    return json.loads(match.group(1).strip())


def has_block(text, block_id):
    pattern = re.compile(
        rf'<script\s+type=["\']application/json["\']\s+id=["\']{re.escape(block_id)}["\']\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    return bool(pattern.search(text))


def _require_fields(obj, fields, label):
    missing = [field for field in fields if field not in obj]
    if missing:
        raise AssertionError(f"{label} missing required field(s): {', '.join(missing)}")


def _ensure_unique(values, label):
    seen = set()
    duplicates = []
    for value in values:
        if value in seen:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        raise AssertionError(f"{label} contains duplicate id(s): {', '.join(sorted(set(duplicates)))}")


def validate_process_loop(text, required=False):
    present = {block_id: has_block(text, block_id) for block_id in STRICT_BLOCK_IDS}
    enabled = required or any(present.values())
    if not enabled:
        return {
            "enabled": False,
            "blocksPresent": present,
        }

    missing = [block_id for block_id, ok in present.items() if not ok]
    if missing:
        raise AssertionError(f"missing strict closure block(s): {', '.join(missing)}")

    critique = extract_block(text, "critique-loop-log")
    findings = extract_block(text, "source-review-findings")
    followups = extract_block(text, "followup-query-matrix")
    closures = extract_block(text, "p0p1-closure-matrix")

    _require_fields(critique, ["strictLoopRequired", "rounds"], "critique-loop-log")
    if required and not critique["strictLoopRequired"]:
        raise AssertionError("critique-loop-log.strictLoopRequired must be true for high-impact reports")
    if not isinstance(critique["rounds"], list) or not critique["rounds"]:
        raise AssertionError("critique-loop-log.rounds must be a non-empty array")

    if not isinstance(findings, list):
        raise AssertionError("source-review-findings must be an array")
    if not isinstance(followups, list):
        raise AssertionError("followup-query-matrix must be an array")
    if not isinstance(closures, list):
        raise AssertionError("p0p1-closure-matrix must be an array")

    for idx, round_item in enumerate(critique["rounds"]):
        _require_fields(
            round_item,
            ["roundId", "purpose", "sourceIds", "reviewFindingIds", "generatedFollowupQueryIds", "stopDecision"],
            f"critique-loop-log.rounds[{idx}]",
        )
        if not isinstance(round_item["sourceIds"], list) or not round_item["sourceIds"]:
            raise AssertionError(f"critique-loop-log.rounds[{idx}].sourceIds must be a non-empty array")
        if not isinstance(round_item["reviewFindingIds"], list):
            raise AssertionError(f"critique-loop-log.rounds[{idx}].reviewFindingIds must be an array")
        if not isinstance(round_item["generatedFollowupQueryIds"], list):
            raise AssertionError(
                f"critique-loop-log.rounds[{idx}].generatedFollowupQueryIds must be an array"
            )

    finding_map = {}
    for idx, finding in enumerate(findings):
        _require_fields(
            finding,
            ["id", "severity", "sourceIds", "weakness", "blockedObjects", "requiredEvidenceTypes"],
            f"source-review-findings[{idx}]",
        )
        if finding["severity"] not in {"P0", "P1", "P2", "P3"}:
            raise AssertionError(f"source-review-findings[{idx}] has invalid severity: {finding['severity']}")
        if not isinstance(finding["sourceIds"], list) or not finding["sourceIds"]:
            raise AssertionError(f"source-review-findings[{idx}].sourceIds must be a non-empty array")
        finding_map[finding["id"]] = finding

    _ensure_unique(finding_map.keys(), "source-review-findings")

    followup_map = {}
    for idx, followup in enumerate(followups):
        _require_fields(
            followup,
            ["queryId", "findingIds", "query", "preferredSourceTiers"],
            f"followup-query-matrix[{idx}]",
        )
        if not isinstance(followup["findingIds"], list) or not followup["findingIds"]:
            raise AssertionError(f"followup-query-matrix[{idx}].findingIds must be a non-empty array")
        if not isinstance(followup["preferredSourceTiers"], list) or not followup["preferredSourceTiers"]:
            raise AssertionError(
                f"followup-query-matrix[{idx}].preferredSourceTiers must be a non-empty array"
            )
        followup_map[followup["queryId"]] = followup
        for finding_id in followup["findingIds"]:
            if finding_id not in finding_map:
                raise AssertionError(
                    f"followup-query-matrix[{idx}] references unknown finding id: {finding_id}"
                )

    _ensure_unique(followup_map.keys(), "followup-query-matrix")

    closure_map = {}
    for idx, closure in enumerate(closures):
        _require_fields(
            closure,
            ["findingId", "status", "closingEvidenceIds", "closureReason"],
            f"p0p1-closure-matrix[{idx}]",
        )
        if closure["status"] not in {"closed", "blocked", "accepted-risk"}:
            raise AssertionError(f"p0p1-closure-matrix[{idx}] has invalid status: {closure['status']}")
        if not isinstance(closure["closingEvidenceIds"], list):
            raise AssertionError(f"p0p1-closure-matrix[{idx}].closingEvidenceIds must be an array")
        if not closure["closureReason"].strip():
            raise AssertionError(f"p0p1-closure-matrix[{idx}].closureReason must not be empty")
        closure_map[closure["findingId"]] = closure

    _ensure_unique(closure_map.keys(), "p0p1-closure-matrix")

    p0p1_findings = [finding for finding in findings if finding["severity"] in {"P0", "P1"}]
    for finding in p0p1_findings:
        closure = closure_map.get(finding["id"])
        if closure is None:
            raise AssertionError(f"missing closure entry for P0/P1 finding: {finding['id']}")
        if closure["status"] == "closed" and not closure["closingEvidenceIds"]:
            raise AssertionError(f"closed finding {finding['id']} must have closingEvidenceIds")
        if closure["status"] not in {"blocked", "accepted-risk"}:
            matched = [item for item in followups if finding["id"] in item["findingIds"]]
            if not matched:
                raise AssertionError(
                    f"finding {finding['id']} requires at least one follow-up query before closure"
                )

    for idx, round_item in enumerate(critique["rounds"]):
        for finding_id in round_item["reviewFindingIds"]:
            if finding_id not in finding_map:
                raise AssertionError(
                    f"critique-loop-log.rounds[{idx}] references unknown finding id: {finding_id}"
                )
        for query_id in round_item["generatedFollowupQueryIds"]:
            if query_id not in followup_map:
                raise AssertionError(
                    f"critique-loop-log.rounds[{idx}] references unknown follow-up query id: {query_id}"
                )

    return {
        "enabled": True,
        "blocksPresent": present,
        "findings": len(findings),
        "followups": len(followups),
        "closures": len(closures),
    }
