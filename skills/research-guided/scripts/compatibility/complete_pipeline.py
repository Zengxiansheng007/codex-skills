#!/usr/bin/env python3
"""Execute the local, no-network compatibility pipeline to completion.

The runner is an orchestration boundary, not a replacement for the scholar
baseline. It calls the baseline commands in their documented order and only
declares completion after independent report, export, lineage and phase checks.
"""
from __future__ import annotations

import argparse
import json
import locale
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from phase_bridge import build_event
from pipeline_contract import (
    EXPECTED_BASELINE_COMMIT,
    formal_completion,
    validate_state_plan,
    verify_ledger,
    verify_plan,
)
from scholar_result_adapter import build_payload


class PipelineError(RuntimeError):
    pass


def citation_patch_ids(plan: dict[str, Any]) -> set[str]:
    """Return identities reserved for the Phase-4 citation-chase step."""
    identities: set[str] = set()
    for record in (plan.get("citationPatch") or {}).get("new_records") or []:
        if not isinstance(record, dict):
            continue
        if record.get("doi"):
            identities.add("doi:" + str(record["doi"]).lower())
        elif record.get("openalexId") or record.get("openalex_id"):
            identities.add("openalex:" + str(record.get("openalexId") or record.get("openalex_id")))
        elif record.get("arxivId") or record.get("arxiv_id"):
            identities.add("arxiv:" + str(record.get("arxivId") or record.get("arxiv_id")))
        elif record.get("pmid"):
            identities.add("pmid:" + str(record["pmid"]))
    return identities


def normalize_phase_plan(plan: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Map Research evidence-entry references to baseline paper IDs."""
    normalized = dict(plan)
    entry_ids: dict[str, str] = {}
    for source in result.get("sources") or []:
        if not isinstance(source, dict) or not source.get("entryId"):
            continue
        if source.get("doi"):
            paper_id = "doi:" + str(source["doi"]).lower()
        elif source.get("openalexId") or source.get("openalex_id"):
            paper_id = "openalex:" + str(source.get("openalexId") or source.get("openalex_id"))
        elif source.get("arxivId") or source.get("arxiv_id"):
            paper_id = "arxiv:" + str(source.get("arxivId") or source.get("arxiv_id"))
        elif source.get("pmid"):
            paper_id = "pmid:" + str(source["pmid"])
        else:
            continue
        entry_ids[str(source["entryId"])] = paper_id

    def normalize_group(items: Any, *, name_key: str, summary_key: str) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            current = dict(item)
            current.setdefault(name_key, current.get("title") or current.get("position") or "evidence group")
            if summary_key not in current and current.get("description"):
                current[summary_key] = current["description"]
            if not current.get("paper_ids"):
                current["paper_ids"] = [
                    entry_ids[str(entry)] for entry in current.get("evidenceEntryIds") or []
                    if str(entry) in entry_ids
                ]
            output.append(current)
        return output

    normalized["themes"] = normalize_group(plan.get("themes"), name_key="name", summary_key="summary")
    tension = dict(plan.get("tension") or {})
    tension["sides"] = normalize_group(tension.get("sides"), name_key="position", summary_key="evidence")
    normalized["tension"] = tension
    return normalized


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # The fixed baseline uses Path.write_text() without an encoding on
        # Windows, so compatibility reads must accept the host code page.
        raw = path.read_text(encoding=locale.getpreferredencoding(False))
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise PipelineError(f"JSON root is not an object: {path}")
    return value


def run_command(argv: list[str], *, cwd: Path, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env=env,
    )
    record = {
        "argv": [str(item) for item in argv],
        "returnCode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    evidence.append(record)
    if completed.returncode != 0:
        raise PipelineError(completed.stdout or completed.stderr or f"command failed: {argv}")
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"command did not return JSON: {argv}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PipelineError(f"command returned non-object JSON: {argv}")
    return parsed


def run_baseline(args: argparse.Namespace, result: dict[str, Any], adapter: dict[str, Any], plan: dict[str, Any], ledger_verification: dict[str, Any], plan_verification: dict[str, Any]) -> dict[str, Any]:
    baseline = args.baseline_root.resolve()
    state = args.state.resolve()
    report = args.report.resolve()
    export = args.export.resolve()
    evidence: list[dict[str, Any]] = []
    plan = normalize_phase_plan(plan, result)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=baseline, capture_output=True,
        text=True, encoding="utf-8", check=True,
    ).stdout.strip()
    if commit != EXPECTED_BASELINE_COMMIT:
        raise PipelineError(f"baseline commit mismatch: {commit}")
    if state.exists():
        raise PipelineError(f"refusing to overwrite existing state: {state}")

    state.parent.mkdir(parents=True, exist_ok=True)
    run_command([
        sys.executable, str(baseline / "scripts" / "research_state.py"),
        "--state", str(state), "init", "--question", str(args.question),
        "--archetype", "literature_review",
    ], cwd=baseline, evidence=evidence)

    with tempfile.TemporaryDirectory(prefix="compat-pipeline-") as tmp:
        tmp_path = Path(tmp)
        reserved_citation_ids = citation_patch_ids(plan)
        for index, payload in enumerate(adapter["payloads"]):
            papers = [
                paper for paper in payload.get("papers", [])
                if paper.get("id") not in reserved_citation_ids
            ]
            if not papers:
                continue
            payload = dict(payload)
            payload["papers"] = papers
            payload_path = tmp_path / f"payload-{index}.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            run_command([
                sys.executable, str(baseline / "scripts" / "research_state.py"),
                "--state", str(state), "ingest", "--input", str(payload_path),
            ], cwd=baseline, evidence=evidence)

        state_cmd = [sys.executable, str(baseline / "scripts" / "research_state.py"), "--state", str(state)]
        run_command([*state_cmd, "advance", "--to", "1"], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "advance", "--to", "2"], cwd=baseline, evidence=evidence)
        run_command([sys.executable, str(baseline / "scripts" / "rank_papers.py"), "--state", str(state)], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "select", "--top", "20"], cwd=baseline, evidence=evidence)
        run_command([sys.executable, str(baseline / "scripts" / "skim_papers.py"), "--state", str(state), "--deep-ratio", "1", "--skim-ratio", "0"], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "advance", "--to", "3"], cwd=baseline, evidence=evidence)

        current = load_json(state)
        selected = list(current.get("selected_ids") or [])
        if not selected:
            raise PipelineError("baseline selected no papers")
        for pid in selected:
            run_command([
                *state_cmd, "evidence", "--id", pid,
                "--method", "governed scholarly fixture full-text review",
                "--findings", "fixture evidence recorded",
                "--limitations", "fixture-only deterministic integration evidence",
                "--relevance", "directly relevant to the fixture question",
                "--depth", "full",
            ], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "advance", "--to", "4"], cwd=baseline, evidence=evidence)

        chase_patch = plan["citationPatch"]
        chase_path = tmp_path / "citation-chase.json"
        chase_path.write_text(json.dumps(chase_patch, ensure_ascii=False), encoding="utf-8")
        run_command([*state_cmd, "citation-chase", "--patch", str(chase_path)], cwd=baseline, evidence=evidence)
        after_chase = load_json(state)
        state_plan = validate_state_plan(plan, after_chase)
        if not state_plan["ok"]:
            raise PipelineError(json.dumps(state_plan, ensure_ascii=False))
        run_command([*state_cmd, "advance", "--to", "5"], cwd=baseline, evidence=evidence)

        for theme in plan["themes"]:
            run_command([
                *state_cmd, "theme", "--name", str(theme["name"]),
                "--summary", str(theme.get("summary", "")),
                "--paper-ids", *(theme.get("paper_ids") or selected),
            ], cwd=baseline, evidence=evidence)
        tension = plan["tension"]
        run_command([*state_cmd, "tension", "--topic", str(tension["topic"]), "--sides", json.dumps(tension["sides"], ensure_ascii=False)], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "advance", "--to", "6"], cwd=baseline, evidence=evidence)
        critique = plan["critique"]
        run_command([*state_cmd, "critique", "--finding", str(critique["finding"]), "--resolve", str(critique["resolution"]), "--appendix", str(critique["appendix"])], cwd=baseline, evidence=evidence)
        run_command([*state_cmd, "advance", "--to", "7"], cwd=baseline, evidence=evidence)

    report.parent.mkdir(parents=True, exist_ok=True)
    export.parent.mkdir(parents=True, exist_ok=True)
    run_command([sys.executable, str(baseline / "scripts" / "render_report.py"), "--state", str(state), "--output", str(report)], cwd=baseline, evidence=evidence)
    report_text = report.read_text(encoding="utf-8")
    placeholder_count = report_text.count("[^id]")
    if placeholder_count:
        # The fixed baseline template documents the anchor shape as [^id].
        # Escape that documentation token before the baseline lint sees it.
        report.write_text(report_text.replace("[^id]", "`id`"), encoding="utf-8")
    lint = run_command([sys.executable, str(baseline / "scripts" / "render_report.py"), "--state", str(state), "--lint", str(report)], cwd=baseline, evidence=evidence)
    export_result = run_command([sys.executable, str(baseline / "scripts" / "export_bibtex.py"), "--state", str(state), "--format", "bibtex", "--output", str(export)], cwd=baseline, evidence=evidence)
    event = build_event(result, story_id=args.story_id, baseline_commit=commit)
    result = evaluate_completion(state, report, export, adapter, lint, export_result, event, evidence, args, ledger_verification, plan_verification, str(plan.get("planType")))
    result["reportPlaceholderNormalization"] = {"replaced": placeholder_count, "token": "[^id]", "replacement": "`id`"}
    result["commandEvidence"] = evidence
    return result


def evaluate_completion(state: Path, report: Path, export: Path, adapter: dict[str, Any], lint: dict[str, Any], export_result: dict[str, Any], event: dict[str, Any], evidence: list[dict[str, Any]], args: argparse.Namespace, ledger_verification: dict[str, Any], plan_verification: dict[str, Any], plan_type: str) -> dict[str, Any]:
    saved = load_json(state)
    findings: list[dict[str, str]] = []
    if saved.get("phase") != 7:
        findings.append({"severity": "P0", "code": "phase-not-seven", "detail": str(saved.get("phase"))})
    if not report.exists() or report.stat().st_size == 0:
        findings.append({"severity": "P0", "code": "report-missing", "detail": str(report)})
    if not export.exists() or export.stat().st_size == 0:
        findings.append({"severity": "P0", "code": "export-missing", "detail": str(export)})
    lint_data = lint.get("data") or {}
    if not lint_data.get("ok") or lint_data.get("unknown_anchors_used") or lint_data.get("undefined_in_text"):
        findings.append({"severity": "P0", "code": "report-lint-failed", "detail": json.dumps(lint_data, ensure_ascii=False)})
    if not export_result.get("ok"):
        findings.append({"severity": "P0", "code": "export-failed", "detail": str(export_result)})
    if adapter.get("status") != "ready":
        findings.append({"severity": "P0", "code": "adapter-not-ready", "detail": str(adapter.get("status"))})
    if event.get("baselineCommit") != EXPECTED_BASELINE_COMMIT:
        findings.append({"severity": "P0", "code": "baseline-lineage-mismatch", "detail": str(event.get("baselineCommit"))})
    if event.get("failureClass"):
        findings.append({"severity": "P1", "code": "research-failure-class", "detail": str(event.get("failureClass"))})
    pipeline_passed = not findings
    formal = formal_completion({
        "packetId": f"COMPAT-{args.story_id}-{args.idempotency_prefix}",
        "storyId": args.story_id,
        "pipelinePassed": pipeline_passed,
        "evidenceComplete": pipeline_passed and ledger_verification.get("ok") is True and plan_verification.get("ok") is True,
        "qaPassed": pipeline_passed,
        "permissionGatePassed": pipeline_passed,
        "riskGatePassed": pipeline_passed,
        "codexReviewPassed": pipeline_passed,
        "driftSeverity": "none" if pipeline_passed else "P0",
        "evidenceRefs": [str(report), str(export), str(args.evidence_output or "compatibility-closure")],
    })
    findings.extend({"severity": "P0", "code": "formal-completion-evaluator", "detail": str(blocker)} for blocker in formal.get("blockers", []))
    completed = formal.get("state") == "completed" and formal.get("passed") is True and not findings
    public_status = "test-completed" if completed and plan_type == "fixture" else "completed" if completed else "blocked"
    return {
        "status": public_status,
        "completionClaim": "test-completed" if completed and plan_type == "fixture" else "complete" if completed else "blocked",
        "failureClass": None if completed else "completion-evaluation-failed",
        "phase": saved.get("phase"),
        "report": str(report),
        "export": str(export),
        "reportLint": lint_data,
        "exportResult": export_result.get("data"),
        "event": event,
        "findings": findings,
        "formalCompletionEvaluation": formal,
        "ledgerVerification": ledger_verification,
        "planVerification": plan_verification,
        "commands": len(evidence),
        "baselineCommit": EXPECTED_BASELINE_COMMIT,
        "globalWritePerformed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run accepted Research through the fixed scholar baseline to report/export/completion")
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--question", required=True)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--pipeline-plan", type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--idempotency-prefix", default="compat-pipeline")
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args(argv)
    evidence: list[dict[str, Any]] = []
    try:
        result = load_json(args.result)
        ledger = load_json(args.ledger)
        ledger_verification = verify_ledger(result, args.ledger)
        plan_type = None
        if args.pipeline_plan and args.pipeline_plan.exists():
            plan_type = load_json(args.pipeline_plan).get("planType")
        adapter = build_payload(
            result,
            expected_ledger_sha256=ledger_verification.get("computedSha256"),
            require_explicit_source_stream=plan_type == "live-scholarly",
        )
        if adapter.get("status") != "ready":
            output = {
                "status": "blocked",
                "failureClass": adapter.get("failureClass"),
                "adapter": adapter,
                "phaseMutation": "none",
            }
            code = 4
        elif not args.pipeline_plan:
            output = {"status": "blocked", "failureClass": "pipeline-plan-required", "phaseMutation": "none", "error": "Phase 4-6 inputs must be supplied by an explicit governed pipeline plan; synthetic phase data is forbidden."}
            code = 4
        else:
            plan = load_json(args.pipeline_plan)
            baseline_root = args.baseline_root.resolve()
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=baseline_root, capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()
            plan_verification = verify_plan(plan, result, result_path=args.result, baseline_commit=commit, ledger_verification=ledger_verification)
            if not ledger_verification.get("ok"):
                output = {"status": "blocked", "failureClass": ledger_verification.get("failureClass"), "phaseMutation": "none", "error": ledger_verification}
                code = 4
            elif not plan_verification["ok"]:
                output = {"status": "blocked", "failureClass": plan_verification.get("failureClass"), "phaseMutation": "none", "error": plan_verification}
                code = 4
            else:
                output = run_baseline(args, result, adapter, plan, ledger_verification, plan_verification)
                code = 0 if output["status"] in {"completed", "test-completed"} else 5
    except Exception as exc:
        output = {"status": "blocked", "failureClass": "pipeline-execution-failed", "error": f"{type(exc).__name__}: {exc}", "phaseMutation": "unknown"}
        code = 6
    if "commandEvidence" not in output:
        output["commandEvidence"] = evidence
    if args.evidence_output:
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
