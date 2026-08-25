# CR-20260822-006 - Compiler Runtime And Result Governance

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test |
| Stories | PH02-ST01..PH04-ST04 |

## Summary

Add deterministic dependency compilation, multi-view rendering, immutable local releases, plan/sync concurrency, receipts, retention metadata, fresh-context Flow runtime, current-session checkpoint routing, run-scoped UI-only R2 control, event-folded RunResult and read-only downstream projections. Add conservative first-pilot deletion gates.

## Context And Problem

Generated assets, runtime state and reports lacked one governed lifecycle.

## Sections Changed

Compiler, release runtime, R2 guard, RunResult, projections and migration gates.

## Decision And Alternatives

Use immutable releases and event-folded results instead of mutable generated files and report-owned status.

## Impact Analysis

Thin tests share runtime layers and all downstream output derives from RunResult.

## Validation Evidence

- 88 candidate tests pass.
- No model or network call exists in compilation.
- Failure injection preserves the previous active release.
- R2 submit is run-bound and one-shot; teardown never deletes business data.
- Reports, evidence and experience cannot override RunResult status.

## Safety And Privacy

R2 is current-run, test-only, visible-UI-only and one-shot.

## Risks And Follow-up

Private pilot evidence remains required before final completion.
