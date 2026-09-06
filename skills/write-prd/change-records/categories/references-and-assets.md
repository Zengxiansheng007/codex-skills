# References And Assets Change Ledger

## Purpose

Track reference or asset changes that affect router contracts, baselines, or governed write behavior.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-002 | grill-system-requirements-adapter.md, shared-contracts.md, baseline-selection.md | governance | Replace immediate-return writing with closure-backed centralized writeback and exclude Spec Kit incremental saving. | validated |

## Detailed Records

### CR-20260906-002 - phase-aware-router-references

- Section changed: requirements adapter, shared artifact contract, and baseline selection.
- Before: The adapter returned a legacy status and directed immediate PRD resumption.
- After: It describes phase/result semantics and non-writing outcomes, while shared contracts define formal asset freeze and baseline/conflict handling.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: `../entries/2026/2026-09/CR-20260906-002-phase-aware-grill-routing.md`

### CR-20260906-008 - Reviewed documentation

- Section changed: current documentation and category validation projection.
- Before: preparation snapshots could be mistaken for current state.
- After: historical notes labeled; current public documentation linked.
- Why: align documentation with released code and actual evidence.
- Impact: Markdown only; executable content unchanged.
- Validation: this documentation release's static/evidence/package checks passed; executable content unchanged.
- Status: validated.
- Detail record: [entry](../entries/2026/2026-09/CR-20260906-008-reviewed-public-documentation.md).
