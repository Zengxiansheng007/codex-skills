"""Create the approved temporary Git fixture used by the PH-3 two-slot live test."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from git_worktree_runtime import create_slot


def git(repo: Path, args: list[str]) -> None:
    result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise SystemExit(f"git fixture command failed: {args[0]}")


def main() -> int:
    root = Path(__file__).resolve().parents[3] / "test-runs" / "clw-ph3-runtime-20260817" / "live-repo-001"
    root.mkdir(parents=True, exist_ok=True)
    repo = root / "baseline-repo"
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        git(repo, ["init", "--initial-branch=main"])
        git(repo, ["config", "user.email", "clw-ph3-live@example.com"])
        git(repo, ["config", "user.name", "CLW PH-3 Live"])
        (repo / "README.md").write_text("# CLW PH-3 live fixture\n", encoding="utf-8")
        git(repo, ["add", "README.md"])
        git(repo, ["commit", "-m", "live baseline"])
    approved_root = root
    slots = []
    for slot_id, branch, path, write_set in (
        ("LIVE-SLOT-A", "clw/live-a", root / "slot-a", ["live/a.txt"]),
        ("LIVE-SLOT-B", "clw/live-b", root / "slot-b", ["live/b.txt"]),
    ):
        if path.exists():
            raise SystemExit(f"fixture worktree already exists: {path}")
        slots.append(create_slot(str(repo), slot_id, branch, str(path), "main", write_set, str(approved_root)))
    output = root / "slot-manifests.json"
    output.write_text(json.dumps({"repo": str(repo), "approvedRoot": str(approved_root), "slots": slots}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"repo": str(repo), "approvedRoot": str(approved_root), "slots": slots}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
