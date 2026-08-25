# CR-20260822-009 - Deferred Migration Completion Status

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / validation / governance |
| Scope | scripts-and-validation |
| Source | completion evidence semantic review |
| Baseline | CR-20260822-008 validated candidate |
| Author | Codex |
| Related Records | CR-20260822-008 |

## Summary

Added an explicit deferred migration status so CompletionEvaluator does not report a passed dry-run and gated future disposition as a migration failure.

## Context And Problem

The migration dry-run passed and emitted a machine-readable issue list, while destructive disposition remains closed until the private pilot is complete. A boolean-only completion input collapsed this valid deferred state into `migration-failed`.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/ui_test_core/completion.py` | release evaluation | Add passed/failed/deferred migration status with legacy boolean compatibility. |
| `tests/test_pipeline_contracts.py` | completion regression | Assert deferred stays blocking but is not mislabeled failed. |
| `pilot/build_governance_evidence.py` | final gate | Supply `migration_status=deferred`. |

## Decision And Alternatives

Preserve fail-closed completion while distinguishing operational delay from validator failure. Do not mark migration passed until historical disposition is actually completed.

## Detailed Change

`migration_status` accepts only `passed`, `failed` or `deferred`. Unknown values fail closed as `migration-status-invalid`; existing callers using `migration_ok` remain compatible.

## Impact Analysis

Reports and downstream automation receive an accurate stable blocker. No migration, deletion or global installation permission is added.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Core and pilot tests | pytest | passed, 102 tests | candidate validation evidence |
| Completion gate regeneration | governed evidence builder | passed; blocker is `migration-deferred` | PH-06 completion evidence |
| Sensitive data | candidate package scan | clear, 0 findings | PH-06 evidence |

## Safety And Privacy

The change is local deterministic status logic and handles no credentials or private page data.

## Risks And Follow-up

Private P0-A/P0-B, historical disposition and global installation remain blocked by their existing gates.

Refs: FR-CASE-032, AC-CASE-039
