# Safety And Governance Change Ledger

## Purpose

Track routing constraints, write authorization, and capability-boundary changes.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-002 | SKILL.md and shared-contracts.md | governance | Prohibit report, per-question, callee-return, and legacy-result write authorization; state no OS interception claim. | validated |

## Detailed Records

### CR-20260906-002 - router-write-authorization-governance

- Section changed: SKILL.md and shared-contracts.md.
- Before: The router did not explicitly distinguish session closure from artifact writing authority.
- After: One closure-backed eligible result controls a centralized batch, notes-only produces zero writes, and non-writing outcomes remain blocked from formal mutation.
- Validation: Pending candidate structure, change-record, and runtime behavior checks.
- Detail record: `../entries/2026/2026-09/CR-20260906-002-phase-aware-grill-routing.md`

### CR-20260906-006 - Portable validation guidance

- Section changed: SKILL.md Operating Rules and Validation.
- Before: host-specific paths.
- After: generic global directory and explicit installed validator placeholders.
- Why: public installation portability.
- Impact: documentation only; runtime unchanged.
- Validation: release preflight and deployed validation receipts are maintained in the task release record.
- Status: validated.
- Detail record: [CR-20260906-006](../entries/2026/2026-09/CR-20260906-006-portable-release-validation.md).
