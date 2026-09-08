from __future__ import annotations

from typing import Any


def build_event(result: dict[str, Any], *, story_id: str, baseline_commit: str) -> dict[str, Any]:
    """Build an audit event without mutating scholar phase state."""
    ledger = result.get("evidenceLedgerRef") or {}
    return {
        "eventType": "governed-research-observed",
        "storyId": story_id,
        "requirementAnchor": result.get("requirementAnchor"),
        "researchId": result.get("researchId"),
        "roundId": result.get("roundId"),
        "reinforcementRounds": result.get("reinforcementRounds", 0),
        "completionClaim": result.get("completionClaim"),
        "failureClass": result.get("failureClass"),
        "baselineCommit": baseline_commit,
        "evidenceLedgerRef": {
            "ledgerId": ledger.get("ledgerId"),
            "ledgerSha256": ledger.get("ledgerSha256"),
        },
        "phaseMutation": "delegated-to-scholar-research_state-advance",
        "stateMutationAuthority": "scholar-research_state-only",
    }


def check_resume(checkpoint: dict[str, Any], *, story_id: str, requirement_anchor: str,
                 baseline_commit: str, ledger_sha256: str) -> dict[str, Any]:
    checks = {
        "story": checkpoint.get("storyId") == story_id,
        "requirementAnchor": checkpoint.get("requirementAnchor") == requirement_anchor,
        "baselineCommit": checkpoint.get("baselineCommit") == baseline_commit,
        "ledgerSha256": checkpoint.get("ledgerSha256") == ledger_sha256,
    }
    return {
        "resumeAllowed": all(checks.values()),
        "checks": checks,
        "failureClass": None if all(checks.values()) else "checkpoint-lineage-mismatch",
    }
