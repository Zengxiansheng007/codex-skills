import json
import unittest
from importlib.metadata import version
from pathlib import Path

from scripts.ui_test_core.jcs import RFC8785_IMPLEMENTATION, RFC8785_VERSION, dumps, sha256


class JcsWrapperTests(unittest.TestCase):
    def test_wrapper_uses_locked_implementation(self):
        self.assertEqual(RFC8785_IMPLEMENTATION, "rfc8785")
        self.assertEqual(RFC8785_VERSION, "0.1.4")

    def test_rfc8785_fixture_canonical_bytes(self):
        fixture_path = Path(__file__).with_name("fixtures_jcs.json")
        document = json.loads(fixture_path.read_text(encoding="utf-8"))
        for fixture in document["fixtures"]:
            self.assertEqual(dumps(fixture["input"]).decode("utf-8"), fixture["canonical_utf8"], fixture["id"])

    def test_hash_is_stable_and_key_order_independent(self):
        self.assertEqual(sha256({"b": 2, "a": 1}), sha256({"a": 1, "b": 2}))
        self.assertNotEqual(sha256({"a": 1}), sha256({"a": 2}))

    def test_dependency_lock_and_license_manifest_match_runtime(self):
        root = Path(__file__).parents[1]
        lock = (root / "requirements.lock").read_text(encoding="utf-8")
        self.assertIn("rfc8785==0.1.4", lock)
        self.assertIn("jsonschema==4.26.0", lock)
        self.assertIn("pytest==9.1.1", lock)
        self.assertEqual(version("rfc8785"), "0.1.4")
        self.assertEqual(version("pytest"), "9.1.1")
        licenses = json.loads((root / "dependency-licenses.json").read_text(encoding="utf-8"))
        by_name = {item["name"]: item for item in licenses["dependencies"]}
        self.assertEqual(by_name["rfc8785"]["license_expression"], "Apache-2.0")
        self.assertEqual(by_name["jsonschema"]["license_expression"], "MIT")
        self.assertEqual(by_name["pytest"]["license_expression"], "MIT")


if __name__ == "__main__":
    unittest.main()
