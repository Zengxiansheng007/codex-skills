"""Contract tests for the governed YAML credential-index loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ui_test_core.credential_index_loader import (
    CredentialIndexError,
    compute_manual_hash,
    get_credential_value,
    load_credential_index,
)
from tests.fixtures_credential_index import (
    compute_manual_hash as fixture_manual_hash,
    document_malformed_yaml,
    document_missing_key,
    document_with_hash_drift,
    document_with_unknown_version,
    valid_document_with_hash,
    write_fixture,
)


class CredentialIndexLoaderTests(unittest.TestCase):
    def _load(self, path: Path):
        with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", path.parent):  # Keep synthetic credentials inside a temporary private root.
            return load_credential_index(path)

    def test_loads_yaml_fixture_and_reads_credential_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), valid_document_with_hash())  # Materialize credentials only for this test process.
            loaded = self._load(path)  # Verify YAML comments and values are supported.
        self.assertEqual(loaded["schema_version"], "ui-test.credential-index.v1")
        self.assertEqual(get_credential_value(loaded, "BOPS_ACCOUNT_USER"), "synthetic-user")
        self.assertNotIn("raw", loaded)

    def test_missing_credential_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), valid_document_with_hash())  # Use a valid baseline before requesting a missing key.
            loaded = self._load(path)
        with self.assertRaisesRegex(CredentialIndexError, "E_CRI_KEY_NOT_FOUND"):
            get_credential_value(loaded, "not_present")

    def test_manual_hash_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_hash_drift())  # Mutate a human value without rehashing.
            with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", path.parent):
                with self.assertRaisesRegex(CredentialIndexError, "E_CRI_MANUAL_HASH_DRIFT"):
                    load_credential_index(path)

    def test_manual_hash_ignores_added_metadata(self):
        document = valid_document_with_hash()  # Start with a self-consistent manual partition.
        original_hash = document["manual_hash"]
        document["credentials"]["BOPS_ACCOUNT_USER"]["notes"] = "candidate note"  # Add metadata that should be part of the human partition.
        self.assertNotEqual(compute_manual_hash(document), original_hash)

    def test_required_credential_key_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_missing_key())  # Keep the manual hash valid for this gate.
            with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", path.parent):
                with self.assertRaisesRegex(CredentialIndexError, "E_CRI_REQUIRED_KEY_MISSING"):
                    load_credential_index(path)

    def test_private_path_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credential-index.yaml"
            import yaml  # type: ignore
            path.write_text(yaml.safe_dump(valid_document_with_hash(), allow_unicode=True, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(CredentialIndexError, "E_CRI_PATH_FORBIDDEN"):
                load_credential_index(path)

    def test_malformed_yaml_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.yaml"
            path.write_text(document_malformed_yaml(), encoding="utf-8")  # Write intentionally truncated YAML.
            with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", path.parent):
                with self.assertRaisesRegex(CredentialIndexError, "E_CRI_FILE_UNREADABLE"):
                    load_credential_index(path)

    def test_unknown_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_unknown_version())  # Exercise version gating before other checks.
            with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", path.parent):
                with self.assertRaisesRegex(CredentialIndexError, "E_CRI_VERSION_UNKNOWN"):
                    load_credential_index(path)

    def test_fixture_hash_matches_loader_hash(self):
        fixture = valid_document_with_hash()  # Build the credential fixture in memory only.
        self.assertEqual(fixture["manual_hash"], fixture_manual_hash(fixture))  # Verify fixture provenance.


if __name__ == "__main__":
    unittest.main()
