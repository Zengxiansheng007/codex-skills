"""Deterministic CLW PH-3 Windows Git worktree runtime tests for CLW-ST-301.

This suite exercises the real Windows Git worktree execution slot runtime
(``git_worktree_runtime.py``) against *real* temporary Git repositories and
worktrees created inside ``tempfile.TemporaryDirectory`` roots. It never
spawns a shell (all Git calls use ``subprocess`` argv arrays with
``shell=False``), never installs dependencies, never touches the network and
never merges or force-resets branches.

Coverage:
- FR-CLW3-001 repository preflight (valid repo, non-Git input, submodule
  boundary rejection).
- FR-CLW3-002 unique branch + worktree creation (fail-on-collision, never
  ``git worktree add -B``).
- FR-CLW3-003 slot identity/baseline manifest (unique branch, isolated path,
  baseline identity, declared write set).
- FR-CLW3-004 status inspection + dirty preserve semantics (dirty worktrees
  are preserved as evidence; only Codex may remove them).
- AC-CLW3-001 through AC-CLW3-005.

The script is intentionally self-contained: it imports only
``git_worktree_runtime`` and the Python standard library, and it emits a
single deterministic pass/fail marker so it can be wired into the approved
PowerShell validation command in SKILL.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Allow running this test directly from the scripts directory without an
# installed package: ensure the parent directory (the skill root) is on
# ``sys.path`` so ``import git_worktree_runtime`` resolves.
SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from git_worktree_runtime import (  # noqa: E402
    SLOT_STATE_PRESERVED,
    SLOT_STATE_RUNNING,
    SLOT_STATE_READY,
    SlotError,
    build_slot_manifest,
    build_merge_candidate,
    create_integration_worktree,
    create_slot,
    evaluate_observed_write_set,
    integrate_candidates,
    inspect_slot,
    load_slot_manifest,
    observed_changed_files,
    preflight_repository,
    preserve_dirty_slot,
    save_slot_manifest,
    validate_merge_candidate,
)
from build_clw_ph3_live_packets import build_packet  # noqa: E402


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def test_live_packet_generation_uses_exact_policy_feedback_schema(errors: list[str]) -> None:
    """Live packets must preserve exact-match preauthorization fields."""
    policy = {
        "policyId": "POLICY-EXACT",
        "policyHash": "c" * 64,
        "actions": ["read", "edit"],
        "tools": ["Claude Code local file tools"],
        "data": ["synthetic"],
        "network": [],
        "credentialBoundary": "inherit only",
        "feedbackSchema": "C:/exact/policy/feedback-packet.schema.json",
        "stopConditions": ["boundary drift"],
    }
    slot = {
        "declaredWriteSet": ["live/a.txt"],
        "worktreePath": "C:/approved/worktree/slot-a",
        "baselineCommit": "d" * 40,
    }
    packet = build_packet(slot, policy, 1)
    required = packet["requiredAuthorization"]
    check(
        required["feedbackSchema"] == policy["feedbackSchema"],
        "requiredAuthorization feedbackSchema was normalized or rewritten",
        errors,
    )
    check(
        packet["expectedFeedbackSchema"] == policy["feedbackSchema"],
        "expectedFeedbackSchema was normalized or rewritten",
        errors,
    )


def _git(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run a Git command with an argv array (never shell=True)."""
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        shell=False,
    )


def _make_baseline_repo(root: Path) -> Path:
    """Create a real temporary Git repository with one committed file."""
    repo = root / "baseline-repo"
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, ["init", "--initial-branch=main"])
    _git(repo, ["config", "user.email", "clw-ph3@example.com"])
    _git(repo, ["config", "user.name", "CLW PH-3 Test"])
    (repo / "README.md").write_text("# CLW PH-3 baseline\n", encoding="utf-8")
    _git(repo, ["add", "README.md"])
    _git(repo, ["commit", "-m", "baseline"])
    return repo


def _commit_file(repo: Path, relative: str, content: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(repo, ["add", relative])
    result = _git(repo, ["commit", "-m", message])
    if result.returncode != 0:
        raise AssertionError(f"git commit failed: {message}")


def test_preflight_valid_repository(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        result = preflight_repository(str(repo))
        check(result["ok"], f"preflight valid repo rejected: {result}", errors)
        check(
            bool(result.get("gitVersion")),
            "preflight did not report gitVersion",
            errors,
        )
        check(
            result.get("isGit") is True,
            "preflight did not set isGit=True",
            errors,
        )
        check(
            result.get("hasSubmodules") is False,
            "preflight incorrectly detected submodules",
            errors,
        )


def test_preflight_non_git_input(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        non_git = root / "not-a-repo"
        non_git.mkdir(parents=True, exist_ok=True)
        (non_git / "file.txt").write_text("hello", encoding="utf-8")
        result = preflight_repository(str(non_git))
        check(not result["ok"], "non-Git input was accepted by preflight", errors)
        check(
            "not-a-git-repository" in result.get("reason", "")
            or result.get("isGit") is False,
            f"non-Git input reason wrong: {result}",
            errors,
        )


def test_preflight_submodule_boundary_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        # Simulate a submodule boundary by creating .gitmodules.
        (repo / ".gitmodules").write_text(
            '[submodule "vendor"]\npath = vendor\nurl = https://example.com/vendor.git\n',
            encoding="utf-8",
        )
        _git(repo, ["add", ".gitmodules"])
        _git(repo, ["commit", "-m", "add submodule boundary"])
        result = preflight_repository(str(repo))
        check(not result["ok"], "submodule boundary repo was accepted", errors)
        check(
            "submodule" in result.get("reason", "").lower(),
            f"submodule reason wrong: {result}",
            errors,
        )


def test_create_slot_unique_branch_and_worktree(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        pre = preflight_repository(str(repo))
        check(pre["ok"], "preflight failed before create_slot", errors)
        worktree_path = root / "slot-a"
        slot = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-A",
            branch="clw/slot-a",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/a.py"],
            approved_root=str(root),
        )
        check(slot["slotId"] == "SLOT-A", "slotId mismatch", errors)
        check(slot["branch"] == "clw/slot-a", "branch mismatch", errors)
        check(slot["state"] == SLOT_STATE_READY, "state not READY", errors)
        check(
            len(slot["baselineFingerprint"]) == 64
            and all(c in "0123456789abcdef" for c in slot["baselineFingerprint"]),
            "baseline fingerprint is not a 64-char lowercase hex SHA-256",
            errors,
        )
        baseline_commit = _git(repo, ["rev-parse", "main"]).stdout.strip()
        check(
            slot["baselineCommit"] == baseline_commit,
            "slot baselineCommit does not match the real Git baseline",
            errors,
        )
        check(worktree_path.exists(), "worktree path not created", errors)
        # Worktree must have its own working tree file.
        check(
            (worktree_path / "README.md").exists(),
            "worktree does not contain baseline file",
            errors,
        )
        # Branch must be unique: rev-parse --verify should succeed.
        rev = _git(repo, ["rev-parse", "--verify", "clw/slot-a"])
        check(rev.returncode == 0, "unique branch was not created", errors)
        # Worktree list must include the new path (normalize backslashes for
        # Windows cross-comparison).
        wt_list = _git(repo, ["worktree", "list"])
        wt_path_norm = str(worktree_path).replace("\\", "/")
        wt_list_norm = wt_list.stdout.replace("\\", "/")
        check(
            wt_path_norm in wt_list_norm,
            "worktree list missing new path",
            errors,
        )


def test_create_slot_branch_collision_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        # Pre-create a branch with the collision name.
        _git(repo, ["branch", "clw/collide"])
        worktree_path = root / "slot-collide"
        try:
            create_slot(
                repo_path=str(repo),
                slot_id="SLOT-COLLIDE",
                branch="clw/collide",
                worktree_path=str(worktree_path),
                baseline_ref="main",
                declared_write_set=["src/c.py"],
                approved_root=str(root),
            )
            check(False, "branch collision was accepted", errors)
        except SlotError as exc:
            check(
                "branch-collision" in exc.reason,
                f"branch collision reason wrong: {exc.reason}",
                errors,
            )
            check(
                not worktree_path.exists(),
                "worktree path created despite collision",
                errors,
            )


def test_create_slot_shared_worktree_path_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        shared = root / "shared"
        shared.mkdir(parents=True, exist_ok=True)
        try:
            create_slot(
                repo_path=str(repo),
                slot_id="SLOT-SHARED",
                branch="clw/shared",
                worktree_path=str(shared),
                baseline_ref="main",
                declared_write_set=["src/s.py"],
                approved_root=str(root),
            )
            check(False, "shared worktree path was accepted", errors)
        except SlotError as exc:
            check(
                "worktree-path-not-empty" in exc.reason
                or "path-escape" in exc.reason,
                f"shared path reason wrong: {exc.reason}",
                errors,
            )


def test_create_slot_path_escape_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        # Worktree path that escapes the approved root.
        escaping = Path(tmp).parent / "escaped-slot"
        try:
            create_slot(
                repo_path=str(repo),
                slot_id="SLOT-ESCAPE",
                branch="clw/escape",
                worktree_path=str(escaping),
                baseline_ref="main",
                declared_write_set=["src/e.py"],
                approved_root=str(root),
            )
            check(False, "path escape was accepted", errors)
        except SlotError as exc:
            check(
                "path-escape" in exc.reason,
                f"path escape reason wrong: {exc.reason}",
                errors,
            )


def test_create_slot_never_uses_force_reset(errors: list[str]) -> None:
    """Confirm create_slot never uses `git worktree add -B` or `git switch -B`.

    This is a structural guard: we run create_slot in a temp repo with a
    pre-existing branch and verify it fails closed instead of resetting.
    The runtime must use fail-on-collision semantics.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        _git(repo, ["branch", "clw/force"])
        worktree_path = root / "slot-force"
        try:
            create_slot(
                repo_path=str(repo),
                slot_id="SLOT-FORCE",
                branch="clw/force",
                worktree_path=str(worktree_path),
                baseline_ref="main",
                declared_write_set=["src/f.py"],
                approved_root=str(root),
            )
            check(False, "force-reset branch was silently reused", errors)
        except SlotError as exc:
            check(
                "branch-collision" in exc.reason,
                "force-reset guard did not detect branch collision",
                errors,
            )
        # The original branch ref must be unchanged (no reset).
        rev_before = _git(repo, ["rev-parse", "clw/force"])
        rev_main = _git(repo, ["rev-parse", "main"])
        check(
            rev_before.stdout.strip() == rev_main.stdout.strip(),
            "branch was reset despite fail-on-collision",
            errors,
        )


def test_slot_manifest_identity_and_baseline(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_path = root / "slot-manifest"
        slot = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-M",
            branch="clw/manifest",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/m.py", "tests/m_test.py"],
            approved_root=str(root),
        )
        manifest = build_slot_manifest(slot)
        check(manifest["slotId"] == "SLOT-M", "manifest slotId wrong", errors)
        check(
            manifest["branch"] == "clw/manifest",
            "manifest branch wrong",
            errors,
        )
        check(
            manifest["worktreePath"] == str(worktree_path),
            "manifest worktreePath wrong",
            errors,
        )
        check(
            manifest["baselineFingerprint"] == slot["baselineFingerprint"],
            "manifest baseline fingerprint wrong",
            errors)
        check(
            manifest["baselineCommit"] == slot["baselineCommit"],
            "manifest baseline commit wrong",
            errors,
        )
        check(
            manifest["state"] == SLOT_STATE_READY,
            "manifest state wrong",
            errors,
        )
        check(
            manifest["workspaceFingerprint"] != manifest["baselineFingerprint"],
            "workspace fingerprint equals baseline fingerprint",
            errors,
        )
        # Declared write set must be normalized.
        check(
            manifest["declaredWriteSet"] == ["src/m.py", "tests/m_test.py"]
            or manifest["declaredWriteSet"] == ["src/m.py", "tests/m_test.py"]
            or sorted(manifest["declaredWriteSet"]) == ["src/m.py", "tests/m_test.py"],
            f"manifest write set wrong: {manifest['declaredWriteSet']}",
            errors,
        )
        # Save/load manifest round-trip.
        manifest_path = root / "manifest.json"
        save_slot_manifest(manifest, manifest_path)
        loaded = load_slot_manifest(manifest_path)
        check(
            loaded["slotId"] == manifest["slotId"],
            "loaded manifest slotId mismatch",
            errors,
        )
        check(
            loaded["workspaceFingerprint"] == manifest["workspaceFingerprint"],
            "loaded manifest workspace fingerprint mismatch",
            errors,
        )


def test_inspect_slot_clean(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_path = root / "slot-clean"
        slot = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-CLEAN",
            branch="clw/clean",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/clean.py"],
            approved_root=str(root),
        )
        status = inspect_slot(slot)
        check(status["slotId"] == "SLOT-CLEAN", "inspect slotId wrong", errors)
        check(
            status["isDirty"] is False,
            f"clean slot reported dirty: {status}",
            errors,
        )
        check(
            status["branch"] == "clw/clean",
            "inspect branch wrong",
            errors,
        )
        check(
            bool(status.get("headCommit")),
            "inspect missing headCommit",
            errors,
        )


def test_inspect_slot_dirty(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_path = root / "slot-dirty"
        slot = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-DIRTY",
            branch="clw/dirty",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/dirty.py"],
            approved_root=str(root),
        )
        # Make the worktree dirty.
        (worktree_path / "README.md").write_text(
            "# CLW PH-3 dirty\n",
            encoding="utf-8",
        )
        status = inspect_slot(slot)
        check(
            status["isDirty"] is True,
            f"dirty slot reported clean: {status}",
            errors,
        )


def test_dirty_preserve_semantics(errors: list[str]) -> None:
    """Dirty or failed worktrees are preserved as evidence; only Codex removes."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_path = root / "slot-preserve"
        slot = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-PRESERVE",
            branch="clw/preserve",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/preserve.py"],
            approved_root=str(root),
        )
        # Make dirty.
        (worktree_path / "README.md").write_text(
            "# CLW PH-3 preserve\n",
            encoding="utf-8",
        )
        preserved = preserve_dirty_slot(slot, reason="test-dirty-preserve")
        check(
            preserved["state"] == SLOT_STATE_PRESERVED,
            f"preserve state wrong: {preserved}",
            errors,
        )
        check(
            preserved["preserved"] is True,
            "preserve did not set preserved=True",
            errors,
        )
        check(
            "test-dirty-preserve" in preserved["reason"],
            "preserve reason missing",
            errors,
        )
        # The worktree must still exist (not deleted).
        check(
            worktree_path.exists(),
            "dirty worktree was deleted during preserve",
            errors,
        )
        # And the worktree must still be registered in git worktree list.
        wt_list = _git(repo, ["worktree", "list"])
        wt_path_norm = str(worktree_path).replace("\\", "/")
        wt_list_norm = wt_list.stdout.replace("\\", "/")
        check(
            wt_path_norm in wt_list_norm,
            "dirty worktree removed from git worktree list",
            errors,
        )


def test_agent_cannot_merge_or_delete(errors: list[str]) -> None:
    """The runtime must not expose merge/delete operations to an Agent."""
    import git_worktree_runtime as mod

    forbidden = ["merge_slot", "delete_slot", "force_reset_slot"]
    for name in forbidden:
        check(
            not hasattr(mod, name),
            f"runtime exposes forbidden Agent operation: {name}",
            errors,
        )


def test_slot_worktree_isolation(errors: list[str]) -> None:
    """Two slots must have isolated worktree paths and unique branches."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_a = root / "slot-iso-a"
        worktree_b = root / "slot-iso-b"
        slot_a = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-ISO-A",
            branch="clw/iso-a",
            worktree_path=str(worktree_a),
            baseline_ref="main",
            declared_write_set=["src/a.py"],
            approved_root=str(root),
        )
        slot_b = create_slot(
            repo_path=str(repo),
            slot_id="SLOT-ISO-B",
            branch="clw/iso-b",
            worktree_path=str(worktree_b),
            baseline_ref="main",
            declared_write_set=["src/b.py"],
            approved_root=str(root),
        )
        check(
            slot_a["worktreePath"] != slot_b["worktreePath"],
            "slot worktree paths not isolated",
            errors,
        )
        check(
            slot_a["branch"] != slot_b["branch"],
            "slot branches not unique",
            errors,
        )
        check(
            slot_a["workspaceFingerprint"] != slot_b["workspaceFingerprint"],
            "workspace fingerprints not unique",
            errors,
        )


def test_baseline_identity_unchanged(errors: list[str]) -> None:
    """Creating a slot must not move the baseline branch."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        baseline_before = _git(repo, ["rev-parse", "main"]).stdout.strip()
        worktree_path = root / "slot-base"
        create_slot(
            repo_path=str(repo),
            slot_id="SLOT-BASE",
            branch="clw/base",
            worktree_path=str(worktree_path),
            baseline_ref="main",
            declared_write_set=["src/b.py"],
            approved_root=str(root),
        )
        baseline_after = _git(repo, ["rev-parse", "main"]).stdout.strip()
        check(
            baseline_before == baseline_after,
            "baseline branch moved during slot creation",
            errors,
        )


def test_create_slot_invalid_baseline_ref_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        worktree_path = root / "slot-badref"
        try:
            create_slot(
                repo_path=str(repo),
                slot_id="SLOT-BADREF",
                branch="clw/badref",
                worktree_path=str(worktree_path),
                baseline_ref="nonexistent-ref",
                declared_write_set=["src/x.py"],
                approved_root=str(root),
            )
            check(False, "invalid baseline ref was accepted", errors)
        except SlotError as exc:
            check(
                "baseline-ref-not-found" in exc.reason,
                f"invalid baseline ref reason wrong: {exc.reason}",
                errors,
            )


def test_observed_write_set_and_out_of_scope_detection(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        baseline = _git(repo, ["rev-parse", "main"]).stdout.strip()
        worktree = root / "slot-observed"
        slot = create_slot(str(repo), "SLOT-OBS", "clw/observed", str(worktree), "main", ["src/a"], str(root))
        _commit_file(worktree, "src/a/changed.py", "a\n", "slot change")
        observed = observed_changed_files(str(repo), baseline, str(worktree))
        decision = evaluate_observed_write_set(["src/a"], observed)
        check(decision["allowed"], f"declared directory did not allow child diff: {decision}", errors)
        (worktree / "outside.txt").write_text("outside\n", encoding="utf-8")
        observed_with_outside = observed_changed_files(str(repo), baseline, str(worktree))
        blocked = evaluate_observed_write_set(["src/a"], observed_with_outside)
        check(not blocked["allowed"], "out-of-scope observed write was accepted", errors)
        check("outside.txt" in blocked["outOfScope"], f"out-of-scope file missing: {blocked}", errors)
        check(slot["baselineCommit"] == baseline, "slot baseline commit changed during observation", errors)


def test_observed_write_set_expands_untracked_directories(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        baseline = _git(repo, ["rev-parse", "main"]).stdout.strip()
        worktree = root / "slot-untracked-dir"
        create_slot(str(repo), "SLOT-UNTRACKED", "clw/untracked", str(worktree), "main", ["live/a.txt"], str(root))
        (worktree / "live").mkdir(parents=True, exist_ok=True)
        (worktree / "live" / "a.txt").write_text("a\n", encoding="utf-8")
        observed = observed_changed_files(str(repo), baseline, str(worktree))
        decision = evaluate_observed_write_set(["live/a.txt"], observed)
        check("live/a.txt" in observed, f"untracked file was not expanded: {observed}", errors)
        check("live" not in observed, f"untracked directory leaked into observed set: {observed}", errors)
        check(decision["allowed"], f"expanded untracked file was rejected: {decision}", errors)


def _candidate_for_slot(slot: dict[str, Any], story_id: str, head: str, observed: list[str]) -> dict[str, Any]:
    return build_merge_candidate(
        {**slot, "storyId": story_id, "mappedFrAc": [f"FR-{story_id}", f"AC-{story_id}"]},
        head,
        "a" * 64,
        [{"command": "deterministic-test", "passed": True}],
        [f"evidence://{story_id}"],
        feedback_validation={"ok": True, "validatorId": "test", "schemaRef": "schema", "feedbackHash": "b" * 64},
        observed_write_set=observed,
    )


def test_merge_candidate_hash_and_tamper_rejection(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        slot = create_slot(str(repo), "SLOT-CAND", "clw/candidate", str(root / "slot"), "main", ["src"], str(root))
        candidate = _candidate_for_slot(slot, "CLW-ST-302", slot["baselineCommit"], ["src/a.py"])
        valid = validate_merge_candidate(candidate)
        check(valid["valid"], f"valid candidate rejected: {valid}", errors)
        candidate["head"] = "tampered"
        invalid = validate_merge_candidate(candidate)
        check(not invalid["valid"] and not invalid["checks"]["hashMatches"], "tampered candidate accepted", errors)


def test_integration_success_and_regression_gate(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        baseline = _git(repo, ["rev-parse", "main"]).stdout.strip()
        slot_a_path, slot_b_path = root / "slot-a", root / "slot-b"
        slot_a = create_slot(str(repo), "SLOT-A", "clw/a", str(slot_a_path), "main", ["src/a"], str(root))
        slot_b = create_slot(str(repo), "SLOT-B", "clw/b", str(slot_b_path), "main", ["src/b"], str(root))
        _commit_file(slot_a_path, "src/a/a.py", "a\n", "a")
        _commit_file(slot_b_path, "src/b/b.py", "b\n", "b")
        head_a = _git(slot_a_path, ["rev-parse", "HEAD"]).stdout.strip()
        head_b = _git(slot_b_path, ["rev-parse", "HEAD"]).stdout.strip()
        cand_a = _candidate_for_slot(slot_a, "CLW-ST-303-A", head_a, ["src/a/a.py"])
        cand_b = _candidate_for_slot(slot_b, "CLW-ST-303-B", head_b, ["src/b/b.py"])
        integration = create_integration_worktree(str(repo), "codex/integration-ok", str(root / "integration-ok"), "main", str(root))
        result = integrate_candidates(str(repo), integration, [cand_b, cand_a], baseline_ref="main", regression_argv=[sys.executable, "-c", "raise SystemExit(0)"])
        check(result["mergeAllowed"] and result["state"] == "passed", f"disjoint integration rejected: {result}", errors)
        check(result["merged"] == ["CLW-ST-303-A", "CLW-ST-303-B"], f"merge order unstable: {result}", errors)
        check((Path(integration["integrationPath"]) / "src/a/a.py").exists(), "integration missing A change", errors)
        check((Path(integration["integrationPath"]) / "src/b/b.py").exists(), "integration missing B change", errors)
        check(_git(repo, ["rev-parse", "main"]).stdout.strip() == baseline, "main baseline mutated by integration", errors)


def test_integration_conflict_preserved_and_baseline_drift_rejected(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        baseline = _git(repo, ["rev-parse", "main"]).stdout.strip()
        slot_a_path, slot_b_path = root / "slot-conflict-a", root / "slot-conflict-b"
        slot_a = create_slot(str(repo), "SLOT-CA", "clw/ca", str(slot_a_path), "main", ["README.md"], str(root))
        slot_b = create_slot(str(repo), "SLOT-CB", "clw/cb", str(slot_b_path), "main", ["README.md"], str(root))
        _commit_file(slot_a_path, "README.md", "A\n", "conflict A")
        _commit_file(slot_b_path, "README.md", "B\n", "conflict B")
        cand_a = _candidate_for_slot(slot_a, "CLW-ST-CONFLICT-A", _git(slot_a_path, ["rev-parse", "HEAD"]).stdout.strip(), ["readme.md"])
        cand_b = _candidate_for_slot(slot_b, "CLW-ST-CONFLICT-B", _git(slot_b_path, ["rev-parse", "HEAD"]).stdout.strip(), ["readme.md"])
        integration = create_integration_worktree(str(repo), "codex/integration-conflict", str(root / "integration-conflict"), "main", str(root))
        conflict = integrate_candidates(str(repo), integration, [cand_a, cand_b], baseline_ref="main")
        check(conflict["state"] == "repair-needed" and conflict["reason"] == "merge-conflict", f"conflict not blocked: {conflict}", errors)
        check(conflict["evidencePreserved"] and conflict["conflictFiles"], "conflict evidence not preserved", errors)
        check(Path(integration["integrationPath"]).exists(), "conflict integration worktree was removed", errors)
        drift_path = root / "slot-drift"
        drift_slot = create_slot(str(repo), "SLOT-DRIFT", "clw/drift", str(drift_path), "main", ["src"], str(root))
        _commit_file(drift_path, "src/drift.py", "drift\n", "drift branch")
        drift_candidate = _candidate_for_slot(drift_slot, "CLW-ST-DRIFT", _git(drift_path, ["rev-parse", "HEAD"]).stdout.strip(), ["src/drift.py"])
        drift_integration = create_integration_worktree(str(repo), "codex/integration-drift", str(root / "integration-drift"), "main", str(root))
        _commit_file(repo, "baseline-after-slot.py", "baseline\n", "baseline drift")
        drift = integrate_candidates(str(repo), drift_integration, [drift_candidate], baseline_ref="main")
        check(drift["reason"] == "baseline-drift" and not drift["mergeAllowed"], f"baseline drift accepted: {drift}", errors)


def test_integration_regression_failure_preserved(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = _make_baseline_repo(root)
        path = root / "slot-regression"
        slot = create_slot(str(repo), "SLOT-REG", "clw/reg", str(path), "main", ["src"], str(root))
        _commit_file(path, "src/reg.py", "reg\n", "reg")
        candidate = _candidate_for_slot(slot, "CLW-ST-REG", _git(path, ["rev-parse", "HEAD"]).stdout.strip(), ["src/reg.py"])
        integration = create_integration_worktree(str(repo), "codex/integration-reg", str(root / "integration-reg"), "main", str(root))
        result = integrate_candidates(str(repo), integration, [candidate], baseline_ref="main", regression_argv=[sys.executable, "-c", "raise SystemExit(3)"])
        check(result["reason"] == "integration-regression-failed" and not result["mergeAllowed"], f"regression failure accepted: {result}", errors)
        check(Path(integration["integrationPath"]).exists(), "failed regression worktree was removed", errors)


def main() -> int:
    errors: list[str] = []
    test_live_packet_generation_uses_exact_policy_feedback_schema(errors)
    test_preflight_valid_repository(errors)
    test_preflight_non_git_input(errors)
    test_preflight_submodule_boundary_rejected(errors)
    test_create_slot_unique_branch_and_worktree(errors)
    test_create_slot_branch_collision_rejected(errors)
    test_create_slot_shared_worktree_path_rejected(errors)
    test_create_slot_path_escape_rejected(errors)
    test_create_slot_never_uses_force_reset(errors)
    test_create_slot_invalid_baseline_ref_rejected(errors)
    test_slot_manifest_identity_and_baseline(errors)
    test_inspect_slot_clean(errors)
    test_inspect_slot_dirty(errors)
    test_dirty_preserve_semantics(errors)
    test_agent_cannot_merge_or_delete(errors)
    test_slot_worktree_isolation(errors)
    test_baseline_identity_unchanged(errors)
    test_observed_write_set_and_out_of_scope_detection(errors)
    test_observed_write_set_expands_untracked_directories(errors)
    test_merge_candidate_hash_and_tamper_rejection(errors)
    test_integration_success_and_regression_gate(errors)
    test_integration_conflict_preserved_and_baseline_drift_rejected(errors)
    test_integration_regression_failure_preserved(errors)
    if errors:
        print("CLW_PHASE3_WORKTREE_RUNTIME_FAIL")
        for error in errors:
            print("  -", error)
        return 1
    print("CLW_PHASE3_WORKTREE_RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
