"""Contract tests for the governed YAML runtime-value loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ui_test_core.runtime_value_loader import (
    RuntimeValueError,
    compute_manual_hash,
    external_env_conflict,
    get_exploration_value,
    get_runtime_value,
    load_runtime_value_index,
    parse_env_ref,
    resolve_value_ref,
)
from scripts.ui_test_core.credential_index_loader import load_credential_index
from tests.fixtures_runtime_value_loader import (
    compute_manual_hash as fixture_manual_hash,
    document_malformed_yaml,
    document_missing_key,
    document_with_hash_drift,
    document_with_malformed_runtime_state,
    document_with_runtime_state_partition,
    document_with_secret_in_runtime_values,
    document_with_unknown_version,
    valid_document_with_hash,
    valid_fixture_path,
    write_fixture,
)
from tests.fixtures_credential_index import valid_document_with_hash as valid_credential_document_with_hash


class RuntimeValueLoaderTests(unittest.TestCase):
    def test_loads_yaml_fixture_and_reads_runtime_value(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Verify YAML comments and values are supported.
        self.assertEqual(loaded["schema_version"], "ui-test.runtime-value-index.v1")
        self.assertEqual(get_runtime_value(loaded, "base_url"), "https://synthetic-test.example.com")
        self.assertEqual(get_runtime_value(loaded, "timeout_ms"), 30000)
        self.assertNotIn("credentials", loaded)  # Runtime index no longer stores credentials.

    def test_reads_exploration_value(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Exploration values are a separate partition.
        self.assertEqual(get_exploration_value(loaded, "create_route"), "/synthetic/create")

    def test_missing_runtime_key_fails_closed(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Use a valid baseline before requesting a missing key.
        with self.assertRaisesRegex(RuntimeValueError, "E_RVI_KEY_NOT_FOUND"):
            get_runtime_value(loaded, "not_present")

    def test_manual_hash_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_hash_drift())  # Mutate a human value without rehashing.
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_MANUAL_HASH_DRIFT"):
                load_runtime_value_index(path)

    def test_manual_hash_ignores_exploration_changes(self):
        document = valid_document_with_hash()  # Start with a self-consistent manual partition.
        original_hash = document["manual_hash"]
        document["exploration_values"]["extra"] = {"value": "/extra", "source_type": "literal", "status": "candidate", "run_id": "RUN-2", "discovered_at": "2026-08-27T00:00:00Z", "scope": "synthetic/test", "evidence_ref": "evidence:extra"}  # Append machine-owned data.
        self.assertEqual(compute_manual_hash(document), original_hash)  # Machine-owned additions cannot cause manual drift.

    def test_required_runtime_key_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_missing_key())  # Keep the manual hash valid for this gate.
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_REQUIRED_KEY_MISSING"):
                load_runtime_value_index(path)

    def test_secret_in_non_credential_partition_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_secret_in_runtime_values())  # Put a token-like value in runtime_values.
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_SECRET_DETECTED") as context:
                load_runtime_value_index(path)
            self.assertNotIn("Bearer", str(context.exception))  # Errors must not echo the sensitive value.

    def test_external_environment_conflict_reports_names_only(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Load a valid file before checking an external conflict.
        conflicts = external_env_conflict(loaded, {"base_url": "https://different.example.com"})  # External values never win.
        self.assertEqual(conflicts, ["base_url"])

    def test_malformed_yaml_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.yaml"
            path.write_text(document_malformed_yaml(), encoding="utf-8")  # Write intentionally truncated YAML.
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_FILE_UNREADABLE"):
                load_runtime_value_index(path)

    def test_unknown_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_unknown_version())  # Exercise version gating before other checks.
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_VERSION_UNKNOWN"):
                load_runtime_value_index(path)

    def test_legacy_env_ref_is_metadata_only(self):
        parsed = parse_env_ref({"env_ref": "SYNTHETIC_TEST_VALUE"})  # Parse the name without reading os.environ.
        self.assertEqual(parsed, {"ok": True, "code": "OK", "env_ref": "SYNTHETIC_TEST_VALUE"})

    def test_new_and_legacy_refs_resolve_from_loaded_index(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Use the file as the only runtime source.
        self.assertEqual(resolve_value_ref(loaded, "value:base_url"), "https://synthetic-test.example.com")
        self.assertEqual(resolve_value_ref(loaded, "env:base_url"), "https://synthetic-test.example.com")  # Legacy env metadata never reads os.environ.
        self.assertEqual(resolve_value_ref(loaded, "exploration:create_route"), "/synthetic/create")

    def test_credential_ref_resolves_in_memory(self):
        loaded = load_runtime_value_index(valid_fixture_path())  # Load runtime values from the governed runtime index.
        with tempfile.TemporaryDirectory() as directory:
            credential_path = Path(directory) / "credential-index.yaml"
            import yaml  # type: ignore
            credential_path.write_text(yaml.safe_dump(valid_credential_document_with_hash(), allow_unicode=True, sort_keys=False), encoding="utf-8")
            with patch("scripts.ui_test_core.credential_index_loader.PRIVATE_RUNTIME_ROOT", credential_path.parent):  # Keep synthetic credentials inside a temporary private root.
                credentials = load_credential_index(credential_path)  # Load credentials from the separate private credential index.
        loaded["credentials"] = credentials["credentials"]  # Merge only in process memory for reference resolution.
        self.assertEqual(resolve_value_ref(loaded, "credential:BOPS_ACCOUNT_USER"), "synthetic-user")

    def test_credential_ref_is_not_resolved_from_process_environment(self):
        loaded = {"runtime_values": {}, "credentials": {}, "exploration_values": {}}
        with self.assertRaisesRegex(RuntimeValueError, "E_ENV_REF_UNRESOLVED"):
            resolve_value_ref(loaded, "env:BOPS_ACCOUNT_PASSWORD")

    def test_fixture_hash_matches_loader_hash(self):
        fixture = valid_document_with_hash()  # Build the fixture in memory instead of persisting credential samples.
        self.assertEqual(fixture["manual_hash"], fixture_manual_hash(fixture))  # Verify fixture provenance.

    def test_runtime_state_partition_is_exposed_without_changing_manual_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_runtime_state_partition())  # Persist a synthetic index with mutable state.
            without_state = valid_document_with_hash()  # The same manual partition without runtime_state.
            loaded = load_runtime_value_index(path)  # Load the index that carries runtime_state.
            self.assertIn("runtime_state", loaded)  # The loader exposes the validated mutable partition.
            self.assertEqual(loaded["runtime_state"]["popup_announcement_version"]["next_value"], 2)  # The prior allocation advanced the counter.
            self.assertEqual(loaded["manual_hash"], without_state["manual_hash"])  # Machine-maintained state never changes the protected human hash.

    def test_runtime_state_does_not_change_manual_hash_value(self):
        document = valid_document_with_hash()  # Start with a self-consistent manual partition.
        original_hash = document["manual_hash"]
        document["runtime_state"] = {"seq": {"next_value": 1, "scope": "s", "description": "Synthetic sequence", "allocations": []}}  # Add valid initialized machine state.
        self.assertEqual(compute_manual_hash(document), original_hash)  # compute_manual_hash must never fold runtime_state.

    def test_malformed_runtime_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(Path(directory), document_with_malformed_runtime_state())  # Persist a non-positive counter.
            with self.assertRaisesRegex(RuntimeValueError, "runtime_state"):  # The schema or runtime-state gate names the malformed partition.
                load_runtime_value_index(path)  # The loader rejects malformed machine state before returning.

    def test_runtime_state_secret_evidence_ref_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            document = valid_document_with_hash()  # Keep the manual partition valid for this gate.
            document["runtime_state"] = {"seq": {"next_value": 2, "scope": "s", "description": "Synthetic sequence", "allocations": [{"value": 1, "run_id": "RUN-LEAK", "allocated_at": "2026-08-27T00:00:00Z", "evidence_ref": "Bearer " + "x" * 30}]}}  # Put a credential-like evidence ref in the mutable ledger.
            path = write_fixture(Path(directory), document)
            with self.assertRaisesRegex(RuntimeValueError, "E_RVI_RUNTIME_STATE_SECRET_DETECTED"):
                load_runtime_value_index(path)  # Mutable state must never persist credential-like references.


if __name__ == "__main__":
    unittest.main()
