import unittest

from document_manifest_runtime import digest_text, register_or_reuse, rollback, transition, validate_manifest


CONTENT = "# stable document\n"


def manifest(status="draft", digest=None):
    return {
        "docId": "urn:project:requirements:demo@1.0.0",
        "category": "requirements",
        "phase": "draft",
        "version": "1.0.0",
        "sourceCommit": "a" * 40,
        "integrity": {"algorithm": "SHA-256", "digest": digest or digest_text(CONTENT)},
        "classification": {"skill": "development-system", "subSkill": "", "product": "demo", "project": "demo", "module": "core"},
        "paths": {"localRag": "project/demo/requirements/demo.md", "github": "https://github.example/blob/" + "a" * 40 + "/demo.md", "online": ""},
        "provenance": {"derivedFrom": [], "generatedBy": "test", "attributedTo": "test"},
        "status": status,
    }


class ManifestRuntimeTests(unittest.TestCase):
    def test_valid_manifest_and_digest(self):
        self.assertEqual(validate_manifest(manifest(), CONTENT), [])

    def test_digest_mismatch_rejected(self):
        self.assertIn("digest-mismatch", validate_manifest(manifest(digest="b" * 64), CONTENT))

    def test_invalid_transition_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid-transition"):
            transition({"status": "draft", "history": []}, "gitbook-verified")

    def test_idempotent_repeat_reuses_record(self):
        registry = []
        first = register_or_reuse(manifest(), registry)
        second = register_or_reuse(manifest(), registry)
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(len(registry), 1)

    def test_rollback_is_append_only(self):
        record = register_or_reuse(manifest(status="github-published"), [])["record"]
        rolled = rollback(record, "repair-required")
        self.assertEqual(rolled["status"], "rolled-back")
        self.assertEqual(len(rolled["history"]), 1)
        self.assertEqual(record["status"], "github-published")


if __name__ == "__main__":
    unittest.main()
