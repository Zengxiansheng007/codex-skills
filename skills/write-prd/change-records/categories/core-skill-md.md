# Core Skill Markdown Change Ledger

## Purpose

Track router trigger wording and prerequisite governance changes.

## Outline

| Date | Change ID | Section | Summary | Status |
|---|---|---|---|---|
| 2026-09-06 | CR-20260906-002 | SKILL.md | Add active-Grill freeze inheritance and closure-backed return checks. | validated |
| 2026-08-29 | CR-20260829-004 | SKILL.md | Added explicit trigger wording for router use. | validated |

## Detailed Records

### CR-20260906-002

- Section changed: SKILL.md operating rules, child return checks, and decision rules.
- Before: A child return could resume artifact processing without an explicit phase/writeback eligibility check.
- After: The router freezes formal artifacts during Grill and requires `phase`, `result`, `closureEvidence`, `writebackPolicy`, `protectedAssets`, `processArtifacts`, `exceptions`, `checkpoints`, and `writebackReceipts` before centralized writing.
- Validation: Pending candidate structure, change-record, and runtime behavior checks.
- Detail record: `../entries/2026/2026-09/CR-20260906-002-phase-aware-grill-routing.md`

### CR-20260829-004

- Detail record: `../entries/2026/2026-08/CR-20260829-004-router-trigger-wording.md`

### CR-20260906-006 - Portable validation guidance

- Section changed: SKILL.md Operating Rules and Validation.
- Before: host-specific paths.
- After: generic global directory and explicit installed validator placeholders.
- Why: public installation portability.
- Impact: documentation only; runtime unchanged.
- Validation: release preflight and deployed validation receipts are maintained in the task release record.
- Status: validated.
- Detail record: [CR-20260906-006](../entries/2026/2026-09/CR-20260906-006-portable-release-validation.md).
