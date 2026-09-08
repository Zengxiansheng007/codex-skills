import unittest

from document_manifest_runtime import digest_text
from publish_package import plan_publish


CONTENT = "# package\n"


def manifest():
    return {
        "docId": "urn:project:requirements:package@1.0.0",
        "category": "requirements",
        "phase": "published",
        "version": "1.0.0",
        "sourceCommit": "b" * 40,
        "integrity": {"algorithm": "SHA-256", "digest": digest_text(CONTENT)},
        "classification": {"skill": "development-system", "subSkill": "", "product": "demo", "project": "demo", "module": "core"},
        "paths": {"localRag": "x", "github": "https://github.example/blob/" + "b" * 40 + "/x.md", "githubRepository": "org/repo", "online": ""},
        "provenance": {"derivedFrom": [], "generatedBy": "test", "attributedTo": "test"},
        "status": "draft",
    }


class PublishPlanTests(unittest.TestCase):
    def test_dry_run_requires_no_external_write(self):
        result = plan_publish(manifest(), CONTENT, {"approved": True, "targetRepository": "org/repo"}, [])
        self.assertEqual(result["status"], "preflight-passed")
        self.assertFalse(result["preflight"]["externalWrite"])
        self.assertEqual(result["github"], "not-written")
        self.assertEqual(result["gitbook"], "not-written")

    def test_target_mismatch_blocks(self):
        result = plan_publish(manifest(), CONTENT, {"approved": True, "targetRepository": "other/repo"}, [])
        self.assertEqual(result["status"], "failed")
        self.assertIn("target-repository-mismatch", result["preflight"]["errors"])

    def test_approval_missing_blocks(self):
        result = plan_publish(manifest(), CONTENT, {"approved": False, "targetRepository": "org/repo"}, [])
        self.assertEqual(result["status"], "failed")
        self.assertIn("approval-required", result["preflight"]["errors"])


if __name__ == "__main__":
    unittest.main()
