import json
import tempfile
import unittest
from pathlib import Path

from landed_review import build_report


def baseline():
    return {
        "anchorId": "REQ-EXAMPLE-001",
        "artifacts": [{"artifactId": "PRD-1", "version": "1.0.0", "contentHash": "a" * 64}],
    }


def observed(**kwargs):
    value = {"artifacts": [{"artifactId": "PRD-1", "version": "1.0.0", "contentHash": "a" * 64}], "evidence": [{"id": "E1"}], "implementation": {}}
    value.update(kwargs)
    return value


class LandedReviewTests(unittest.TestCase):
    def test_no_drift_is_reviewed(self):
        result = build_report(baseline(), observed())["result"]
        self.assertEqual(result["classification"], "no-drift")
        self.assertFalse(result["retestRequired"])

    def test_implementation_drift_creates_candidate(self):
        current = observed()
        current["artifacts"][0]["contentHash"] = "b" * 64
        current["artifacts"][0]["changeReason"] = "implementation differs"
        result = build_report(baseline(), current)["result"]
        self.assertEqual(result["classification"], "implementation-drift")
        self.assertEqual(result["candidateRevisions"][0]["approvalStatus"], "need-review")

    def test_semantic_change_requires_review(self):
        result = build_report(baseline(), observed(implementation={"semanticRequirementChange": True}))["result"]
        self.assertEqual(result["classification"], "requirements-review")
        self.assertEqual(result["rcStatus"], "not-generated")

    def test_missing_evidence_blocks(self):
        result = build_report(baseline(), observed(evidence=[]))["result"]
        self.assertEqual(result["classification"], "insufficient-evidence")
        self.assertEqual(result["status"], "blocked")

    def test_sensitive_value_blocks_without_echoing_secret(self):
        current = observed()
        current["implementation"] = {"notes": "pass" + "word" + "=do-not-store"}
        report = build_report(baseline(), current)
        self.assertEqual(report["result"]["status"], "blocked")
        self.assertEqual(report["result"]["classification"], "invalid-or-sensitive-input")
        self.assertNotIn("do-not-store", json.dumps(report))

    def test_baseline_is_not_modified(self):
        original = baseline()
        before = json.dumps(original, sort_keys=True)
        build_report(original, observed())
        self.assertEqual(json.dumps(original, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
