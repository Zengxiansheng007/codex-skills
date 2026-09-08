# CR-20260817-002 - CLW-ST-201 Serial Queue Fixtures And Tests

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / validation |
| Scope | references-and-assets / scripts-and-validation |
| Source | CLW-ST-201; FR-CLW2-001, FR-CLW2-002, FR-CLW2-003, FR-CLW2-004; AC-CLW2-001, AC-CLW2-002, AC-CLW2-003, AC-CLW2-004, AC-CLW2-005 |
| Baseline | Workspace after CR-20260817-001; CLW PH-2 queue helpers existed but had no dedicated fixture suite or deterministic CLW-ST-201 test |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260817-001, CR-20260816-005 |

## Summary

Close CLW-ST-201 by adding a dedicated `assets/fixtures/clw-phase2` fixture
suite (four positive and seven negative cases) and a deterministic
`scripts/test_clw_phase2_serial_runtime.py` that exercises the existing
`development_runtime.py` queue functions against those fixtures plus three
end-to-end serial walks. No `development_runtime.py` change was needed: the
new regression tests did not demonstrate a real contract defect.

## Context And Problem

The CLW-PH-2 serial orchestration contract (see
`references/clw-phase2-serial-orchestration-contract.md`) requires unique
Story IDs, known dependencies, acyclic edges, non-empty FR/AC mappings,
stable priority/ID selection, a single-active gate, a dependency blocker
rule, and a Codex-owned Story completion gate. CR-20260817-001 added the
runtime helpers (`validate_story_graph`, `select_next_story`,
`transition_story_after_review`) and a cross-phase regression suite, but no
dedicated fixture suite or deterministic CLW-ST-201 test existed. PH-2
therefore lacked traceable evidence that the serial contract holds for the
negative matrix (cycle, unknown dependency, duplicate ID, missing FR/AC,
single-active violation, dependency blocker, false Agent completion).

## Decision And Alternatives

Selected a fixture-driven test that reuses the existing runtime helpers and
schemas. The fixtures are plain JSON so they can be inspected and regenerated
without running Python. The test asserts both fixture-level expectations and
three end-to-end serial walks (dependency-aware, blocked dependency, and
review-pending dependency). Rejected: copying the queue runtime into a second
module, modifying `development_runtime.py` without a failing test, and
implementing CLW-ST-202/ST-203 coverage in this round.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `assets/fixtures/clw-phase2/pos-clw2-001-valid-dag.json` | New fixture | Positive: valid DAG accepted by `validate_story_graph` (FR-CLW2-001, AC-CLW2-001) |
| `assets/fixtures/clw-phase2/pos-clw2-002-stable-selection.json` | New fixture | Positive: stable priority/ID selection by `select_next_story` (FR-CLW2-003, AC-CLW2-003) |
| `assets/fixtures/clw-phase2/pos-clw2-003-dependency-completed.json` | New fixture | Positive: completed dependency unlocks downstream selection (FR-CLW2-002, AC-CLW2-002) |
| `assets/fixtures/clw-phase2/pos-clw2-004-story-completion-gate.json` | New fixture | Positive: real Codex completion evaluation transitions Story to passed (FR-CLW2-004, AC-CLW2-005) |
| `assets/fixtures/clw-phase2/neg-clw2-001-cycle.json` | New fixture | Negative: dependency cycle rejected with P0 (FR-CLW2-001, AC-CLW2-001) |
| `assets/fixtures/clw-phase2/neg-clw2-002-unknown-dependency.json` | New fixture | Negative: unknown dependency rejected with P0 (FR-CLW2-001, AC-CLW2-001) |
| `assets/fixtures/clw-phase2/neg-clw2-003-duplicate-id.json` | New fixture | Negative: duplicate Story ID rejected with P0 (FR-CLW2-001, AC-CLW2-001) |
| `assets/fixtures/clw-phase2/neg-clw2-004-missing-fr-ac.json` | New fixture | Negative: missing FR/AC mapping rejected with P1 (FR-CLW2-001, AC-CLW2-001) |
| `assets/fixtures/clw-phase2/neg-clw2-005-single-active.json` | New fixture | Negative: single-active violation rejected with P0 (FR-CLW2-003, AC-CLW2-003) |
| `assets/fixtures/clw-phase2/neg-clw2-006-dependency-blocker.json` | New fixture | Negative: dependency blocker prevents selecting the dependent Story ahead of its prerequisite (FR-CLW2-002, AC-CLW2-002) |
| `assets/fixtures/clw-phase2/neg-clw2-007-false-agent-completion.json` | New fixture | Negative: false Agent completion claim does not transition Story to passed (FR-CLW2-004, AC-CLW2-005) |
| `scripts/test_clw_phase2_serial_runtime.py` | New | Deterministic CLW-ST-201 test: fixture-driven positive/negative matrix plus three end-to-end serial walks |
| `SKILL.md` | Validation | Add `python scripts/test_clw_phase2_serial_runtime.py` to the validation command list |
| `scripts/development_runtime.py` | Unchanged | No runtime change was required; the new tests did not demonstrate a contract defect |

## Requirement Trace

| Story | FR | AC | Evidence |
|---|---|---|---|
| CLW-ST-201 | FR-CLW2-001, FR-CLW2-002, FR-CLW2-003, FR-CLW2-004 | AC-CLW2-001, AC-CLW2-002, AC-CLW2-003, AC-CLW2-004, AC-CLW2-005 | `test_clw_phase2_serial_runtime.py`, `assets/fixtures/clw-phase2/*` |

## Validation

- All existing tests preserved without weakened assertions.
- New CLW-ST-201 tests cover the positive matrix (valid DAG, stable selection, dependency completed, real completion gate) and the negative matrix (cycle, unknown dependency, duplicate ID, missing FR/AC, single-active, dependency blocker, false Agent completion).
- Three end-to-end serial walks exercise DAG validation, stable selection, single-active, the dependency blocker path, the review-pending blocker path and the Codex Story completion gate together.
- `development_runtime.py` was not modified: the new regression tests did not demonstrate a real contract defect.
- No global Skill writes or user-level installation.
- No network access or dependency installation.

## Impact Analysis

- **Scope**: Only the approved `development-system` workspace copy is modified.
- **Risk**: Low — all changes are additive fixtures and a new test file; no runtime behavior change.
- **Rollback**: Delete `assets/fixtures/clw-phase2/*`, `scripts/test_clw_phase2_serial_runtime.py`, this change record, and the SKILL.md validation line.
- **Dependencies**: None — CLW-ST-201 reuses existing `validate_story_graph`, `select_next_story` and `transition_story_after_review` helpers.

## Validation Evidence

- Deterministic test suite: `python scripts/test_clw_phase2_serial_runtime.py` prints `CLW_PHASE2_SERIAL_RUNTIME_OK`.
- Fixture suite: 4 positive and 7 negative JSON fixtures under `assets/fixtures/clw-phase2/`.
- No `development_runtime.py` change was required.

## Safety And Privacy

No prompt, credential, private provider output or production data is embedded in the new fixtures, test or change record. No dependency, global configuration, user-level Skill or external system was modified.

## Risks And Follow-up

The CLW-ST-201 live Attempt was executed after dry-run and exact preauthorization; the adapter produced schema-valid and semantically valid feedback with child exit code 0. Codex independently reran `test_clw_phase2_serial_runtime.py` and observed `CLW_PHASE2_SERIAL_RUNTIME_OK`. CLW-ST-202/ST-203 coverage is intentionally not implemented in this Story record; the PH-2 phase remains open until those Stories and the aggregate CompletionEvaluator pass. No global Skill or user-level installation occurred.
