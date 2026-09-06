# Downstream And Handoff Change Ledger

## Purpose

Track domain-modeling behavior when invoked by Grill.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-004 | Grill Invocation Boundary | contract | Return proposed canonical terms and ADR candidates to the Grill ledger. | validated |

## Detailed Records

### CR-20260906-004 - domain-proposal-return

- Section changed: Grill Invocation Boundary.
- Before: The caller had no documented non-writing result to consume.
- After: Grill receives proposed terms and ADR candidates in its canonical ledger and the owning writer applies them only after eligible writeback.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: `../entries/2026/2026-09/CR-20260906-004-active-grill-domain-modeling.md`
