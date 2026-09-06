# Safety And Governance Change Ledger

## Purpose

Track formal PRD write authorization and external-change handling.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-003 | SKILL.md | governance | Prohibit per-question, report, and legacy-result formal writes; preserve external changes and selectively reopen. | validated |

## Detailed Records

### CR-20260906-003 - prd-write-authorization-governance

- Section changed: SKILL.md.
- Before: The PRD Skill did not state the active-Grill freeze or result-specific non-writing outcomes.
- After: It distinguishes whole-review closure from a question confirmation and blocks writes for notes-only, pause, block, repair, partial failure, and legacy-read-only outcomes.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: `../entries/2026/2026-09/CR-20260906-003-phase-aware-prd-authoring.md`
