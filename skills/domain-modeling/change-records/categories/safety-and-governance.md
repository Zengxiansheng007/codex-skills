# Safety And Governance Change Ledger

## Purpose

Track the boundary that prevents active Grill calls from mutating formal domain assets.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-004 | Grill Invocation Boundary | governance | Require closure-backed centralized writeback and preserve external domain edits. | validated |

## Detailed Records

### CR-20260906-004 - domain-write-boundary

- Section changed: Grill Invocation Boundary.
- Before: Domain-modeling had no caller-phase exception to immediate formal updates.
- After: It suppresses those updates only for the active Grill context and rejects report, question, callee-return, and legacy-record authority.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: `../entries/2026/2026-09/CR-20260906-004-active-grill-domain-modeling.md`
