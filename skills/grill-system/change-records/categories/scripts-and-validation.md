# Scripts And Validation Change Ledger

## Purpose

Record changes to validators, tests, or scripts.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-005 | scripts/grill_session_runtime.py, grill_artifact_checks.py, tests, validate_grill_report.py | added / changed | Implement V2 ledger CLI and fail-closed boundary checks, then cover CLI, no-op, actual postcondition, and Windows junction paths. | validated |
| 2026-08-29 | CR-20260829-001 | scripts/validate_grill_report.py | updated | Add schema validation, formal session-id check, failure-class stability check, and aligned rule names to failure classification. | validated-candidate |
| 2026-08-29 | CR-20260829-001 | scripts/test_validate_grill_report.py | updated | Add 8 new negative/positive tests for formal session, invalid status, JSON direct, invalid question fields, no-questions, risk-accepted, and failure classification. | validated-candidate |

## Detailed Records

### CR-20260906-005 - v2-runtime-and-artifact-checks

- Section changed: `scripts/grill_session_runtime.py`, `scripts/grill_artifact_checks.py`, `scripts/test_grill_phase_contract.py`, `scripts/test_grill_artifact_checks.py`, and `scripts/validate_grill_report.py`.
- Before: The candidate had no V2 ledger runtime or target-aware protected-asset checks.
- After: The runtime provides the documented V2 CLI; its batch plans freeze decisions, scopes, and actual target postconditions. Artifact checks fail closed for traversal, symlink, and Windows junction/reparse paths; tests use owned temporary targets for updated, no-op, exception, and receipt evidence.
- Why: FR-001 to FR-012 and AC-001 to AC-012 need testable phase, asset, exception, legacy, and postcondition behavior.
- Impact: A process-ledger mutation does not authorize formal writes; no-op evidence is distinct from an actual update and a hash mismatch is not success.
- Validation: Pending root final suite and independent junction evidence.
- Detail record: ../entries/2026/2026-09/CR-20260906-005-v2-runtime-artifact-boundary.md

### CR-20260829-001 - grill-validator-strengthening

- Section changed: scripts/validate_grill_report.py, scripts/test_validate_grill_report.py.
- Before: Validator checked only top-level fields, question fields, P0-open-items, sensitive data, and multiple-questions. Rule names were ad hoc.
- After: Validator now (1) validates against grill-session.schema.json, (2) checks formal non-empty sessionId, (3) checks failure-class stability (never completed), (4) uses rule names aligned to grill-failure-classification.json. Tests grew from 6 to 14 cases.
- Why: Each gate needs a deterministic, traceable rule name; schema validation catches structural violations the semantic checks miss.
- Impact: All existing negative tests pass with updated rule names; new tests cover the strengthened gates.
- Validation: Pending execution; implementation is complete and deterministic.
- Detail record: ../entries/2026/2026-08/CR-20260829-001-grill-strong-gate.md
