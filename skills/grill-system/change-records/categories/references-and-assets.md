# References And Assets Change Ledger

## Purpose

Record changes to references/ or assets/ content, templates, schemas, or fixtures.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-005 | schemas/grill-session-v2.schema.json, references/grill-session-contract.md, phase-boundary-contract.md, assets/grill-report-template.html | added / changed | Define V2 ledger fields and project the same ledger into the report without granting report write authority. | validated |
| 2026-09-06 | CR-20260906-001 | references/routing-policy.md, downstream-skill-map.md, question-packs/ | governance | Apply the same freeze and ledger rule to all seven Grill routes and downstream transition guidance. | validated |
| 2026-08-29 | CR-20260829-001 | schemas/ | added | Add grill-session.schema.json and grill-failure-classification.json. | validated-candidate |
| 2026-08-29 | CR-20260829-001 | assets/fixtures/ | added | Add positive fixture grill-session-valid.html and four negative fixtures. | validated-candidate |

## Detailed Records

### CR-20260906-005 - v2-schema-contract-and-report-projection

- Section changed: `schemas/grill-session-v2.schema.json`, `references/grill-session-contract.md`, `references/phase-boundary-contract.md`, and `assets/grill-report-template.html`.
- Before: V1 report data did not express the V2 phase boundary, process artifacts, protected assets, closure, exception, recovery, checkpoint, or receipt model.
- After: V2 defines one canonical ledger and the HTML report is its exact projection. It exposes phase/result and no-op or updated outcome without creating a second decision source.
- Why: FR-003, FR-008, FR-009, FR-011, and FR-012 require one recoverable source and truthful report capability claims.
- Impact: V1 remains legacy-read-only; the report and format validator cannot authorize closure or writeback.
- Validation: Pending root final suite and independent junction evidence.
- Detail record: ../entries/2026/2026-09/CR-20260906-005-v2-runtime-artifact-boundary.md

### CR-20260906-001 - route-and-downstream-phase-boundary

- Section changed: routing policy, downstream map, and seven question packs.
- Before: Route packs and handoffs could be read as allowing formal output during a question loop.
- After: Each route directs answers to the authoritative ledger and freezes formal and substitute artifacts until closure-backed centralized writeback.
- Why: FR-002, FR-004, FR-008, FR-010, and AC-002, AC-004, AC-008, AC-010 require route-consistent behavior.
- Impact: Downstream writers receive explicit non-writing outcomes and domain-modeling receives a separate active-review output mode.
- Validation: Pending candidate structure, change-record, and runtime behavior checks.
- Detail record: ../entries/2026/2026-09/CR-20260906-001-phase-boundary-cross-skill-documentation.md

### CR-20260829-001 - grill-schemas-and-fixtures

- Section changed: schemas/, assets/fixtures/.
- Before: No formal JSON schema or negative fixtures existed for grill sessions.
- After: Added grill-session.schema.json (Draft 2020-12), grill-failure-classification.json (12 stable failure classes), grill-session-valid.html (positive), and four negative fixtures (NEG-GRILL-001 through 004).
- Why: Formal schema and deterministic negative fixtures are required for the strong grill gate (AC-003, AC-004, AC-011).
- Impact: The validator now checks schema compliance and the failure classification is traceable.
- Detail record: ../entries/2026/2026-08/CR-20260829-001-grill-strong-gate.md
