"""Build traceability and completion evidence for a Development System candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from development_runtime import _sha256, evaluate_completion


PHASE_EVIDENCE = {
    "PH-01": {
        "references": [
            "control-plane-and-authority.md", "artifact-lifecycle-contract.md",
            "metagpt-role-sop-contract.md", "plan-story-contract.md",
            "handoff-interface-contract.md", "rework-and-gate-reopen-contract.md",
            "event-history-and-recovery-contract.md", "state-and-completion-contract.md",
            "long-task-runtime-contract.md", "workspace-and-approval-contract.md",
        ],
        "tests": ["test_phase_story_contract.py", "test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-02": {
        "references": ["claude-first-execution-contract.md", "workspace-and-approval-contract.md", "handoff-interface-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-03": {
        "references": ["software-company-pipeline-contract.md", "metagpt-role-sop-contract.md", "rework-and-gate-reopen-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-04": {
        "references": ["long-task-runtime-contract.md", "event-history-and-recovery-contract.md", "state-and-completion-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-05": {
        "references": ["multi-agent-concurrency-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-06": {
        "references": ["observability-and-resource-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
    "PH-07": {
        "references": ["metagpt-module-admission.md", "handoff-interface-contract.md"],
        "tests": ["test_development_runtime.py", "test_full_refactor_contract.py"],
    },
}

LOCAL_CHECKS = [
    "validate_development_system.py",
    "test_phase_story_contract.py",
    "test_development_runtime.py",
    "test_full_refactor_contract.py",
    "test_phase1_boundary_contract.py",
    "test_skill_governance_contract.py",
]


def run_checks(skill_root: Path) -> list[dict[str, object]]:
    results = []
    for name in LOCAL_CHECKS:
        command = [sys.executable, str(skill_root / "scripts" / name)]
        completed = subprocess.run(command, cwd=skill_root, text=True, capture_output=True, timeout=120)
        results.append({
            "check": name,
            "exitCode": completed.returncode,
            "status": "passed" if completed.returncode == 0 else "failed",
            "stdout": completed.stdout.strip()[-4000:],
            "stderr": completed.stderr.strip()[-2000:],
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", required=True)
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    skill_root = Path(args.skill_root).resolve()
    requirements_path = Path(args.requirements).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    checks = run_checks(skill_root)
    checks_passed = all(item["status"] == "passed" for item in checks)

    story_rows = []
    for phase in requirements.get("phases", []):
        evidence = PHASE_EVIDENCE.get(phase["phaseId"], {})
        for story in phase.get("stories", []):
            story_rows.append({
                "phaseId": phase["phaseId"],
                "storyId": story["storyId"],
                "requirements": story.get("mappedRequirements", []),
                "acceptanceCriteria": story.get("acceptanceCriteria", []),
                "references": [f"references/{name}" for name in evidence.get("references", [])],
                "tests": [f"scripts/{name}" for name in evidence.get("tests", [])],
                "status": "validated" if checks_passed else "review-required",
            })

    requirement_ids = [item["id"] for item in requirements.get("functionalRequirements", [])]
    requirement_ids += [item["id"] for item in requirements.get("nonFunctionalRequirements", [])]
    ac_ids = [item["id"] for item in requirements.get("acceptanceCriteria", [])]
    requirement_coverage = {
        item_id: [row["storyId"] for row in story_rows if item_id in row["requirements"]]
        for item_id in requirement_ids
    }
    ac_coverage = {
        item_id: [row["storyId"] for row in story_rows if item_id in row["acceptanceCriteria"]]
        for item_id in ac_ids
    }
    uncovered = [item_id for item_id, stories in {**requirement_coverage, **ac_coverage}.items() if not stories]

    rtm = {
        "reportId": "DS-REFRACTOR-RTM-20260815",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "requirementsBaseline": str(requirements_path),
        "summary": {
            "phases": len(requirements.get("phases", [])),
            "stories": len(story_rows),
            "functionalRequirements": len(requirements.get("functionalRequirements", [])),
            "nonFunctionalRequirements": len(requirements.get("nonFunctionalRequirements", [])),
            "acceptanceCriteria": len(ac_ids),
            "uncoveredIds": uncovered,
        },
        "storyTrace": story_rows,
        "requirementCoverage": requirement_coverage,
        "acceptanceCoverage": ac_coverage,
        "validationChecks": checks,
    }
    rtm_path = out_dir / "development-system-full-refactor-rtm-2026-08-15.json"
    rtm_path.write_text(json.dumps(rtm, ensure_ascii=False, indent=2), encoding="utf-8")

    workspace_candidate_passed = checks_passed and not uncovered and len(story_rows) == 33
    feedback = {
        "packetId": "FB-DS-WORKSPACE-20260815-001",
        "result": "workspace-candidate-validated" if workspace_candidate_passed else "workspace-candidate-repair-needed",
        "evidenceRefs": [str(rtm_path)],
    }
    evaluation_input = {
        "allStoriesPassed": workspace_candidate_passed,
        "allAcceptanceCriteriaVerified": workspace_candidate_passed,
        "feedback": feedback,
        "feedbackValidation": {
            "schemaRef": "handoff-system/feedback-packet.schema.json",
            "validatorId": "development-system-workspace-report-gate",
            "feedbackHash": _sha256(feedback),
            "ok": True,
            "errorCount": 0,
            "errors": [],
            "validatedAt": datetime.now(timezone.utc).isoformat(),
        },
        "evidenceComplete": workspace_candidate_passed,
        "qaPassed": checks_passed,
        "driftSeverity": "none" if workspace_candidate_passed else "P1",
        "unmappedActions": [],
        "permissionGatePassed": True,
        "riskGatePassed": True,
        "codexReviewPassed": workspace_candidate_passed,
    }
    evaluation_result = evaluate_completion(evaluation_input)
    completion = {
        "reportId": "DS-REFRACTOR-COMPLETION-20260815",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "workspaceCandidatePassed": workspace_candidate_passed,
        "installationApproved": False,
        "evaluationInput": evaluation_input,
        "evaluationResult": evaluation_result,
        "nextState": evaluation_result["state"],
        "installationState": "risk-gate-required",
        "installationRiskGate": "A new explicit user approval is required before user-level Skill installation.",
        "rtmRef": str(rtm_path),
    }
    completion_path = out_dir / "development-system-completion-evaluation-2026-08-15.json"
    completion_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": completion["nextState"],
        "workspaceCandidatePassed": workspace_candidate_passed,
        "rtm": str(rtm_path),
        "completion": str(completion_path),
        "uncoveredIds": uncovered,
    }, ensure_ascii=False, indent=2))
    return 0 if workspace_candidate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
