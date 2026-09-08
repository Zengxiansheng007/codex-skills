# CR-20260817-004 - CLW-ST-203 Failure/Resource Budgets, Circuit And Phase Completion

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / validation |
| Scope | scripts-and-validation |
| Source | CLW-ST-203; FR-CLW2-008, FR-CLW2-009, FR-CLW2-010; AC-CLW2-010, AC-CLW2-011, AC-CLW2-012, AC-CLW2-013, AC-CLW2-014 |
| Baseline | Workspace after CR-20260817-003; CLW-ST-201 and CLW-ST-202 accepted |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260817-001, CR-20260817-002, CR-20260817-003 |

## Summary

Close CLW-ST-203 by extending the dedicated PH-2 serial test with dedicated coverage for the three-state circuit (CLOSED/OPEN/HALF_OPEN), failure fingerprint budgets, invalid-feedback budgets, timeout recovery, resource budgets, round limits, the verified-progress evaluator, and the Phase completion gate. The test exercises every AC-CLW2-010 through AC-CLW2-014 negative and positive case using the existing `advance_circuit`, `authorize_half_open`, `evaluate_resources`, `evaluate_phase_completion`, `evaluate_verified_progress`, `failure_fingerprint`, `select_next_story`, and `transition_story_after_review` helpers. No `development_runtime.py` change was needed: the new regression tests did not demonstrate a real contract defect.

## Context And Problem

The CLW-PH-2 serial orchestration contract (see `references/clw-phase2-serial-orchestration-contract.md`) and the long-task-runtime-contract require three-state circuit breaking (CLOSED/OPEN/HALF_OPEN), no-progress budgets (three rounds open), failure fingerprint budgets (third enters repair, fifth opens), invalid-feedback budgets (third opens), timeout recovery (first permits recovery, later blocks or permits bounded takeover), resource budgets, round limits (ten max), and Phase completion that requires every Story, AC, feedback, evidence, QA, drift, permission, risk and Codex review gate. CR-20260817-002 and CR-20260817-003 closed CLW-ST-201 and CLW-ST-202, but CLW-ST-203 coverage for budgets, circuit and completion was still missing.

## Decision And Alternatives

Selected inline test functions (like the existing CLW-ST-202 recovery test) rather than separate JSON fixtures. The budget and circuit tests require multi-step state accumulation (e.g., three no-progress rounds, five failure fingerprints) that is more clearly expressed in imperative Python than in static JSON. The `test_fixture_directory_coverage` test still guards that every JSON fixture in `assets/fixtures/clw-phase2` is exercised. Rejected: modifying `development_runtime.py` without a failing test, creating separate JSON fixtures for multi-step scenarios, and relaxing any completion or budget gate.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/test_clw_phase2_serial_runtime.py` | Module docstring | Update to note CLW-ST-203 coverage is hosted in this file |
| `scripts/test_clw_phase2_serial_runtime.py` | Imports | Add `advance_circuit`, `authorize_half_open`, `evaluate_completion`, `evaluate_phase_completion`, `evaluate_resources`, `evaluate_verified_progress`, `failure_fingerprint` |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_no_progress_circuit` | New: AC-CLW2-010 three no-progress rounds open circuit |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_verified_progress_resets_no_progress` | New: AC-CLW2-010 verified progress resets no-progress counter |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_failure_fingerprint_repair_and_open` | New: AC-CLW2-011 third fingerprint enters repair, fifth opens |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_failure_fingerprint_different_does_not_stack` | New: AC-CLW2-011 different fingerprints do not stack |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_invalid_feedback_opens_circuit` | New: AC-CLW2-011 third invalid feedback opens circuit |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_timeout_recovery_and_block` | New: AC-CLW2-012 first timeout recovers, later blocks or takeover |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_half_open_probe` | New: AC-CLW2-013 HALF_OPEN requires Codex reauth, one probe |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_resource_budget_within_and_exceeded` | New: AC-CLW2-014 resource within/exceeded budget |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_phase_completion_gate_positive` | New: AC-CLW2-014 Phase completion positive gate |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_phase_completion_gate_negative_matrix` | New: AC-CLW2-014 Phase completion negative matrix |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_false_completion_signals` | New: AC-CLW2-014 queue empty, timeout, circuit OPEN, resource exhaustion, Agent claim never completion |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_verified_progress_evaluator` | New: AC-CLW2-010 evaluate_verified_progress requires all four checks |
| `scripts/test_clw_phase2_serial_runtime.py` | `test_st203_round_limit` | New: AC-CLW2-010 ten round limit opens circuit |
| `scripts/test_clw_phase2_serial_runtime.py` | `main` | Add all ST-203 test calls |
| `scripts/development_runtime.py` | Unchanged | No runtime change was required; the new tests did not demonstrate a contract defect |

## Requirement Trace

| Story | FR | AC | Evidence |
|---|---|---|---|
| CLW-ST-203 | FR-CLW2-008 | AC-CLW2-010 | `test_st203_no_progress_circuit`, `test_st203_verified_progress_resets_no_progress`, `test_st203_verified_progress_evaluator`, `test_st203_round_limit` |
| CLW-ST-203 | FR-CLW2-008 | AC-CLW2-011 | `test_st203_failure_fingerprint_repair_and_open`, `test_st203_failure_fingerprint_different_does_not_stack`, `test_st203_invalid_feedback_opens_circuit` |
| CLW-ST-203 | FR-CLW2-008 | AC-CLW2-012 | `test_st203_timeout_recovery_and_block` |
| CLW-ST-203 | FR-CLW2-009 | AC-CLW2-013 | `test_st203_half_open_probe` |
| CLW-ST-203 | FR-CLW2-010 | AC-CLW2-014 | `test_st203_resource_budget_within_and_exceeded`, `test_st203_phase_completion_gate_positive`, `test_st203_phase_completion_gate_negative_matrix`, `test_st203_false_completion_signals` |

## Validation

- All existing tests preserved without weakened assertions.
- New CLW-ST-203 tests cover: no-progress circuit (three rounds), verified progress reset, failure fingerprint (third repair, fifth open), different fingerprints, invalid feedback (third opens), timeout recovery and block, HALF_OPEN probe, resource budget (within and exceeded), Phase completion (positive and negative matrix), false completion signals (queue empty, timeout, circuit OPEN, resource exhaustion, Agent claim), verified progress evaluator, and round limit.
- `development_runtime.py` was not modified: the new regression tests did not demonstrate a contract defect.
- No global Skill writes or user-level installation.
- No network access or dependency installation.

## Impact Analysis

- **Scope**: Only the approved `development-system` workspace copy is modified.
- **Risk**: Low — all changes are additive test functions; no runtime behavior change.
- **Rollback**: Remove the ST-203 test functions and imports from `scripts/test_clw_phase2_serial_runtime.py` and delete this change record.
- **Dependencies**: None — CLW-ST-203 reuses existing `advance_circuit`, `authorize_half_open`, `evaluate_resources`, `evaluate_phase_completion`, `evaluate_verified_progress`, `failure_fingerprint`, `select_next_story`, and `transition_story_after_review` helpers.

## Validation Evidence

- Deterministic test suite: `python scripts/test_clw_phase2_serial_runtime.py` prints `CLW_PHASE2_SERIAL_RUNTIME_OK`.
- No `development_runtime.py` change was required.

## Safety And Privacy

No prompt, credential, private provider output or production data is embedded in the new test or change record. No dependency, global configuration, user-level Skill or external system was modified.

## Risks And Follow-up

The CLW-ST-203 live Attempt was executed after dry-run and exact preauthorization. The PH-2 phase completion gate remains owned by Codex; the test only verifies the deterministic runtime helpers. A later read-only Codex validation pass is still required before the PH-2 aggregate gate. No global Skill or user-level installation occurred.
