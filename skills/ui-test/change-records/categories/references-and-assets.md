# References And Assets Change Ledger

## Purpose

Track schemas, fixtures, references and generated-asset contracts.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-03 | CR-20260903-001 | v2 schemas and asset governance | changed | Add page-module, product-outline, aggregate-manifest and pre-submit qualification contracts | validated |
| 2026-09-02 | CR-20260902-001 | schemas, fixtures and asset-governance reference | added | Define the v2 parameter, release, diagnostics, migration and cleanup artifact family | validated |
| 2026-08-18 | CR-20260818-001 | schemas/assets/fixtures | added | Add versioned packet schema and valid/invalid fixtures | applied |
| 2026-08-22 | CR-20260822-001 | schemas/contract-registry.json | changed | Extend registry with planned Source Case, Case IR, Resolved IR and Compile Receipt entries | applied |

## Detailed Records

### CR-20260902-001 - test-data-sync-execution-governance

- Section changed: contract registry, v2 schemas, fixtures and project-asset governance.
- Before: Source Case v1 carried business values and no complete v2 artifact family was registered.
- After: proposed contracts separate Source Case semantics from branch-level editable Test Data and generated projections.
- Why: ensure one editable business-data source and deterministic downstream assets.
- Impact: old-format artifacts remain readable for audit but cannot execute.
- Validation: every registered Schema passed Draft 2020-12 meta-validation and positive/negative registry tests.
- Detail record: `../entries/2026/2026-09/CR-20260902-001-test-data-sync-execution-governance.md`.

### CR-20260822-007 - candidate-validation-and-pilot-runtime

- Section changed: no reference contract behavior changed.
- Before: package references predated the current validator.
- After: reference links are validated as bounded resources.
- Why: final package traceability.
- Impact: documentation only in this category.
- Validation: reference existence checks.
- Detail record: `../entries/2026/2026-08/CR-20260822-007-candidate-validation-and-pilot-runtime.md`.
