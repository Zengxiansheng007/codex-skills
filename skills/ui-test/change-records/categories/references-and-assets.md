# References And Assets Change Ledger

## Purpose

Track schemas, fixtures, references and generated-asset contracts.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-18 | CR-20260818-001 | schemas/assets/fixtures | added | Add versioned packet schema and valid/invalid fixtures | applied |
| 2026-08-22 | CR-20260822-001 | schemas/contract-registry.json | changed | Extend registry with planned Source Case, Case IR, Resolved IR and Compile Receipt entries | applied |

## Detailed Records

### CR-20260822-007 - candidate-validation-and-pilot-runtime

- Section changed: no reference contract behavior changed.
- Before: package references predated the current validator.
- After: reference links are validated as bounded resources.
- Why: final package traceability.
- Impact: documentation only in this category.
- Validation: reference existence checks.
- Detail record: `../entries/2026/2026-08/CR-20260822-007-candidate-validation-and-pilot-runtime.md`.
