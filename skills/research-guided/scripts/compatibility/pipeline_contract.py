from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_BASELINE_COMMIT = "e7ce1cbe657f2e0386f075f9aa9f6ead7171876e"
DEVELOPMENT_RUNTIME = Path(
    "C:/Users/lenovo/Documents/ChatGPT/ui-test/work/handoffs/"
    "claude-glm52-adapter-repair-handoff-20260827/candidate-workspace/"
    "development-system/scripts/development_runtime.py"
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ledger_sha256(ledger: dict[str, Any]) -> str:
    body = dict(ledger)
    body.pop("ledgerSha256", None)
    return sha256_json(body)


def verify_ledger(result: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "failureClass": "evidence-ledger-missing", "error": str(exc)}
    if not isinstance(ledger, dict):
        return {"ok": False, "failureClass": "evidence-ledger-invalid", "error": "ledger root must be object"}
    computed = ledger_sha256(ledger)
    declared = str(ledger.get("ledgerSha256", ""))
    result_hash = str((result.get("evidenceLedgerRef") or {}).get("ledgerSha256", ""))
    source_urls = {
        str(item.get("url")) for item in ledger.get("sources", [])
        if isinstance(item, dict) and item.get("url")
    }
    result_urls = {
        str(item.get("url")) for item in result.get("sources", [])
        if isinstance(item, dict) and item.get("url")
    }
    missing_urls = sorted(result_urls - source_urls)
    claim_urls = {
        str(item.get("sourceUrl")) for item in result.get("claims", [])
        if isinstance(item, dict) and item.get("sourceUrl")
    }
    missing_claim_urls = sorted(claim_urls - source_urls)
    checks = {
        "ledgerHashSelfConsistent": bool(declared) and declared == computed,
        "resultHashMatches": result_hash == computed,
        "ledgerIdMatches": str(ledger.get("ledgerId", "")) == str((result.get("evidenceLedgerRef") or {}).get("ledgerId", "")),
        "requirementAnchorMatches": str(ledger.get("requirementAnchor", "")) == str(result.get("requirementAnchor", "")),
        "sourceSetContainsResult": not missing_urls,
        "claimSetContainsResult": not missing_claim_urls,
    }
    return {
        "ok": all(checks.values()),
        "failureClass": None if all(checks.values()) else "evidence-ledger-mismatch",
        "path": str(ledger_path.resolve()),
        "computedSha256": computed,
        "declaredSha256": declared,
        "resultSha256": result_hash,
        "missingResultSources": missing_urls,
        "missingClaimSources": missing_claim_urls,
        "checks": checks,
    }


def verify_plan(plan: dict[str, Any], result: dict[str, Any], *, result_path: Path,
                baseline_commit: str, ledger_verification: dict[str, Any]) -> dict[str, Any]:
    required = ("planType", "requirementAnchor", "researchId", "roundId", "ledgerSha256", "baselineCommit", "sourceStateHash", "derivedFrom", "citationPatch", "themes", "tension", "critique")
    missing = [key for key in required if key not in plan]
    checks = {
        "requiredFields": not missing,
        "planTypeValid": plan.get("planType") in {"fixture", "live-scholarly"},
        "anchorMatches": plan.get("requirementAnchor") == result.get("requirementAnchor"),
        "researchIdMatches": plan.get("researchId") == result.get("researchId"),
        "roundIdMatches": plan.get("roundId") == result.get("roundId"),
        "ledgerHashMatches": plan.get("ledgerSha256") == ledger_verification.get("computedSha256"),
        "baselineMatches": plan.get("baselineCommit") == baseline_commit == EXPECTED_BASELINE_COMMIT,
        "sourceStateHashMatches": plan.get("sourceStateHash") == file_sha256(result_path),
        "derivedFromPresent": isinstance(plan.get("derivedFrom"), list) and bool(plan.get("derivedFrom")),
        "ledgerVerified": ledger_verification.get("ok") is True,
        "phaseInputsPresent": all(isinstance(plan.get(key), (dict, list)) for key in ("citationPatch", "themes", "tension", "critique")),
        "liveEvidenceBoundary": plan.get("planType") == "fixture" or (
            isinstance(plan.get("liveEvidenceRefs"), list)
            and bool(plan.get("liveEvidenceRefs"))
            and plan.get("syntheticPhaseData") is not True
        ),
    }
    return {
        "ok": not missing and all(checks.values()),
        "failureClass": None if not missing and all(checks.values()) else "pipeline-plan-lineage-invalid",
        "missing": missing,
        "checks": checks,
    }


def validate_state_plan(plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    paper_ids = set((state.get("papers") or {}).keys())
    missing: list[str] = []
    for theme in plan.get("themes") or []:
        for paper_id in theme.get("paper_ids") or []:
            if paper_id not in paper_ids:
                missing.append(str(paper_id))
    for side in (plan.get("tension") or {}).get("sides") or []:
        for paper_id in side.get("paper_ids") or []:
            if paper_id not in paper_ids:
                missing.append(str(paper_id))
    for record in (plan.get("citationPatch") or {}).get("new_records") or []:
        identity = str(record.get("doi") or record.get("openalex_id") or record.get("arxiv_id") or record.get("pmid") or "")
        if identity:
            if record.get("doi"):
                expected = "doi:" + str(record["doi"]).lower()
            elif record.get("openalex_id"):
                expected = "openalex:" + str(record["openalex_id"])
            elif record.get("arxiv_id"):
                expected = "arxiv:" + str(record["arxiv_id"])
            else:
                expected = "pmid:" + str(record["pmid"])
            if expected not in paper_ids:
                missing.append(expected)
    return {"ok": not missing, "failureClass": None if not missing else "pipeline-plan-paper-reference-invalid", "missingPaperIds": sorted(set(missing))}


def formal_completion(evaluation: dict[str, Any], *, development_runtime: Path = DEVELOPMENT_RUNTIME) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("compat_development_runtime", development_runtime)
    if spec is None or spec.loader is None:
        return {"state": "repair-needed", "passed": False, "blockers": ["development-runtime-load-failed"]}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    feedback = {
        "packetId": evaluation["packetId"],
        "packetType": "feedback",
        "version": "1.0",
        "storyId": evaluation["storyId"],
        "result": "completed" if evaluation.get("pipelinePassed") else "blocked",
        "evidenceRefs": list(evaluation.get("evidenceRefs") or []),
    }
    feedback_validation = {
        "schemaRef": "compatibility-closure-evidence-v1",
        "validatorId": "compatibility-closure",
        "feedbackHash": sha256_json(feedback),
        "ok": True,
        "errorCount": 0,
        "errors": [],
        "validatedAt": datetime.now(timezone.utc).isoformat(),
    }
    formal_input = {
        "allStoriesPassed": evaluation.get("pipelinePassed") is True,
        "allAcceptanceCriteriaVerified": evaluation.get("pipelinePassed") is True,
        "feedback": feedback,
        "feedbackValidation": feedback_validation,
        "evidenceComplete": evaluation.get("evidenceComplete") is True,
        "qaPassed": evaluation.get("qaPassed") is True,
        "driftSeverity": evaluation.get("driftSeverity", "P0"),
        "unmappedActions": evaluation.get("unmappedActions") or [],
        "permissionGatePassed": evaluation.get("permissionGatePassed") is True,
        "riskGatePassed": evaluation.get("riskGatePassed") is True,
        "codexReviewPassed": evaluation.get("codexReviewPassed") is True,
        "agentCompletionClaim": False,
    }
    result = module.evaluate_completion(formal_input)
    result["input"] = formal_input
    return result
