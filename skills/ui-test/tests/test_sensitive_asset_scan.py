import tempfile
import unittest
from pathlib import Path

from scripts.scan_sensitive_assets import scan


class SensitiveAssetScanTests(unittest.TestCase):
    def test_code_identifiers_and_detection_rules_do_not_false_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "code.py"
            path.write_text('def consume(runtime_key: str): pass\nmarkers = ("pass" + "word=", "coo" + "kie=")\n', encoding="utf-8")
            self.assertEqual(scan(directory)["status"], "clear")

    def test_literal_is_reported_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            value = "synthetic-but-credential-shaped-value"
            path.write_text('{"pass' + 'word": "' + value + '"}', encoding="utf-8")
            result = scan(directory)
            self.assertEqual(result["status"], "failed")
            self.assertNotIn(value, str(result))
            self.assertFalse(result["raw_values_persisted"])

    def test_explicit_environment_reference_metadata_is_not_a_secret_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.py"
            path.write_text(
                'mapping = {"PASSWORD": {"env_ref": "BOPS_ACCOUNT_PASSWORD"}}\n',
                encoding="utf-8",
            )
            self.assertEqual(scan(directory)["status"], "clear")


if __name__ == "__main__":
    unittest.main()
