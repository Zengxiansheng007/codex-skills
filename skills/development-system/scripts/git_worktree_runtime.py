"""CLW PH-3 Windows Git worktree execution slot runtime.

This module implements **only** CLW-ST-301: repository preflight, unique
branch/worktree creation, slot identity/baseline manifest, status inspection
and dirty preserve semantics. It does **not** implement merge, force-reset,
branch deletion, network access, dependency installation or any Agent
completion authority.

Design invariants (see ``references/clw-phase3-isolated-concurrency-contract.md``
and ``references/multi-agent-concurrency-contract.md``):

- Every Git invocation uses a ``subprocess`` argv array with ``shell=False``.
  There is no ``shell=True`` path and no wildcard expansion.
- Branch creation is **fail-on-collision**. The runtime never uses
  ``git worktree add -B`` or ``git switch -B``. A pre-existing branch name
  fails closed with ``branch-collision``.
- Worktree failure fails closed. There is no automatic sandbox fallback.
- Dirty or failed worktrees are preserved as evidence. Only Codex may merge
  or delete governed worktrees; this module exposes no merge/delete API to
  an Agent.
- Worktree paths must be unique, non-shared and inside an approved root.
- The baseline branch is never moved by slot creation.

Trace: FR-CLW3-001, FR-CLW3-002, FR-CLW3-003, FR-CLW3-004,
AC-CLW3-001 through AC-CLW3-005.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Slot states. ``PRESERVED`` is a terminal evidence state: a preserved dirty
# worktree is not deleted and not re-used by another slot.
SLOT_STATE_READY = "ready"
SLOT_STATE_RUNNING = "running"
SLOT_STATE_REVIEW = "review"
SLOT_STATE_BLOCKED = "blocked"
SLOT_STATE_PASSED = "passed"
SLOT_STATE_FAILED = "failed"
SLOT_STATE_PRESERVED = "preserved"

SLOT_STATES = (
    SLOT_STATE_READY,
    SLOT_STATE_RUNNING,
    SLOT_STATE_REVIEW,
    SLOT_STATE_BLOCKED,
    SLOT_STATE_PASSED,
    SLOT_STATE_FAILED,
    SLOT_STATE_PRESERVED,
)


class SlotError(Exception):
    """Closed failure raised by the worktree runtime.

    Attributes:
        reason: a stable, machine-readable reason code (never the raw Git
            stderr).  Reason codes include ``branch-collision``,
            ``path-escape``, ``worktree-path-not-empty``,
            ``not-a-git-repository``, ``submodule-boundary``,
            ``baseline-ref-not-found``, ``worktree-add-failed`` and
            ``write-set-invalid``.
        git_rc: the redacted Git return code (int or None). The raw stderr is
            never persisted or printed by the caller.
    """

    def __init__(self, reason: str, git_rc: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.git_rc = git_rc


def _git(
    args: list[str],
    cwd: str | Path,
    *,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a Git command with an argv array and ``shell=False``.

    The caller is responsible for interpreting the return code. When
    ``check=True``, a non-zero return code raises ``SlotError`` with a stable
    reason code derived from the command; raw stderr is never surfaced.
    """
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
    )


def _git_version() -> str:
    """Return the Git version string, or 'unknown' if Git is unavailable."""
    try:
        result = _git(["--version"], cwd=os.getcwd())
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, FileNotFoundError):
        pass
    return "unknown"


def _resolve_inside(path: str | Path, root: str | Path) -> bool:
    """Return True if ``path`` resolves to a location inside ``root``."""
    try:
        candidate = Path(path).resolve()
        root_resolved = Path(root).resolve()
        candidate.relative_to(root_resolved)
        return True
    except (ValueError, OSError):
        return False


def _write_set_normalized(paths: list[str]) -> list[str]:
    """Normalize a declared write set (forward-slash, case-fold, de-duped)."""
    seen: list[str] = []
    for raw in paths or []:
        value = str(raw).strip().replace("\\", "/")
        if not value or "*" in value or value.startswith("../") or "/../" in value:
            continue
        value = value.rstrip("/").casefold()
        if value not in seen:
            seen.append(value)
    return seen


def preflight_repository(repo_path: str) -> dict[str, Any]:
    """FR-CLW3-001: repository preflight.

    Verifies:
    - ``git`` is invokable and reports a version.
    - ``repo_path`` is a Git repository (``.git`` exists or ``git rev-parse``
      succeeds).
    - The repository has no submodule boundary (``.gitmodules`` absent).

    Returns a dict with ``ok``, ``gitVersion``, ``isGit``,
    ``hasSubmodules`` and, on failure, ``reason``.
    """
    version = _git_version()
    result: dict[str, Any] = {
        "ok": False,
        "gitVersion": version,
        "isGit": False,
        "hasSubmodules": False,
        "reason": "",
    }
    repo = Path(repo_path)
    if not repo.exists() or not repo.is_dir():
        result["reason"] = "not-a-git-repository"
        return result
    # Detect submodule boundary before any further work.
    gitmodules = repo / ".gitmodules"
    if gitmodules.exists():
        result["hasSubmodules"] = True
        result["reason"] = "submodule-boundary-not-supported"
        return result
    rev_parse = _git(["rev-parse", "--is-inside-work-tree"], cwd=str(repo))
    if rev_parse.returncode != 0 or rev_parse.stdout.strip() != "true":
        result["reason"] = "not-a-git-repository"
        return result
    result["isGit"] = True
    result["ok"] = True
    return result


def create_slot(
    repo_path: str,
    slot_id: str,
    branch: str,
    worktree_path: str,
    baseline_ref: str,
    declared_write_set: list[str],
    approved_root: str,
) -> dict[str, Any]:
    """FR-CLW3-002 / AC-CLW3-001 / AC-CLW3-002: create an isolated slot.

    Steps:
    1. Validate the worktree path is inside the approved root (no escape).
    2. Validate the worktree path does not already exist or is non-empty.
    3. Validate the declared write set.
    4. Validate the baseline ref resolves.
    5. **Fail-on-collision**: if the branch already exists, fail closed.
    6. Create the worktree with ``git worktree add <path> <branch>`` (never
       ``-B``).
    7. Build and return the slot identity.

    Returns a slot dict with ``slotId``, ``branch``, ``worktreePath``,
    ``baselineRef``, ``baselineFingerprint``, ``workspaceFingerprint``,
    ``declaredWriteSet`` and ``state``.

    Raises ``SlotError`` on any failure; the worktree is never created on
    failure.
    """
    # Validate approved-root boundary.
    if not _resolve_inside(worktree_path, approved_root):
        raise SlotError("path-escape")
    worktree = Path(worktree_path)
    # Fail closed if the worktree path already exists (even as an empty
    # directory): a shared or reused path is never accepted. The contract
    # requires unique, isolated worktree paths.
    if worktree.exists():
        raise SlotError("worktree-path-not-empty")
    # Validate declared write set.
    normalized_ws = _write_set_normalized(declared_write_set)
    if not normalized_ws:
        raise SlotError("write-set-invalid")
    # Validate baseline ref.
    baseline_check = _git(["rev-parse", "--verify", baseline_ref], cwd=repo_path)
    if baseline_check.returncode != 0:
        raise SlotError("baseline-ref-not-found")
    baseline_commit = baseline_check.stdout.strip()
    baseline_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "baselineCommit": baseline_commit,
                "baselineRef": baseline_ref,
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    # Fail-on-collision: if the branch already exists, fail closed.
    branch_check = _git(["rev-parse", "--verify", branch], cwd=repo_path)
    if branch_check.returncode == 0:
        raise SlotError("branch-collision")
    # Create the worktree. We never use -B/--force.
    # Use an explicit branch creation: `git worktree add -b <branch> <path> <baseline>`
    add_cmd = [
        "worktree",
        "add",
        "-b",
        branch,
        str(worktree),
        baseline_ref,
    ]
    add_result = _git(add_cmd, cwd=repo_path)
    if add_result.returncode != 0:
        raise SlotError("worktree-add-failed", git_rc=add_result.returncode)
    # Compute workspace fingerprint: hash of slotId + branch + worktree path.
    workspace_fp = hashlib.sha256(
        json.dumps(
            {
                "slotId": slot_id,
                "branch": branch,
                "worktreePath": str(worktree.resolve()),
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "slotId": slot_id,
        "branch": branch,
        "worktreePath": str(worktree.resolve()),
        "baselineRef": baseline_ref,
        "baselineCommit": baseline_commit,
        "baselineFingerprint": baseline_fingerprint,
        "workspaceFingerprint": workspace_fp,
        "declaredWriteSet": normalized_ws,
        "state": SLOT_STATE_READY,
        "agentId": "claude-code",
        "agentMayMerge": False,
    }


def build_slot_manifest(slot: dict[str, Any]) -> dict[str, Any]:
    """FR-CLW3-003 / AC-CLW3-003: build a slot identity/baseline manifest.

    The manifest is a stable JSON document that records the slot's unique
    branch, isolated worktree path, baseline identity and declared write set.
    It is suitable for evidence and merge-candidate construction (in a later
    Story).
    """
    return {
        "slotId": slot["slotId"],
        "branch": slot["branch"],
        "worktreePath": slot["worktreePath"],
        "baselineRef": slot["baselineRef"],
        "baselineCommit": slot["baselineCommit"],
        "baselineFingerprint": slot["baselineFingerprint"],
        "workspaceFingerprint": slot["workspaceFingerprint"],
        "declaredWriteSet": list(slot["declaredWriteSet"]),
        "state": slot["state"],
        "agentId": slot.get("agentId", "claude-code"),
        "agentMayMerge": False,
    }


def save_slot_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    """Persist a slot manifest as JSON for evidence."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_slot_manifest(path: str | Path) -> dict[str, Any]:
    """Load a persisted slot manifest."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def inspect_slot(slot: dict[str, Any]) -> dict[str, Any]:
    """FR-CLW3-004 / AC-CLW3-004: inspect slot status.

    Returns a dict with ``slotId``, ``branch``, ``isDirty``, ``headCommit``,
    and ``state``. Never mutates the worktree.
    """
    worktree = Path(slot["worktreePath"])
    # git status --porcelain in the worktree directory.
    status = _git(["status", "--porcelain"], cwd=str(worktree))
    is_dirty = bool(status.stdout.strip())
    # git rev-parse HEAD in the worktree.
    head = _git(["rev-parse", "HEAD"], cwd=str(worktree))
    head_commit = head.stdout.strip() if head.returncode == 0 else ""
    return {
        "slotId": slot["slotId"],
        "branch": slot["branch"],
        "isDirty": is_dirty,
        "headCommit": head_commit,
        "state": slot["state"],
    }


def preserve_dirty_slot(slot: dict[str, Any], reason: str) -> dict[str, Any]:
    """FR-CLW3-004 / AC-CLW3-005: preserve a dirty or failed worktree.

    The worktree is **not** deleted. The slot state transitions to
    ``preserved`` and the reason is recorded. Only Codex may later decide to
    remove or merge a governed worktree; this module exposes no deletion API.
    """
    preserved = dict(slot)
    preserved["state"] = SLOT_STATE_PRESERVED
    preserved["preserved"] = True
    preserved["reason"] = reason
    return preserved


def observed_changed_files(repo_path: str, baseline_commit: str, worktree_path: str) -> list[str]:
    """Return the normalized files changed from a fixed baseline.

    Committed changes are read from ``baseline_commit..HEAD`` and uncommitted
    changes are read from porcelain status. Agent self-report is never used as
    a substitute for Git evidence.
    """
    worktree = Path(worktree_path)
    diff = _git(["diff", "--name-only", baseline_commit, "HEAD"], cwd=worktree)
    status = _git(["status", "--porcelain", "--untracked-files=all"], cwd=worktree)
    values: list[str] = []
    if diff.returncode == 0:
        values.extend(line.strip() for line in diff.stdout.splitlines() if line.strip())
    for line in status.stdout.splitlines():
        if len(line) >= 4:
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path:
                values.append(path)
    normalized: list[str] = []
    for value in values:
        clean = value.replace("\\", "/").strip().lstrip("./").casefold()
        if clean and clean not in normalized:
            normalized.append(clean)
    return sorted(normalized)


def evaluate_observed_write_set(declared: list[str], observed: list[str]) -> dict[str, Any]:
    """Compare actual Git paths to a declaration using Windows-safe rules."""
    declared_norm = _write_set_normalized(declared)
    observed_norm = _write_set_normalized(observed)
    out_of_scope: list[str] = []
    for path in observed_norm:
        if not any(path == allowed or path.startswith(allowed + "/") for allowed in declared_norm):
            out_of_scope.append(path)
    return {
        "allowed": bool(declared_norm) and not out_of_scope,
        "declared": declared_norm,
        "observed": observed_norm,
        "outOfScope": sorted(out_of_scope),
        "state": "running" if bool(declared_norm) and not out_of_scope else "requirements-review",
    }


def build_merge_candidate(
    slot: dict[str, Any],
    head_commit: str,
    diff_hash: str,
    tests: list[dict[str, Any]],
    evidence_refs: list[str],
    *,
    feedback_validation: dict[str, Any] | None = None,
    observed_write_set: list[str] | None = None,
) -> dict[str, Any]:
    """Build an immutable, hash-bound candidate owned by Codex."""
    candidate = {
        "candidateType": "merge-candidate",
        "slotId": slot.get("slotId"),
        "storyId": slot.get("storyId", slot.get("slotId")),
        "branch": slot.get("branch"),
        "base": slot.get("baselineFingerprint"),
        "baseCommit": slot.get("baselineCommit"),
        "head": head_commit,
        "diffHash": diff_hash,
        "declaredWriteSet": _write_set_normalized(slot.get("declaredWriteSet") or slot.get("writeSet") or []),
        "observedWriteSet": _write_set_normalized(observed_write_set or []),
        "tests": list(tests),
        "evidenceRefs": list(evidence_refs),
        "mappedFrAc": list(slot.get("mappedFrAc") or []),
        "feedbackValidation": dict(feedback_validation or {}),
    }
    candidate["candidateHash"] = hashlib.sha256(
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return candidate


def validate_merge_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Recompute candidate identity and reject tampering or missing evidence."""
    supplied = candidate.get("candidateHash")
    body = {key: value for key, value in candidate.items() if key != "candidateHash"}
    computed = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    checks = {
        "hashMatches": supplied == computed,
        "storyTrace": bool(candidate.get("storyId")) and bool(candidate.get("mappedFrAc")),
        "evidence": bool(candidate.get("evidenceRefs")),
        "tests": bool(candidate.get("tests")),
        "writeSet": bool(candidate.get("declaredWriteSet")),
    }
    return {"valid": all(checks.values()), "checks": checks, "computedHash": computed}


def create_integration_worktree(
    repo_path: str,
    integration_branch: str,
    integration_path: str,
    baseline_ref: str,
    approved_root: str,
) -> dict[str, Any]:
    """Create a Codex-only integration worktree from a fixed baseline."""
    if not _resolve_inside(integration_path, approved_root):
        raise SlotError("path-escape")
    path = Path(integration_path)
    if path.exists():
        raise SlotError("integration-path-not-empty")
    baseline = _git(["rev-parse", "--verify", baseline_ref], cwd=repo_path)
    if baseline.returncode != 0:
        raise SlotError("baseline-ref-not-found")
    branch_check = _git(["rev-parse", "--verify", integration_branch], cwd=repo_path)
    if branch_check.returncode == 0:
        raise SlotError("branch-collision")
    added = _git(["worktree", "add", "-b", integration_branch, str(path), baseline_ref], cwd=repo_path)
    if added.returncode != 0:
        raise SlotError("integration-worktree-add-failed", git_rc=added.returncode)
    return {
        "integrationBranch": integration_branch,
        "integrationPath": str(path.resolve()),
        "baselineCommit": baseline.stdout.strip(),
        "agentMayMerge": False,
        "owner": "codex",
        "state": "ready",
    }


def integrate_candidates(
    repo_path: str,
    integration: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    baseline_ref: str,
    regression_argv: list[str] | None = None,
) -> dict[str, Any]:
    """Serially merge validated candidates in a separate worktree.

    The integration worktree is intentionally retained for every outcome. A
    conflict is left dirty so its files and branch remain inspectable.
    """
    validation = [validate_merge_candidate(item) for item in candidates]
    if not all(item["valid"] for item in validation):
        return {"state": "repair-needed", "mergeAllowed": False, "reason": "candidate-invalid", "validation": validation}
    current_baseline = _git(["rev-parse", "--verify", baseline_ref], cwd=repo_path)
    if current_baseline.returncode != 0 or current_baseline.stdout.strip() != integration.get("baselineCommit"):
        return {"state": "repair-needed", "mergeAllowed": False, "reason": "baseline-drift", "validation": validation}
    ordered = sorted(candidates, key=lambda item: str(item.get("storyId", "")))
    merged: list[str] = []
    for candidate in ordered:
        result = _git(["merge", "--no-ff", "--no-edit", str(candidate["branch"])], cwd=integration["integrationPath"])
        if result.returncode != 0:
            conflicts = _git(["diff", "--name-only", "--diff-filter=U"], cwd=integration["integrationPath"])
            return {
                "state": "repair-needed",
                "mergeAllowed": False,
                "reason": "merge-conflict",
                "integration": integration,
                "merged": merged,
                "conflictFiles": sorted(line.strip() for line in conflicts.stdout.splitlines() if line.strip()),
                "evidencePreserved": True,
            }
        merged.append(str(candidate["storyId"]))
    regression = {"ran": False, "passed": True, "argv": list(regression_argv or [])}
    if regression_argv:
        run = subprocess.run(regression_argv, cwd=integration["integrationPath"], capture_output=True, text=True, shell=False)
        regression = {"ran": True, "passed": run.returncode == 0, "argv": list(regression_argv), "returnCode": run.returncode}
    if not regression["passed"]:
        return {"state": "repair-needed", "mergeAllowed": False, "reason": "integration-regression-failed", "integration": integration, "merged": merged, "regression": regression}
    head = _git(["rev-parse", "HEAD"], cwd=integration["integrationPath"])
    return {"state": "passed", "mergeAllowed": True, "integration": integration, "merged": merged, "head": head.stdout.strip(), "regression": regression}


# Explicitly **do not** define merge_slot, delete_slot, or force_reset_slot.
# An Agent must not be able to mutate shared refs, merge, force-reset or
# delete a governed worktree. Only Codex controls those operations.


def main() -> int:
    """CLI entry for diagnostics only. Not used by tests."""
    print(json.dumps({"gitVersion": _git_version(), "states": list(SLOT_STATES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
