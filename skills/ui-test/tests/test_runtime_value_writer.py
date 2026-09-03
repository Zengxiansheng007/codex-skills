"""Contract tests for append-only exploration writes and automatic promotion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.ui_test_core.runtime_value_loader import compute_manual_hash, load_runtime_value_index
from scripts.ui_test_core.runtime_value_writer import (
    RuntimeValueWriteError,
    append_exploration_value,
    promote_exploration_value,
)
from tests.fixtures_runtime_value_loader import valid_document_with_hash, write_fixture


class RuntimeValueWriterTests(unittest.TestCase):
    def _path(self, directory: str) -> Path:
        return write_fixture(Path(directory), valid_document_with_hash())  # Use a synthetic no-credential index.

    def test_append_preserves_manual_partition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            before = load_runtime_value_index(path)["manual_hash"]  # Capture the human partition before writing.
            result = append_exploration_value(path, "new_route", "/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:new")  # Append only machine-owned data.
            after = load_runtime_value_index(path)  # Read back the atomically replaced file.
            self.assertEqual(result["status"], "candidate")
            self.assertEqual(before, after["manual_hash"])  # Human values must remain byte-independent and semantically unchanged.
            self.assertEqual(after["exploration_values"]["new_route"]["status"], "candidate")

    def test_promote_candidate_to_active(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            append_exploration_value(path, "new_route", "https://test.example.com/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:new", allowed_hosts={"test.example.com"})  # Create a URL candidate on an approved host.
            result = promote_exploration_value(path, "new_route", allowed_hosts={"test.example.com"})  # Codex promotion uses deterministic gates.
            loaded = load_runtime_value_index(path)
            self.assertEqual(result["status"], "active")
            self.assertEqual(loaded["exploration_values"]["new_route"]["status"], "active")

    def test_manual_key_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_MANUAL_KEY_COLLISION"):
                append_exploration_value(path, "base_url", "/collision", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:collision")  # Never shadow a human value.

    def test_duplicate_exploration_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_EXPLORATION_KEY_EXISTS"):
                append_exploration_value(path, "create_route", "/duplicate", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:duplicate")  # Avoid silent machine-value replacement.

    def test_unapproved_url_host_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_HOST_NOT_ALLOWED"):
                append_exploration_value(path, "new_route", "https://other.example.com/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:host", allowed_hosts={"test.example.com"})  # Enforce host scope before persistence.

    def test_concurrent_manual_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_CONCURRENT_MODIFICATION"):
                append_exploration_value(path, "new_route", "/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:new", expected_manual_hash="sha256:" + "0" * 64)  # Simulate a stale writer.

    def test_writer_rechecks_manual_partition_without_caller_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Prepare the competing human partition.
            document["runtime_values"]["timeout_ms"]["value"] = 90000
            document["manual_hash"] = compute_manual_hash(document)
            original_loader = load_runtime_value_index
            with patch("scripts.ui_test_core.runtime_value_writer.load_runtime_value_index", side_effect=[original_loader(path), {"manual_hash": document["manual_hash"]}]):
                with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_CONCURRENT_MODIFICATION"):
                    append_exploration_value(path, "new_route", "/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:new")  # A changed manual partition cannot be overwritten.

    def test_secret_candidate_is_rejected_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_SECRET_DETECTED") as context:
                append_exploration_value(path, "new_value", "Bearer " + "x" * 30, run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:secret")  # Keep credential-like values out of exploration.
            self.assertNotIn("Bearer", str(context.exception))  # The issue is redacted.

    def test_failed_write_keeps_original_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._path(directory)
            before = path.read_text(encoding="utf-8")  # Snapshot the original file bytes.
            with self.assertRaisesRegex(RuntimeValueWriteError, "E_RVI_HOST_NOT_ALLOWED"):
                append_exploration_value(path, "new_route", "https://other.example.com/new", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:host", allowed_hosts={"test.example.com"})  # Reject before atomic replacement.
            self.assertEqual(path.read_text(encoding="utf-8"), before)  # Failed validation must not mutate the target.


if __name__ == "__main__":
    unittest.main()
