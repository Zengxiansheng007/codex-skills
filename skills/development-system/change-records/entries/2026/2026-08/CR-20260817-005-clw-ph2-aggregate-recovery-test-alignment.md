# CR-20260817-005 - CLW PH-2 Aggregate Recovery Test Alignment

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | repair / validation |
| Scope | scripts-and-validation |
| Source | CLW-PH-2 aggregate CompletionEvaluator; FR-CLW2-005 through FR-CLW2-007; AC-CLW2-006 through AC-CLW2-009 |
| Baseline | Workspace after CR-20260817-004; strict event/snapshot recovery contract active |
| Author | Codex QA repair after Claude Story execution; Codex owns completion authority |
| Related Records | CR-20260817-003, CR-20260817-004 |

## Summary

Align the cross-phase deterministic test with the strict ST-202 recovery contract. The old test built a snapshot at sequence zero, appended an event, and still expected reconciliation to pass. The repaired test asserts that this stale snapshot is rejected with `history:snapshot-sequence`, then builds an event-aligned snapshot using the persisted event sequence and hash and verifies successful reconciliation.

## Root Cause

ST-202 correctly tightened recovery so an aggregate snapshot must identify the latest durable event. `test_clw_phase2_phase4_runtime.py` retained the pre-ST-202 expectation and therefore treated a real crash gap as valid. The runtime was correct; the aggregate test was stale.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/test_clw_phase2_phase4_runtime.py` | `test_phase2` | Reject stale pre-event snapshot and accept only the event-aligned snapshot |
| `scripts/development_runtime.py` | Unchanged | Strict recovery behavior preserved |

## Validation

- `test_clw_phase2_phase4_runtime.py`: `CLW_PHASE2_PHASE4_RUNTIME_OK`.
- `test_clw_phase2_serial_runtime.py`: `CLW_PHASE2_SERIAL_RUNTIME_OK`.
- `test_development_runtime.py`: `DEVELOPMENT_RUNTIME_OK`.
- `validate_development_system.py`: accepted, P0/P1/P2 = 0/0/0.

## Impact And Rollback

The repair changes only a deterministic test in the approved workspace copy. It does not alter runtime behavior, schemas, global Skills, dependencies, network state, or completion authority. Rollback is limited to restoring the prior test block, which is not recommended because it would re-accept a stale snapshot.

## Context And Problem

After ST-202 tightened aggregate recovery, one cross-phase test still expected a stale pre-event snapshot to pass. That stale expectation conflicted with the active recovery contract.

## Decision And Alternatives

Decision: update the test to reject the stale snapshot and accept only an event-aligned snapshot. Alternative rejected: loosening runtime recovery, because the stricter runtime behavior was the correct contract.

## Impact Analysis

The change affects deterministic test expectations only. It improves recovery evidence fidelity without changing runtime behavior or downstream Agent authority.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| PH-2/PH-4 runtime | `python scripts/test_clw_phase2_phase4_runtime.py` | passed | `CLW_PHASE2_PHASE4_RUNTIME_OK` |
| PH-2 serial runtime | `python scripts/test_clw_phase2_serial_runtime.py` | passed | `CLW_PHASE2_SERIAL_RUNTIME_OK` |
| Development runtime | `python scripts/test_development_runtime.py` | passed | `DEVELOPMENT_RUNTIME_OK` |
| Development-system validator | `python scripts/validate_development_system.py` | passed | accepted, P0/P1/P2 = 0/0/0 |

## Safety And Privacy

No secrets, production data, external writes, global Skill writes, dependency installation or live Agent execution were introduced.

## Risks And Follow-up

Future aggregate recovery changes must keep the stale-snapshot rejection fixture aligned with the runtime contract.
