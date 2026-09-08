"""Approval-gated GitHub publishing and independent GitBook verification."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


class ReleaseError(RuntimeError):
    pass


DEFAULT_GITHUB_REPOSITORY = "Zengxiansheng007/codex-skills"
DEFAULT_GITHUB_BRANCH = "main"
DEFAULT_GITBOOK_ORGANIZATION_ID = "Nu93G7sN2JZ0YFbZODmd"
DEFAULT_GITBOOK_SITE_ID = "site_xT2YU"
DEFAULT_GITBOOK_SPACE_ID = "q7JoIgovR7WYwPc7tCa0"


def _normalize_repository(value: str) -> str:
    normalized = value.strip().removesuffix(".git").replace("\\", "/")
    if normalized.startswith("git@github.com:"):
        normalized = normalized.removeprefix("git@github.com:")
    if "github.com/" in normalized:
        normalized = normalized.split("github.com/", 1)[1]
    return normalized.strip("/")


def validate_approval(approval: dict, *, repository: str, branch: str, paths: Iterable[str],
                      organization_id: str, gitbook_site_id: str, gitbook_space_id: str) -> None:
    errors: list[str] = []
    if approval.get("approved") is not True:
        errors.append("approval-required")
    if _normalize_repository(str(approval.get("targetRepository", ""))) != _normalize_repository(repository):
        errors.append("target-repository-mismatch")
    if approval.get("targetBranch") != branch:
        errors.append("target-branch-mismatch")
    if approval.get("publishVisibility") != "public":
        errors.append("public-visibility-not-approved")
    if approval.get("gitbookOrganizationId") != organization_id:
        errors.append("gitbook-organization-mismatch")
    if approval.get("gitbookSiteId") != gitbook_site_id:
        errors.append("gitbook-site-mismatch")
    if approval.get("gitbookSpaceId") != gitbook_space_id:
        errors.append("gitbook-space-mismatch")
    approved_roots = tuple(str(item).rstrip("/") + "/" for item in approval.get("approvedPathRoots", []))
    for path in paths:
        candidate = path.replace("\\", "/").lstrip("./")
        if not approved_roots or not any(candidate == root.rstrip("/") or candidate.startswith(root) for root in approved_roots):
            errors.append(f"path-not-approved:{candidate}")
    if errors:
        raise ReleaseError(";".join(errors))


@dataclass
class CommandResult:
    stdout: str
    returncode: int = 0


def default_runner(args: list[str], cwd: Path) -> CommandResult:
    effective_args = args
    if args and args[0] == "git":
        effective_args = ["git", "-c", f"safe.directory={cwd.resolve().as_posix()}", *args[1:]]
    completed = subprocess.run(effective_args, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleaseError(f"command-failed:{args[0]}:{detail[:500]}")
    return CommandResult(completed.stdout.strip(), completed.returncode)


def publish_github(repo: Path, repository: str, branch: str, paths: list[str], message: str,
                   runner: Callable[[list[str], Path], CommandResult] = default_runner) -> dict:
    remote = runner(["git", "remote", "get-url", "origin"], repo).stdout
    if _normalize_repository(remote) != _normalize_repository(repository):
        raise ReleaseError("git-remote-mismatch")
    if runner(["git", "branch", "--show-current"], repo).stdout != branch:
        raise ReleaseError("git-branch-mismatch")

    runner(["git", "add", "--", *paths], repo)
    staged = [line for line in runner(["git", "diff", "--cached", "--name-only"], repo).stdout.splitlines() if line]
    staged_changes = [line for line in runner(["git", "diff", "--cached", "--name-status"], repo).stdout.splitlines() if line]
    roots = tuple(path.replace("\\", "/").rstrip("/") + "/" for path in paths)
    outside = [path for path in staged if not any(path == root.rstrip("/") or path.startswith(root) for root in roots)]
    if outside:
        raise ReleaseError("staged-path-outside-approved-scope")
    non_deleted = [line for line in runner(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"], repo).stdout.splitlines() if line]
    forbidden = [path for path in non_deleted if "/.codex/" in f"/{path}" or "/__pycache__/" in f"/{path}" or path.endswith(".pyc")]
    if forbidden:
        raise ReleaseError("staged-local-runtime-artifact")
    if staged:
        runner(["git", "commit", "-m", message], repo)
        commit_action = "created"
    else:
        commit_action = "reused"
    local_sha = runner(["git", "rev-parse", "HEAD"], repo).stdout
    runner(["git", "push", "origin", f"HEAD:{branch}"], repo)
    remote_line = runner(["git", "ls-remote", "origin", f"refs/heads/{branch}"], repo).stdout
    remote_sha = remote_line.split()[0] if remote_line else ""
    if remote_sha != local_sha:
        raise ReleaseError("remote-sha-mismatch")
    return {"status": "published", "repository": _normalize_repository(repository), "branch": branch,
            "commitSha": local_sha, "commitAction": commit_action, "publishedPaths": staged,
            "publishedChanges": staged_changes}


def _safe_get_json(url: str, credential: str) -> dict:
    auth_scheme = "Bearer"
    request = urllib.request.Request(url, headers={"Authorization": f"{auth_scheme} {credential}", "User-Agent": "codex-development-system"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _walk_pages(value) -> list[dict]:
    pages: list[dict] = []
    if isinstance(value, dict):
        if any(key in value for key in ("title", "path", "slug")):
            pages.append(value)
        for child in value.values():
            pages.extend(_walk_pages(child))
    elif isinstance(value, list):
        for child in value:
            pages.extend(_walk_pages(child))
    return pages


def verify_gitbook(space_id: str, site_id: str, organization_id: str, expected_markers: list[str], *, credential: str,
                   getter: Callable[[str, str], dict] = _safe_get_json) -> dict:
    content = getter(f"https://api.gitbook.com/v1/spaces/{space_id}/content", credential)
    site = getter(f"https://api.gitbook.com/v1/orgs/{organization_id}/sites/{site_id}", credential)
    site_space_response = getter(f"https://api.gitbook.com/v1/orgs/{organization_id}/sites/{site_id}/site-spaces", credential)
    searchable = "\n".join(str(page.get(key, "")) for page in _walk_pages(content) for key in ("title", "path", "slug")).lower()
    missing = [marker for marker in expected_markers if marker.lower() not in searchable]
    site_spaces = site.get("siteSpaces") or []
    listed_spaces = site_spaces if isinstance(site_spaces, list) else site_space_response.get("items", [])
    linked_ids = set()
    for item in listed_spaces:
        if not isinstance(item, dict):
            continue
        space_value = item.get("space") or item.get("spaceId")
        if isinstance(space_value, dict):
            space_value = space_value.get("id")
        if space_value:
            linked_ids.add(space_value)
    linked = space_id in linked_ids or site.get("space") == space_id
    published = site.get("published") is True
    return {"status": "verified" if not missing and linked and published else "not-verified", "spaceId": space_id,
            "siteId": site_id, "contentMarkersPresent": not missing, "missingMarkers": missing,
            "siteLinked": linked, "sitePublished": published,
            "siteSpaceCount": site_spaces if isinstance(site_spaces, int) else len(listed_spaces)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--repository", default=DEFAULT_GITHUB_REPOSITORY)
    parser.add_argument("--branch", default=DEFAULT_GITHUB_BRANCH)
    parser.add_argument("--path", action="append", required=True, dest="paths")
    parser.add_argument("--message", required=True)
    parser.add_argument("--organization-id", default=DEFAULT_GITBOOK_ORGANIZATION_ID)
    parser.add_argument("--gitbook-space-id", default=DEFAULT_GITBOOK_SPACE_ID)
    parser.add_argument("--gitbook-site-id", default=DEFAULT_GITBOOK_SITE_ID)
    parser.add_argument("--expected-marker", action="append", default=[])
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    approval = json.loads(args.approval.read_text(encoding="utf-8"))
    validate_approval(
        approval,
        repository=args.repository,
        branch=args.branch,
        paths=args.paths,
        organization_id=args.organization_id,
        gitbook_site_id=args.gitbook_site_id,
        gitbook_space_id=args.gitbook_space_id,
    )
    github = publish_github(args.repo, args.repository, args.branch, args.paths, args.message)
    credential = os.environ.get("GITBOOK_TOKEN", "")
    if not credential:
        raise ReleaseError("GITBOOK_TOKEN-not-set")
    deadline = time.monotonic() + max(0, args.poll_seconds)
    gitbook = {"status": "not-verified"}
    while True:
        gitbook = verify_gitbook(args.gitbook_space_id, args.gitbook_site_id, args.organization_id,
                                 args.expected_marker, credential=credential)
        if gitbook["status"] == "verified" or time.monotonic() >= deadline:
            break
        time.sleep(10)
    report = {"status": "completed" if gitbook["status"] == "verified" else "partial", "github": github, "gitbook": gitbook}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
