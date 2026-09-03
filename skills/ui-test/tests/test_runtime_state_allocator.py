"""Unit, contract, negative and concurrency tests for the governed runtime-state allocator."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

import yaml

from scripts.ui_test_core.runtime_state_allocator import RuntimeStateError, allocate_runtime_sequence, initialize_runtime_sequence
from scripts.ui_test_core.runtime_value_loader import RuntimeValueError, compute_manual_hash, load_runtime_value_index
from tests.fixtures_runtime_value_loader import valid_document_with_hash, write_fixture


def _index(directory: Path) -> Path:
    return write_fixture(Path(directory), valid_document_with_hash())  # Use a synthetic no-credential index.


def _assert_fail_closed(testcase, path, plant):
    """Run an allocation against a planted malformed index and assert it fails closed without side effects."""
    before = path.read_text(encoding="utf-8")  # Snapshot the file before the attempted allocation.
    with testcase.assertRaises((RuntimeStateError, RuntimeValueError)) as context:  # Reject at the loader or allocator layer.
        allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")
    testcase.assertEqual(path.read_text(encoding="utf-8"), before)  # A rejected allocation must not mutate the file.
    testcase.assertFalse((path.with_name(path.name + ".lock")).exists())  # No lock is left behind after a rejection.
    return str(context.exception)


class RuntimeStateAllocatorUnitTests(unittest.TestCase):
    """Prove the required allocation semantics: first 1, second 2, single allocation per run."""

    def test_first_allocation_returns_one_and_advances_counter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            result = allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1", description="popup version")  # First allocation.
            self.assertEqual(result["allocated_value"], 1)  # The first allocated version is 1.
            self.assertEqual(result["next_value"], 2)  # The stored counter advanced to previous + 1.
            loaded = load_runtime_value_index(path)  # Read back the atomically replaced file.
            entry = loaded["runtime_state"]["popup_announcement_version"]
            self.assertEqual(entry["next_value"], 2)  # The persisted counter reflects the allocation.
            self.assertEqual(entry["allocations"][-1]["value"], 1)  # The append-only ledger records the value handed out.
            self.assertEqual(entry["allocations"][-1]["run_id"], "RUN-1")  # The allocation is bound to this run.

    def test_second_allocation_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            first = allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate 1.
            second = allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-2", scope="synthetic/test", evidence_ref="evidence:run-2")  # Allocate 2 under a new run.
            self.assertEqual(first["allocated_value"], 1)
            self.assertEqual(second["allocated_value"], 2)  # Each later allocation returns previous + 1.

    def test_allocation_preserves_manual_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            before = load_runtime_value_index(path)["manual_hash"]  # Capture the human partition before allocation.
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate once.
            after = load_runtime_value_index(path)  # Read back the final file.
            self.assertEqual(after["manual_hash"], before)  # The human-maintained hash is unchanged.

    def test_lock_file_is_released_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate once.
            self.assertFalse((path.with_name(path.name + ".lock")).exists())  # The sibling lock file is removed after a successful allocation.

    def test_explicit_initialization_persists_one_without_allocating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            result = initialize_runtime_sequence(path, "popup_announcement_version", scope="synthetic/test", description="popup version")  # Store 1 as the first future value.
            self.assertEqual(result["status"], "initialized")  # Initialization is explicit and observable.
            entry = load_runtime_value_index(path)["runtime_state"]["popup_announcement_version"]
            self.assertEqual(entry["next_value"], 1)  # The persisted initial version is 1.
            self.assertEqual(entry["allocations"], [])  # Initialization does not consume the first version.

    def test_explicit_initialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            initialize_runtime_sequence(path, "popup_announcement_version", scope="synthetic/test", description="popup version")  # Initialize once.
            repeated = initialize_runtime_sequence(path, "popup_announcement_version", scope="synthetic/test", description="popup version")  # Repeat the same declaration.
            self.assertEqual(repeated["status"], "existing")  # Repeated initialization preserves state without allocating.
            self.assertEqual(repeated["next_value"], 1)  # Version 1 remains available for the first creation.


class RuntimeStateAllocatorContractTests(unittest.TestCase):
    """Contract tests for the schema and loader integration of the allocator."""

    def test_persisted_entry_passes_loader_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1", description="popup version")  # Allocate once.
            loaded = load_runtime_value_index(path)  # The loader must accept the allocator's persisted document.
            self.assertEqual(loaded["runtime_state"]["popup_announcement_version"]["description"], "popup version")  # Description is persisted.

    def test_allocated_at_is_utc_iso8601(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate once.
            entry = load_runtime_value_index(path)["runtime_state"]["popup_announcement_version"]
            self.assertTrue(entry["allocations"][-1]["allocated_at"].endswith("Z"))  # The ledger timestamp is UTC ISO-8601.

    def test_manual_partition_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Prepare a competing human partition.
            document["runtime_values"]["timeout_ms"]["value"] = 90000
            document["manual_hash"] = compute_manual_hash(document)  # Keep the human hash internally valid.
            from unittest.mock import patch
            original = load_runtime_value_index
            with patch("scripts.ui_test_core.runtime_state_allocator.load_runtime_value_index", side_effect=[original(path), {"manual_hash": document["manual_hash"]}, original(path), {"manual_hash": document["manual_hash"]}, original(path)]):
                with self.assertRaisesRegex(RuntimeStateError, "E_RVS_MANUAL_PARTITION_DRIFT"):
                    allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # A moved human partition cannot be overwritten.


class RuntimeStateAllocatorNegativeTests(unittest.TestCase):
    """Negative tests for malformed state, duplicate runs and non-positive values."""

    def test_duplicate_run_allocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate once for this run.
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_DUPLICATE_RUN_ALLOCATION"):
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # The same run must never allocate the same sequence twice.

    def test_duplicate_run_is_rejected_after_an_intervening_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Allocate version 1.
            allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-2", scope="synthetic/test", evidence_ref="evidence:run-2")  # Allocate version 2 under another run.
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_DUPLICATE_RUN_ALLOCATION"):
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1-retry")  # The full ledger blocks a non-adjacent retry.
            entry = load_runtime_value_index(path)["runtime_state"]["popup_announcement_version"]
            self.assertEqual(entry["next_value"], 3)  # The rejected retry does not consume version 3.

    def test_non_positive_existing_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Read the synthetic document.
            document["runtime_state"] = {"popup_announcement_version": {"next_value": 0, "scope": "s", "description": "Broken sequence", "allocations": []}}  # Plant a non-positive counter.
            path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
            message = _assert_fail_closed(self, path, "non-positive")  # A non-positive counter fails closed before allocation.
            self.assertIn("runtime_state", message)  # The rejection names the runtime-state partition.

    def test_malformed_runtime_state_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Read the synthetic document.
            document["runtime_state"] = "not-an-object"  # Plant a malformed partition type.
            path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
            message = _assert_fail_closed(self, path, "scalar-partition")  # A scalar partition fails closed.
            self.assertIn("runtime_state", message)  # The rejection names the malformed partition.

    def test_malformed_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            document = yaml.safe_load(path.read_text(encoding="utf-8"))  # Read the synthetic document.
            document["runtime_state"] = {"popup_announcement_version": "not-a-dict"}  # Plant a malformed entry.
            path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
            message = _assert_fail_closed(self, path, "scalar-entry")  # A non-object entry fails closed.
            self.assertIn("popup_announcement_version", message)  # The rejection names the affected sequence key.

    def test_missing_index_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.yaml"  # A non-existent index.
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_FILE_MISSING"):
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Missing indexes fail before touching the lock.

    def test_credential_evidence_ref_is_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_EVIDENCE_REF_INVALID") as context:
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="Bearer " + "x" * 30)  # Credential-like evidence refs must be rejected.
            self.assertNotIn("Bearer", str(context.exception))  # The issue is redacted.

    def test_empty_sequence_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_SEQUENCE_KEY_INVALID"):
                allocate_runtime_sequence(path, "   ", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # Empty sequence keys are rejected.

    def test_failed_allocation_keeps_original_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            before = path.read_text(encoding="utf-8")  # Snapshot the original file bytes.
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_EVIDENCE_REF_INVALID"):
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="Bearer " + "x" * 30)  # A credential-like evidence ref is rejected before any write.
            self.assertEqual(path.read_text(encoding="utf-8"), before)  # Failed validation must not mutate the target.
            self.assertFalse((path.with_name(path.name + ".lock")).exists())  # No lock is left behind after a pre-write failure.


class RuntimeStateAllocatorConcurrencyTests(unittest.TestCase):
    """Concurrency tests proving lock contention fail-closed and allocation uniqueness."""

    def test_lock_contention_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            lock_path = path.with_name(path.name + ".lock")  # The sibling lock file path.
            with open(lock_path, "w", encoding="utf-8"):  # Simulate another run already holding the lock.
                pass
            with self.assertRaisesRegex(RuntimeStateError, "E_RVS_LOCK_CONTENTION"):
                allocate_runtime_sequence(path, "popup_announcement_version", run_id="RUN-1", scope="synthetic/test", evidence_ref="evidence:run-1")  # A held lock fails closed rather than waiting.
            self.assertTrue(lock_path.exists())  # The contention path does not steal the existing lock.

    def test_concurrent_allocations_produce_unique_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            run_count = 8
            results: list[int] = []
            errors: list[Exception] = []
            barrier = threading.Barrier(run_count)  # Release all workers at once to maximize the race window.

            def worker(run_id: str) -> None:
                barrier.wait()  # Start every worker simultaneously.
                last_error: Exception | None = None
                for _ in range(200):  # Bounded retry simulates a real concurrent client that backs off on contention.
                    try:
                        result = allocate_runtime_sequence(path, "popup_announcement_version", run_id=run_id, scope="synthetic/test", evidence_ref=f"evidence:{run_id}")  # Allocate under a unique run.
                        results.append(result["allocated_value"])  # Collect only the winning allocation.
                        return
                    except RuntimeStateError as error:
                        last_error = error  # A losing round fails closed on the lock and is retried.
                errors.append(last_error)  # A worker that never won after the bounded retry reports its last failure.

            runs = [f"RUN-CONC-{i:02d}" for i in range(run_count)]  # Eight concurrent runs.
            threads = [threading.Thread(target=worker, args=(run_id,)) for run_id in runs]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])  # Every worker eventually allocated within the bounded retry.
            self.assertEqual(len(results), run_count)  # All concurrent runs succeeded.
            self.assertEqual(len(set(results)), run_count)  # Every allocation value is unique across concurrent runs.
            self.assertEqual(sorted(results), list(range(1, run_count + 1)))  # The winners cover a contiguous sequence from 1.
            loaded = load_runtime_value_index(path)  # Verify the final persisted state.
            self.assertEqual(loaded["runtime_state"]["popup_announcement_version"]["next_value"], run_count + 1)  # The counter advanced exactly once per allocation.
            self.assertEqual(loaded["runtime_state"]["popup_announcement_version"]["allocations"][-1]["value"], run_count)  # The ledger records the last allocation's value.

    def test_concurrent_duplicate_run_is_never_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _index(Path(directory))
            run_id = "RUN-DUP-CONC-01"  # The same run id attempted concurrently.
            wins: list[int] = []
            losers: list[Exception] = []
            barrier = threading.Barrier(6)  # Release the duplicate attempts at once.

            def worker() -> None:
                barrier.wait()
                try:
                    result = allocate_runtime_sequence(path, "popup_announcement_version", run_id=run_id, scope="synthetic/test", evidence_ref=f"evidence:{run_id}")  # Attempt the same run id.
                    wins.append(result["allocated_value"])  # At most one attempt may win.
                except RuntimeStateError as error:
                    losers.append(error)  # All later attempts must fail closed.

            threads = [threading.Thread(target=worker) for _ in range(6)]  # Six concurrent duplicate-run attempts.
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(len(wins), 1)  # Exactly one allocation succeeds for a given run id.
            self.assertEqual(len(losers), 5)  # The remaining attempts are rejected by lock contention or duplicate-run detection.
            self.assertTrue(all(("E_RVS_LOCK_CONTENTION" in str(error)) or ("E_RVS_DUPLICATE_RUN_ALLOCATION" in str(error)) for error in losers))  # Rejection reasons are governed and fail-closed.


if __name__ == "__main__":
    unittest.main()
