# Safety And Governance Change Ledger

## Purpose

Track approval, privacy, risk, retention and forbidden-action rules.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-18 | CR-20260818-001 | packet risk/secret rules | security | Block R0/R1 writes and secret-like values | applied |
| 2026-08-22 | CR-20260822-007 | R2 private pilot | fixed | Bind approval to run/case/test host/visible UI and one submit | validated |
| 2026-08-22 | CR-20260822-008 | private runtime value references | fixed | Represent environment references explicitly without relaxing literal-secret detection | validated |

## Detailed Records

### CR-20260822-007 - candidate-validation-and-pilot-runtime

- Section changed: R2 runtime and Skill safety boundary.
- Before: pilot used an environment switch plus local counter.
- After: current-run Approval Record and one-shot guard execute before UI submit.
- Why: close AC-CASE-044.
- Impact: missing or mismatched approval fails closed.
- Validation: positive and negative runtime template tests.
- Detail record: `../entries/2026/2026-08/CR-20260822-007-candidate-validation-and-pilot-runtime.md`.

### CR-20260822-008 - pytest-marker-and-env-reference-governance

- Section changed: private runtime value reference metadata.
- Before: an environment-variable name was stored directly under a sensitive field name and triggered the literal-secret scanner.
- After: the mapping uses a nested `env_ref` contract while in-memory injection behavior remains unchanged.
- Why: remove an ambiguous representation without adding a scanner allowlist that could hide real values.
- Impact: no credential value is persisted or printed; missing references still fail closed.
- Validation: positive environment-reference fixture plus retained literal-secret negative fixture.
- Detail record: `../entries/2026/2026-08/CR-20260822-008-pytest-marker-and-env-reference-governance.md`.
