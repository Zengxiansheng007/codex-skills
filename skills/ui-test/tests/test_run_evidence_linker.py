import copy

from scripts.ui_test_core.execution_data_session import ExecutionDataSession
from scripts.ui_test_core.run_evidence_linker import bind_run_result_v3, build_evidence_index_v2, verify_run_evidence_links
from tests.fixtures_v2 import compiled_v2


def test_snapshot_run_result_and_evidence_are_hash_bound(tmp_path):
    data_path = tmp_path / "test-data.json"
    compiled, _ = compiled_v2(data_path)
    run_root = tmp_path / "runs" / "RUN-001"
    session = ExecutionDataSession(
        run_id="RUN-001",
        build_fingerprint=compiled["manifest"]["build_fingerprint"],
        test_data_path=data_path,
        parameter_manifest=compiled["parameter_manifest"],
        credential_resolver=lambda key: "memory-only",
        sequence_resolver=lambda key: 1,
    )
    session.start()
    session.consume("version")
    snapshot_path = run_root / "resolved-test-data.json"
    session.seal_snapshot(snapshot_path, sealed_at="2026-09-02T01:00:00Z")
    base = {
        "run_id": "RUN-001",
        "case_id": "DEMO-CASE-A",
        "branch_id": "primary",
        "overall_status": "passed",
        "evidence_refs": ["steps/S-001.json"]
    }
    result = bind_run_result_v3(base, run_root=run_root, snapshot_path=snapshot_path)
    evidence = build_evidence_index_v2(result, run_result_ref="run-result.json")
    assert verify_run_evidence_links(result, evidence, run_root=run_root) == []
    tampered = copy.deepcopy(evidence)
    tampered["resolved_test_data_hash"] = "sha256:" + "0" * 64
    assert any("resolved_test_data_hash" in item for item in verify_run_evidence_links(result, tampered, run_root=run_root))

