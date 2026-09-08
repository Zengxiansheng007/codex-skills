# CR-20260815-003 - Completion Evidence And State Alignment

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | fixed / validation / governance / downstream handoff |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | research decision gate DS-REPAIR-001 and DS-REPAIR-002; Claude timeout review; Codex regression review |
| Baseline | Workspace before this repair; pre-repair SHA-256 captured for affected files; canonical-source retained under `install-candidate/canonical-source/` |
| Author | mixed Claude and Codex; Codex owns review and completion authority |
| Related Records | CR-20260815-001, CR-20260815-002 |

## Summary

Close the remaining completion-evidence and governed-state defects found after the full runtime implementation. Completion is now bound to external validation evidence for the actual feedback object, and every workspace state contract exactly matches the 11-state confirmed requirements baseline.

## Context And Problem

The live-loop regression exposed four linked completion failures: a nominal feedback-valid signal did not prove schema validation, the supplied feedback was not hash-bound to the validator result, schema errors could be treated as valid, and strict negative coverage was missing. The workspace also contained a twelfth `cancelled-or-superseded` runtime state absent from DS-PSR-001.

Claude timed out during the repair round after changing the approved workspace. Codex reviewed the partial result, removed an unauthorized generated `run_tests.bat`, corrected the missing-hash error contract, completed the state-model repair and reran the gates. No user-level Skill directory or external system was changed.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/development_runtime.py` | feedback validation / state transitions | Require canonical hash-bound evidence and remove undeclared cancellation transitions. |
| `scripts/build_refactor_reports.py` | RTM/completion report generation | Generate hash-bound evaluation input, run CompletionEvaluator and separate workspace completion from installation approval. |
| `scripts/test_development_runtime.py` | regression tests | Add exact 11-state, bare-boolean, missing-evidence, hash, schema-error and negative-fixture semantics. |
| `scripts/test_full_refactor_contract.py` | schema and fixture inventory | Assert exact state parity and include the undeclared-state fixture. |
| `scripts/validate_development_system.py` | strong gates | Require the new fixture and parse runtime/schema state enums against DS-PSR-001. |
| `schemas/completion-evaluation.schema.json` | feedbackValidation | Require schema reference, validator, hash, zero errors and timestamp. |
| `schemas/runtime-state.schema.json` | state enum | Reduce runtime states to the confirmed 11. |
| `schemas/requirement-anchor.schema.json` | nextState enum | Align anchor next-state values and order with the confirmed 11. |
| `references/state-and-completion-contract.md` | state/completion rules | Document hash-bound completion and lifecycle cancellation outside runtime state. |
| `references/phase1-boundary-contract.md` | final state table | Cover all 11 governed states and remove the undeclared state. |
| `references/phase4-controlled-loop.md` | loop state | Align post-feedback state decisions with DS-PSR-001. |
| `assets/fixtures/negative/NEG-STATE-001-undeclared-cancelled-state.json` | negative fixture | Prove the undeclared runtime state is rejected. |
| `plans/development-system-full-refactor-architecture-v1.1-2026-08-15.html` | completion architecture | Remove the stale bare-boolean requirement and mark both repairs validated. |
| `plans/development-system-full-refactor-test-plan-v1.1-2026-08-15.html` | negative fixture inventory | Align planned fixture names with the implemented files and validated status. |

## Decision And Alternatives

The repair reuses handoff-system as the owner of the feedback packet schema and adds only evidence-of-validation checks to development-system. It does not duplicate the packet schema, relax the completion gate, or add a cancellation state. Cancellation/supersession is recorded as an anchor lifecycle event; adding a runtime state requires requirements review.

## Detailed Change

- Added `validate_feedback_evidence()` with canonical SHA-256 matching and explicit external validator evidence.
- Replaced bare completion validity with the result of the evidence validator.
- Added three completion negative fixtures for missing evidence, hash mismatch and schema errors.
- Replaced the report builder's legacy `feedbackValid` output with real feedback, hash-bound evidence and the CompletionEvaluator result.
- Removed `cancelled-or-superseded` from runtime constants, transitions, schemas and state tables.
- Added an undeclared-state negative fixture and semantic test.
- Added AST/JSON hard gates that compare runtime and schema state lists to DS-PSR-001.

## Impact Analysis

- A bare `feedbackValid=true` cannot satisfy completion.
- The feedback object must be non-empty and its canonical SHA-256 must match `feedbackValidation.feedbackHash`.
- The external validator must report `ok=true`, `errorCount=0`, no errors and a validation time.
- Runtime and anchor schemas, transition map and references agree on exactly 11 states.
- Positive completion remains supported when all evidence is valid.
- The downstream executor process-spawn defect remains a separate P1 follow-up; this Skill fails closed rather than masking it.

## Validation Evidence

| Check | Method | Result | Evidence |
|---|---|---|---|
| Feedback regression | `test_development_runtime.py` through governed runner | pass | `DEVELOPMENT_RUNTIME_OK` |
| Full contract regression | `test_full_refactor_contract.py` through governed runner | pass | `FULL_REFACTOR_CONTRACT_OK` |
| Specialized validator | `validate_development_system.py` through governed runner | pass | `accepted`, P0/P1/P2 = 0/0/0 |
| Remaining dedicated suites | Phase/Story, Phase 1 boundary and Skill governance | pass | all three OK markers |
| Generic Skill validator | `validate_create_skill.py --require-change-records` | pass | `accepted-with-constraints`, P0/P1/P2 = 0/0/0 |
| Negative fixtures | completion 004-006 and state 001 loaded and exercised | pass | all intended bypasses rejected |
| RTM and CompletionEvaluator | `build_refactor_reports.py` | pass | 7 phases, 33 stories, uncovered IDs = 0; state `completed` |
| JSON / embedded JSON | 85 JSON files and 7 HTML application/json blocks | pass | parse errors = 0 |
| Sensitive scan | specialized validator plus boundary-aware final scan | pass | no real secret-pattern findings |
| PowerShell failure governance | compatibility and quoting failures recorded after verified repairs | pass | `PS-INC-20260815-010`, `PS-INC-20260815-011` |

## Safety And Privacy

No credentials, tokens, private URLs or production data were added. Claude was bounded to the approved workspace. The unauthorized `run_tests.bat` artifact was removed before validation. User-level installation remains out of scope and requires separate approval.

## Risks And Follow-up

- `handoff-claude-executor` still needs a fix for process-spawn `PermissionError` and guaranteed feedback synthesis.
- Live Claude reliability remains unverified until that downstream defect is repaired and a new exact-scope live run is authorized.
- This workspace candidate is not installed to `C:\Users\lenovo\.codex\skills\development-system`.

Refs: DS-PSR-001 v1.1, DS-REFRACTOR-RA-002 v1.2, DS-REPAIR-001, DS-REPAIR-002, REPAIR-ST-001, REPAIR-ST-002.
