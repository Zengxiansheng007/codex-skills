import shutil  # Clean long-path fixtures through the extended-length namespace.
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

    def test_deep_unicode_path_longer_than_260_characters_is_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            deep_segment = "公告管理模块测试资产目录" * 10  # Repeat a Unicode segment to build a path exceeding 260 characters.
            deep_dir = Path(directory) / deep_segment  # Construct a deep Unicode path that exceeds MAX_PATH on Windows.
            deep_dir.mkdir(parents=True, exist_ok=True)
            deep_file = deep_dir / "sensitive_config.json"  # Place a file at the deep path.
            value = "synthetic-deep-path-secret-value"
            deep_file.write_text('{"pass' + 'word": "' + value + '"}', encoding="utf-8")
            result = scan(directory)
            self.assertEqual(result["status"], "failed")  # Verify the deep path was reached and scanned.
            self.assertNotIn(value, str(result))  # Ensure the secret value is never echoed.
            self.assertFalse(result["raw_values_persisted"])  # Confirm no raw values are persisted.

    def test_short_root_with_deep_descendant_is_scanned(self):
        directory = tempfile.mkdtemp()  # Keep the scanner input root short while constructing a deep descendant.
        from scripts.scan_sensitive_assets import _normalize_long_path  # Use the production namespace adapter for fixture lifecycle operations.
        try:
            deep_dir = Path(directory) / ("公告" * 40) / ("消息" * 40) / ("创建" * 40)  # Keep each segment legal while the full descendant exceeds MAX_PATH.
            deep_dir = Path(_normalize_long_path(str(deep_dir)))  # Create the deep fixture through the Windows extended-length namespace.
            deep_dir.mkdir(parents=True, exist_ok=True)  # Materialize the synthetic deep descendant without weakening the scan input.
            deep_file = deep_dir / "sensitive_config.json"  # Place a file at the deep path.
            value = "synthetic-short-root-deep-descendant-secret-value"
            deep_file.write_text('{"pass' + 'word": "' + value + '"}', encoding="utf-8")
            result = scan(directory)
            self.assertEqual(result["status"], "failed")  # Verify the deep descendant was reached even though the root is short.
            self.assertNotIn(value, str(result))  # Ensure the secret value is never echoed.
            self.assertFalse(result["raw_values_persisted"])  # Confirm no raw values are persisted.
        finally:
            shutil.rmtree(_normalize_long_path(directory), ignore_errors=False)  # Remove every deep fixture through the same namespace.

    def test_already_prefixed_windows_long_path_is_preserved(self):
        from scripts.scan_sensitive_assets import _normalize_long_path  # Import the normalization helper.
        prefixed = "\\\\?\\C:\\some\\path"  # Construct an already-prefixed extended-length path.
        self.assertEqual(_normalize_long_path(prefixed), prefixed)  # Verify already-prefixed paths are preserved unchanged.

    def test_unc_path_is_normalized_to_extended_unc_form(self):
        from scripts.scan_sensitive_assets import _normalize_long_path, _is_windows  # Import the helpers.
        if not _is_windows():  # Skip UNC normalization on non-Windows platforms.
            self.skipTest("UNC normalization only applies on Windows")  # Skip non-Windows.
        unc_path = "\\\\server\\share\\dir"  # Construct a UNC path.
        normalized = _normalize_long_path(unc_path)  # Normalize the UNC path.
        self.assertTrue(normalized.startswith("\\\\?\\UNC\\"))  # Verify the extended-length UNC prefix is applied.

    def test_short_absolute_windows_root_is_prefixed(self):
        from scripts.scan_sensitive_assets import _normalize_long_path, _is_windows  # Import the helpers.
        if not _is_windows():  # Skip on non-Windows platforms.
            self.skipTest("Extended-length prefix only applies on Windows")  # Skip non-Windows.
        short_path = "C:\\Users"  # Construct a short absolute Windows path.
        normalized = _normalize_long_path(short_path)  # Normalize the short path.
        self.assertTrue(normalized.startswith("\\\\?\\"))  # Verify the extended-length prefix is applied even to short roots.


if __name__ == "__main__":
    unittest.main()
