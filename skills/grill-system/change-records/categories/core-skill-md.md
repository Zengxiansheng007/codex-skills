# Core Skill Markdown Change Ledger

## Purpose

Record changes to SKILL.md trigger wording, operating rules, workflow, decision rules, validation, or escalation.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-001 | SKILL.md | governance | Add phase/result separation, ledger authority, closure, batch-writeback, and active-Grill domain-modeling boundary. | validated |
| 2026-08-29 | CR-20260829-001 | SKILL.md | updated | Add Formal Session Gate section referencing grill-session.schema.json and grill-failure-classification.json. | validated-candidate |

## Detailed Records

### CR-20260906-001 - phase-boundary-cross-skill-documentation

- Section changed: SKILL.md.
- Before: Closure, report validation, and downstream routing were described without a cross-Skill frozen-asset and centralized-writeback contract.
- After: The Skill documents the candidate phase/result semantics, one-ledger authority, closure evidence, notes-only behavior, exception lifecycle, external-edit handling, and active-Grill suppression for domain-modeling.
- Why: FR-001 through FR-010 require every route and nested call to carry the same boundary.
- Impact: Documentation now rejects per-question formal writes and report-based authorization while preserving standalone domain modeling.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: ../entries/2026/2026-09/CR-20260906-001-phase-boundary-cross-skill-documentation.md

### CR-20260829-001 - grill-skill-md-formal-gate

- Section changed: SKILL.md.
- Before: Validation section referenced only the HTML template validator and test script.
- After: Added Formal Session Gate section (AC-003, AC-004, AC-011) with schema reference, required fields, single-question rule, P0-open-item completion block, and failure classification link.
- Why: The grill SKILL.md must explicitly advertise the formal session, single-question, and completion gates so downstream skills and agents can rely on them.
- Impact: Future edits that weaken the formal session gate or remove the schema reference should fail review.
- Detail record: ../entries/2026/2026-08/CR-20260829-001-grill-strong-gate.md
