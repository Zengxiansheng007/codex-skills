"""Run Codex-owned PH-3 live slot commit and integration gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from git_worktree_runtime import (
    build_merge_candidate,
    create_integration_worktree,
    evaluate_observed_write_set,
    integrate_candidates,
    observed_changed_files,
    validate_merge_candidate,
)


def _load(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _save(path: str | Path, value: Any) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _git(repo: str | Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, shell=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _ensure_git_identity(worktree: str | Path) -> None:
    _git(worktree, ["config", "user.email", "clw-ph3@example.com"])
    _git(worktree, ["config", "user.name", "CLW PH-3 Codex"])


def _commit_declared_files(slot: dict[str, Any], story_id: str) -> dict[str, Any]:
    worktree = Path(slot["worktreePath"])
    _ensure_git_identity(worktree)
    for relative in slot["declaredWriteSet"]:
        add = _git(worktree, ["add", "--", relative])
        if add.returncode != 0:
            raise RuntimeError(f"git add failed for {relative}: {add.stderr}")
    commit = _git(worktree, ["commit", "-m", f"CLW PH3 live {story_id}"])
    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed for {story_id}: {commit.stderr or commit.stdout}")
    head = _git(worktree, ["rev-parse", "HEAD"])
    if head.returncode != 0:
        raise RuntimeError(f"git rev-parse failed for {story_id}: {head.stderr}")
    return {"head": head.stdout.strip(), "commitStdout": commit.stdout, "commitStderr": commit.stderr}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot-manifests", required=True)
    parser.add_argument("--live-a-dir", required=True)
    parser.add_argument("--live-b-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest = _load(args.slot_manifests)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    repo = manifest["repo"]
    approved_root = manifest["approvedRoot"]
    live_dirs = {
        "CLW-LIVE-STORY-A": Path(args.live_a_dir).resolve(),
        "CLW-LIVE-STORY-B": Path(args.live_b_dir).resolve(),
    }

    candidates: list[dict[str, Any]] = []
    slot_results: list[dict[str, Any]] = []
    for index, slot in enumerate(manifest["slots"], start=1):
        story_id = f"CLW-LIVE-STORY-{chr(64 + index)}"
        live_dir = live_dirs[story_id]
        post_live = _load(live_dir / "post-live-gate.json")
        feedback = _load(live_dir / "feedback.json")
        live_manifest = _load(live_dir / "manifest.json")
        if post_live.get("status") != "accepted":
            raise RuntimeError(f"post-live gate did not accept {story_id}")
        observed_before = observed_changed_files(repo, slot["baselineCommit"], slot["worktreePath"])
        write_set = evaluate_observed_write_set(slot["declaredWriteSet"], observed_before)
        if not write_set["allowed"]:
            raise RuntimeError(f"observed write set rejected for {story_id}: {write_set}")
        commit_result = _commit_declared_files(slot, story_id)
        observed_after = observed_changed_files(repo, slot["baselineCommit"], slot["worktreePath"])
        diff = _git(slot["worktreePath"], ["diff", slot["baselineCommit"], "HEAD"])
        if diff.returncode != 0:
            raise RuntimeError(f"git diff failed for {story_id}: {diff.stderr}")
        feedback_validation = post_live["completionEvaluation"]["feedbackValidation"]
        slot_for_candidate = {
            **slot,
            "storyId": story_id,
            "mappedFrAc": ["FR-CLW3-001", "FR-CLW3-003", "FR-CLW3-007", "AC-CLW3-001", "AC-CLW3-003", "AC-CLW3-008"],
        }
        candidate = build_merge_candidate(
            slot_for_candidate,
            commit_result["head"],
            _sha256_text(diff.stdout),
            [{"command": "post-live-gate", "passed": True}, {"command": "observed-write-set", "passed": True}],
            [
                str(live_dir / "manifest.json"),
                str(live_dir / "feedback.json"),
                str(live_dir / "post-live-gate.json"),
                str(live_dir / "visible-window-capture.json"),
                str(live_dir / "visible-window-live.png"),
            ],
            feedback_validation=feedback_validation,
            observed_write_set=observed_after,
        )
        candidate_path = output_dir / f"{story_id.lower()}-candidate.json"
        _save(candidate_path, candidate)
        slot_results.append({
            "storyId": story_id,
            "postLiveStatus": post_live["status"],
            "feedbackStatus": feedback.get("nextStepRecommendation", {}).get("status"),
            "liveStatus": live_manifest.get("status"),
            "observedBeforeCommit": observed_before,
            "observedAfterCommit": observed_after,
            "writeSetDecision": write_set,
            "head": commit_result["head"],
            "candidatePath": str(candidate_path),
            "candidateValidation": validate_merge_candidate(candidate),
        })
        candidates.append(candidate)

    integration_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    integration = create_integration_worktree(
        repo,
        f"codex/live-integration-{integration_id}",
        str(Path(approved_root) / f"integration-{integration_id}"),
        "main",
        approved_root,
    )
    regression = [
        sys.executable,
        "-c",
        "from pathlib import Path; raise SystemExit(0 if Path('live/a.txt').exists() and Path('live/b.txt').exists() else 2)",
    ]
    integration_result = integrate_candidates(repo, integration, candidates, baseline_ref="main", regression_argv=regression)
    phase_completion = {
        "state": "completed" if integration_result.get("state") == "passed" and all(item["candidateValidation"]["valid"] for item in slot_results) else "repair-needed",
        "passed": integration_result.get("state") == "passed" and all(item["candidateValidation"]["valid"] for item in slot_results),
        "checks": {
            "postLiveAccepted": all(item["postLiveStatus"] == "accepted" for item in slot_results),
            "observedWriteSetAllowed": all(item["writeSetDecision"]["allowed"] for item in slot_results),
            "candidateValid": all(item["candidateValidation"]["valid"] for item in slot_results),
            "integrationPassed": integration_result.get("state") == "passed",
            "regressionPassed": integration_result.get("regression", {}).get("passed") is True,
        },
        "blockers": [],
    }
    if not phase_completion["passed"]:
        phase_completion["blockers"] = [key for key, value in phase_completion["checks"].items() if not value]
    result = {
        "status": "accepted" if phase_completion["passed"] else "review-required",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "slotResults": slot_results,
        "integrationResult": integration_result,
        "phaseCompletionEvaluation": phase_completion,
    }
    _save(output_dir / "clw-ph3-live-integration-result.json", result)
    print("CLW_PHASE3_LIVE_INTEGRATION_OK" if phase_completion["passed"] else "CLW_PHASE3_LIVE_INTEGRATION_REVIEW_REQUIRED")
    return 0 if phase_completion["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
