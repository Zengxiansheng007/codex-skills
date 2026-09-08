# Scripts And Validation Change Ledger

## Purpose

Track changes to deterministic validation and test coverage for development-system.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-24 | CR-20260824-003 | release_adapter.py / test_release_adapter.py | behavior / validation | Add default remote bindings and tests for defaults plus GitBook approval mismatch. | validated |
| 2026-08-24 | CR-20260824-001 | landed_review.py / document_manifest_runtime.py / publish_package.py and tests | implementation / validation | Add deterministic drift, digest, state, idempotency, rollback and dry-run publish checks. | validated |
| 2026-08-20 | CR-20260820-001 | scripts/validate_development_system.py / change-record detail records | governance / validation | Add `write-prd` to the required skill terms, require the new detail record, and normalize legacy detail records required by the generic Skill validator. | validated |
| 2026-08-17 | CR-20260817-001 | CLW PH-2/3/4 runtime and regression suite | implementation / validation | Add deterministic queue, recovery, isolated slot, write-set, merge-candidate, Agent profile and feedback review gates. | validated |
| 2026-08-16 | CR-20260816-004 | PH-4 governance module / tests / validator | implementation / validation | Add exact install and operations gates plus full validator coverage. | validated |
| 2026-08-16 | CR-20260816-003 | PH-3 runtime / tests / validator | implementation / validation | Add live-loop harness, lineage, side-effect and stop-limit tests. | applied |
| 2026-08-16 | CR-20260816-002 | PH-2 runtime / generator / validator / tests | implementation / validation | Enforce policy lifecycle, hashed dry-run, status and takeover gates with full regression coverage. | validated |
| 2026-08-15 | CR-20260815-003 | completion evaluator / state model / validators / regression tests | repair / validation | Bind completion to actual feedback evidence and add exact 11-state and undeclared-state rejection gates. | validated |
| 2026-08-15 | CR-20260815-002 | development runtime / full-contract regression / validator | implementation / validation | Add deterministic gates for transition, recovery, long-task, merge, Skill interfaces, audit, resource and module admission; exercise traced negative fixtures. | validated |
| 2026-08-15 | CR-20260815-001 | PH-01A regression suite | validation | Preserve the failing schema assertion and rerun the complete suite after bounded Claude timeout takeover. | validated |
| 2026-08-14 | CR-20260814-001 | validators / phase-story test | validation | Add schema/reference/fixture checks to validator; add test_phase_story_contract.py; fix root resolution from __file__ in all three test scripts. | validated |
| 2026-08-09 | CR-20260809-003 | governance regression / validator | validation | Add deterministic checks for generic Skill safety heading, canonical change-record sections, and the validator source marker comment used by the contract test. | validated |
| 2026-08-09 | CR-20260809-002 | validators / phase1 test | validation | Enforce Phase 1 boundary contract, single-file behavior fixture, and package-level file coverage. | validated |
| 2026-08-09 | CR-20260809-001 | validators | changed | Require new references, route fixture, change-record artifacts, and fixed router-contract title. | validated |

## Detailed Records

### CR-20260824-003 - default-publish-targets

- Section changed: release adapter argument defaults, approval validation and regression tests.
- Before: all remote IDs were required arguments and GitBook organization/Site/Space were not compared with the approval object.
- After: confirmed targets are defaults and all three GitBook IDs must exactly match approval before publishing.
- Why: defaults should reduce typing while the executable gate prevents silent target expansion.
- Impact: older incomplete approval files fail closed until GitBook fields are added.
- Validation: 10 adapter tests and all 13 workspace test scripts passed; main validator accepted with P0/P1/P2 = 0/0/0.
- Detail record: `change-records/entries/2026/2026-08/CR-20260824-003-default-publish-targets.md`

### CR-20260824-001 - landed-review-and-publish-lifecycle

- Section changed: three deterministic runtimes and their focused tests.
- Before: no executable post-implementation document comparison, computed manifest digest gate or fixed dry-run publish planner.
- After: drift classification, candidate revision output, manifest/state validation, idempotency, append-only rollback and target/approval preflight are executable.
- Why: close P0/P1 lifecycle risks without adding external writes to the candidate.
- Impact: real adapters must supply target binding and evidence before external status transitions.
- Validation: 6 landed-review tests, 5 manifest tests, 3 publish tests, development runtime, full-refactor, PH4, CLW and package validators passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260824-001-landed-review-and-publish-lifecycle.md`

### CR-20260816-002 - ph2-claude-governance

- Section changed: runtime, fixture generator, specialized validator and deterministic tests.
- Before: several PH-2 checks were prose-only or bypassable, and required assets were not validator-enforced.
- After: executable functions and tests cover the complete PH-2 matrix without weakening prior assertions.
- Why: strong gates must be script-backed wherever deterministic validation is possible.
- Impact: PH-2 regressions produce test or validator failure before live execution.
- Validation: validator accepted 0/0/0; runtime, full-refactor and legacy contracts passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-002-ph2-claude-governance.md`

### CR-20260815-003 - completion-evidence-and-state-alignment

- Section changed: `development_runtime.py`, `build_refactor_reports.py`, runtime/full-contract tests and specialized validator.
- Before: `evaluate_completion()` accepted the old `feedbackValid` shape, and validators did not assert exact parity between the runtime state constant and confirmed baseline.
- After: `validate_feedback_evidence()` verifies the actual feedback hash and external validation evidence; report generation emits the same contract; validators and tests enforce exact state parity and rejection semantics.
- Why: the suite must catch the NO_GO completion failures and state-model drift rather than only exercise happy paths.
- Impact: deterministic checks are stronger; no assertion was weakened.
- Validation: `DEVELOPMENT_RUNTIME_OK`, `FULL_REFACTOR_CONTRACT_OK`, and specialized validator `accepted`.
- Detail record: `change-records/entries/2026/2026-08/CR-20260815-003-completion-evidence-and-state-alignment.md`

### CR-20260815-002 - full-runtime-ph1b-ph7

- Section changed: `development_runtime.py`, runtime tests, full-refactor test and specialized validator.
- Before: remaining Phase behavior existed only in plans and requirements; the first runtime red run found one admission-order defect and fourteen missing fixtures.
- After: reusable deterministic functions and regression tests enforce state, preauthorization, progress, circuits, recovery, concurrency, merge, audit and module gates; the portable baseline sync keeps extracted-package tests independent of workspace-only paths.
- Why: strong gates must be executable wherever deterministic validation is possible.
- Impact: prose-only compliance is insufficient; missing assets or weakened behavior fail the test suite.
- Validation: runtime, full-refactor, Phase/Story, Phase 1 boundary, Skill governance and specialized validator all passed in source and the extracted clean Codex candidate.
- Detail record: `change-records/entries/2026/2026-08/CR-20260815-002-full-runtime-ph1b-ph7.md`

### CR-20260815-001 - mappedFrAc-required-repair

- Section changed: validation evidence only; no test assertion was weakened.
- Before: `test_phase_story_contract.py` failed because the schema omitted a required trace field.
- After: the production schema matches the existing regression assertion.
- Why: deterministic gates take priority over prose-only acceptance.
- Impact: the test continues to guard against omission of `mappedFrAc`.
- Validation: all specialized tests and the generic create-skill validator passed with P0/P1/P2 = 0; sensitive scan is included in both validators.
- Detail record: `change-records/entries/2026/2026-08/CR-20260815-001-mappedFrAc-required-repair.md`

### CR-20260820-001 - write-prd-router-entry

- Section changed: `scripts/validate_development_system.py` and change-record detail validation compatibility.
- Before: the validator required `write-requirements-prd` but not `write-prd`.
- After: the validator now requires both `write-prd` and `write-requirements-prd`, requires this detail record, and the legacy 2026-08-17 detail records have the sections required by the generic Skill validator.
- Why: the new top-level router must be visible to skill-governance tests and the package must remain validateable under the generic change-record contract.
- Impact: validation will fail if `write-prd` is missing from the deployed skill body or if the new detail record is absent.
- Validation: workspace `validate_development_system.py` accepted; generic `validate_create_skill.py --require-change-records` accepted-with-constraints.
- Detail record: `change-records/entries/2026/2026-08/CR-20260820-001-write-prd-router-entry.md`

### CR-20260814-001 - ph1-foundation-slice

- Section changed: `scripts/validate_development_system.py`, `scripts/test_phase_story_contract.py`, `scripts/test_phase1_boundary_contract.py`, `scripts/test_skill_governance_contract.py`.
- Before: validator did not check new schemas, references or fixtures; test scripts resolved root from cwd; no phase/story contract test existed.
- After: validator checks schema draft, required fields, reference terms, positive fixture structure, negative fixture rejection rules and CR-20260814-001 entry; new test_phase_story_contract.py validates positive and negative fixtures including dependency cycle detection; all three test scripts now resolve root from `__file__`.
- Why: deterministic validation must reject missing fields, cycles and ownership conflicts; root resolution must not depend on caller cwd.
- Impact: missing schemas, references or fixtures now fail validation; test scripts are portable.
- Validation: all four scripts passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260814-001-ph1-foundation-slice.md`

### CR-20260809-003 - generic-skill-governance-contract

- Section changed: `scripts/test_skill_governance_contract.py` and `scripts/validate_development_system.py`.
- Before: the dedicated validator accepted a Skill that the generic create-skill governance validator classified as review-required.
- After: local regression coverage checks the same required headings, the validator source marker comment, and the Phase 1 impact-analysis section before deployment.
- Why: prevent disagreement between specialized and generic validation from recurring silently.
- Impact: governance contract drift fails deterministic local validation.
- Validation: RED test reproduced the missing safety-heading source marker; GREEN validation passed in workspace and global validation.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-003-generic-skill-governance-contract.md`

### CR-20260809-002 - phase1-boundary-contract

- Section changed: `scripts/test_phase1_boundary_contract.py`, `scripts/validate_development_system.py`, and package-level validator.
- Before: validators did not require the Phase 1 boundary contract or the single-file behavior change fixture.
- After: validators require the new reference, fixture, CR-20260809-002 index entry, and semantic markers.
- Why: the confirmed boundary must fail fast if future edits remove or weaken it.
- Impact: missing Phase 1 boundary assets become P0/P1 validation failures.
- Validation: Phase 1 boundary test and development-system validator passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-002-phase1-boundary-contract.md`

### CR-20260809-001 - development-system-local-global-loop

- Section changed: `scripts/validate_development_system.py` and package-level validator.
- Before: Validators did not cover the new reference gaps or stale router-contract title.
- After: Validators require the new reference files, fixture, and change-record artifacts; the skill validator checks the canonical router contract title and Change ID index entry.
- Why: Prevent the same omissions from returning as silent documentation drift.
- Impact: Missing new guidance or change records now fail validation.
- Validation: Source skill validator and package-level validator passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-001-development-system-local-global-loop.md`
### CR-20260816-004 - ph4-install-operations-governance

- Section changed: `phase4_governance.py`, PH-4 tests and required-file validator.
- Before: PH-4 promotion checks were prose only.
- After: deterministic gates reject approval, hash, rollback and audit defects.
- Why: strong gates must be executable where possible.
- Impact: PH-4 candidate readiness is machine-verifiable without installing.
- Validation: PH4_GOVERNANCE_OK; final suite pending.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-004-ph4-install-operations-governance.md`

### CR-20260816-003 - ph3-real-closed-loop

- Section changed: runtime live-loop functions and PH-3 tests.
- Before: PH-2 primitives were not composed into one completion-controlled loop.
- After: lineage, drift, feedback, side effects and limits are evaluated together.
- Why: PH-3 requires gap review and bounded repair evidence.
- Impact: invalid feedback is classified independently from requirement drift.
- Validation: DEVELOPMENT_RUNTIME_OK after classification repair.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-003-ph3-real-closed-loop.md`

### CR-20260908-003 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: development-system; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-003-research-routing.md).
