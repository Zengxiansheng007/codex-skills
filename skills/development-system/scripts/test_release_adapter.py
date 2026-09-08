import tempfile
import unittest
from pathlib import Path

from release_adapter import (
    DEFAULT_GITHUB_BRANCH,
    DEFAULT_GITHUB_REPOSITORY,
    DEFAULT_GITBOOK_ORGANIZATION_ID,
    DEFAULT_GITBOOK_SITE_ID,
    DEFAULT_GITBOOK_SPACE_ID,
    CommandResult,
    ReleaseError,
    build_parser,
    publish_github,
    validate_approval,
    verify_gitbook,
)


APPROVAL = {"approved": True, "targetRepository": "Zengxiansheng007/codex-skills", "targetBranch": "main",
            "publishVisibility": "public", "approvedPathRoots": ["skills/development-system",
            "skills/_requirements-docs/development-system-lifecycle-20260824"],
            "gitbookOrganizationId": "Nu93G7sN2JZ0YFbZODmd", "gitbookSiteId": "site_xT2YU",
            "gitbookSpaceId": "q7JoIgovR7WYwPc7tCa0"}


def validate(approval, repository="Zengxiansheng007/codex-skills", paths=None, site_id="site_xT2YU"):
    return validate_approval(
        approval,
        repository=repository,
        branch="main",
        paths=paths or ["skills/development-system"],
        organization_id="Nu93G7sN2JZ0YFbZODmd",
        gitbook_site_id=site_id,
        gitbook_space_id="q7JoIgovR7WYwPc7tCa0",
    )


class ReleaseAdapterTests(unittest.TestCase):
    def test_approval_rejects_unlisted_path(self):
        with self.assertRaisesRegex(ReleaseError, "path-not-approved"):
            validate(APPROVAL, paths=["private/raw"])

    def test_approval_accepts_exact_public_scope(self):
        validate(APPROVAL, repository="https://github.com/Zengxiansheng007/codex-skills.git",
                 paths=["skills/development-system", "skills/_requirements-docs/development-system-lifecycle-20260824"])

    def test_default_targets_are_stable(self):
        args = build_parser().parse_args(["--approval", "approval.json", "--repo", ".", "--path", "skills/development-system",
                                          "--message", "release", "--out", "report.json"])
        self.assertEqual(args.repository, DEFAULT_GITHUB_REPOSITORY)
        self.assertEqual(args.branch, DEFAULT_GITHUB_BRANCH)
        self.assertEqual(args.organization_id, DEFAULT_GITBOOK_ORGANIZATION_ID)
        self.assertEqual(args.gitbook_site_id, DEFAULT_GITBOOK_SITE_ID)
        self.assertEqual(args.gitbook_space_id, DEFAULT_GITBOOK_SPACE_ID)

    def test_approval_rejects_gitbook_site_mismatch(self):
        with self.assertRaisesRegex(ReleaseError, "gitbook-site-mismatch"):
            validate(APPROVAL, site_id="site_other")

    def test_publish_checks_remote_sha(self):
        calls = []
        def runner(args, cwd):
            calls.append(args)
            values = {("git", "remote", "get-url", "origin"): "https://github.com/Zengxiansheng007/codex-skills.git",
                      ("git", "branch", "--show-current"): "main",
                      ("git", "diff", "--cached", "--name-only"): "skills/development-system/SKILL.md",
                      ("git", "diff", "--cached", "--name-status"): "M\tskills/development-system/SKILL.md",
                      ("git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"): "skills/development-system/SKILL.md",
                      ("git", "rev-parse", "HEAD"): "a" * 40,
                      ("git", "ls-remote", "origin", "refs/heads/main"): "a" * 40 + "\trefs/heads/main"}
            return CommandResult(values.get(tuple(args), ""))
        with tempfile.TemporaryDirectory() as temp:
            result = publish_github(Path(temp), "Zengxiansheng007/codex-skills", "main", ["skills/development-system"], "release", runner)
        self.assertEqual(result["status"], "published")
        self.assertIn(["git", "push", "origin", "HEAD:main"], calls)

    def test_publish_rejects_local_runtime_artifact(self):
        def runner(args, cwd):
            values = {("git", "remote", "get-url", "origin"): "https://github.com/Zengxiansheng007/codex-skills.git",
                      ("git", "branch", "--show-current"): "main",
                      ("git", "diff", "--cached", "--name-only"): "skills/development-system/scripts/.codex/audit.jsonl",
                      ("git", "diff", "--cached", "--name-status"): "A\tskills/development-system/scripts/.codex/audit.jsonl",
                      ("git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"): "skills/development-system/scripts/.codex/audit.jsonl"}
            return CommandResult(values.get(tuple(args), ""))
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ReleaseError, "staged-local-runtime-artifact"):
                publish_github(Path(temp), "Zengxiansheng007/codex-skills", "main", ["skills/development-system"], "release", runner)

    def test_publish_allows_deleting_local_runtime_artifact(self):
        def runner(args, cwd):
            values = {("git", "remote", "get-url", "origin"): "https://github.com/Zengxiansheng007/codex-skills.git",
                      ("git", "branch", "--show-current"): "main",
                      ("git", "diff", "--cached", "--name-only"): "skills/development-system/scripts/.codex/audit.jsonl",
                      ("git", "diff", "--cached", "--name-status"): "D\tskills/development-system/scripts/.codex/audit.jsonl",
                      ("git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"): "",
                      ("git", "rev-parse", "HEAD"): "a" * 40,
                      ("git", "ls-remote", "origin", "refs/heads/main"): "a" * 40 + "\trefs/heads/main"}
            return CommandResult(values.get(tuple(args), ""))
        with tempfile.TemporaryDirectory() as temp:
            result = publish_github(Path(temp), "Zengxiansheng007/codex-skills", "main", ["skills/development-system"], "cleanup", runner)
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["publishedChanges"], ["D\tskills/development-system/scripts/.codex/audit.jsonl"])

    def test_gitbook_verification_is_independent(self):
        def getter(url, credential):
            if "/content" in url:
                return {"pages": [{"title": "Development System", "path": "skills/development-system"}]}
            if url.endswith("/site-spaces"):
                return {"items": [{"space": {"id": "space-1"}}]}
            return {"published": True, "siteSpaces": 1}
        self.assertEqual(verify_gitbook("space-1", "site-1", "org-1", ["Development System"], credential="redacted", getter=getter)["status"], "verified")

    def test_unpublished_site_does_not_pass(self):
        def getter(url, credential):
            if "/content" in url:
                return {"pages": [{"title": "Development System"}]}
            if url.endswith("/site-spaces"):
                return {"items": []}
            return {"published": False, "siteSpaces": 0}
        self.assertEqual(verify_gitbook("space-1", "site-1", "org-1", ["Development System"], credential="redacted", getter=getter)["status"], "not-verified")

    def test_site_space_count_shape_does_not_crash(self):
        def getter(url, credential):
            if "/content" in url:
                return {"pages": [{"title": "Development System"}]}
            if url.endswith("/site-spaces"):
                return {"items": []}
            return {"published": True, "siteSpaces": 1}
        result = verify_gitbook("space-1", "site-1", "org-1", ["Development System"], credential="redacted", getter=getter)
        self.assertEqual(result["status"], "not-verified")
        self.assertEqual(result["siteSpaceCount"], 1)


if __name__ == "__main__":
    unittest.main()
