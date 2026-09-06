# Safety And Governance Change Ledger

## Purpose

Record changes to approval gates, privacy boundaries, forbidden actions, governance, or sensitive-data handling.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-005 | V2 runtime, artifact checks, schema, and contracts | governance / validation | Fail closed for protected path escapes, reparse points, Windows junctions, forged evidence, legacy writes, and unverified postconditions. | validated |
| 2026-09-06 | CR-20260906-001 | SKILL.md and references/ | governance | State the no-global-interception boundary and prohibit legacy/report/per-question authorization. | validated |
| 2026-08-29 | CR-20260829-001 | schemas/grill-failure-classification.json | added | Define 12 stable grill failure classes; none propagate to completed. | validated-candidate |

## Detailed Records

### CR-20260906-005 - v2-fail-closed-write-governance

- Section changed: V2 runtime, artifact checks, schema, contracts, and tests.
- Before: Candidate governance lacked V2 process-artifact collision, junction/reparse, frozen-plan, actual-hash, and no-op guard evidence.
- After: V2 rejects escapes and forged/stale conditions; it accepts only bounded exception or closure-backed batch paths and records no-op separately from updated work.
- Why: FR-004 to FR-007 and FR-011 require bounded permission and actual-change evidence without claiming an OS-wide interceptor.
- Impact: The runtime detects observable drift but does not infer semantic impact or overwrite external content.
- Initial validation note (historical): Pending root final suite and independent junction evidence.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: ../entries/2026/2026-09/CR-20260906-005-v2-runtime-artifact-boundary.md

### CR-20260906-001 - write-authorization-governance

- Section changed: phase-boundary rules in SKILL.md and references.
- Before: The documentation did not distinguish a formal closure authority from report or question artifacts.
- After: Only closure evidence and policy can make writeback eligible; notes-only, paused, blocked, repair-needed, partial-failure, and legacy-read-only remain non-writing.
- Why: FR-001, FR-005, FR-006, FR-011, and FR-012 require safe, truthful write authority boundaries.
- Impact: No OS/ACL interception is claimed; checkpoint evidence has a stated limit.
- Initial validation note (historical): Pending candidate structure, change-record, and runtime behavior checks.
- Release validation: passed for the verified scope; see the current public documentation and evidence summary. File-symlink capability skip remains explicit.
- Detail record: ../entries/2026/2026-09/CR-20260906-001-phase-boundary-cross-skill-documentation.md

### CR-20260829-001 - grill-failure-governance

- Section changed: schemas/grill-failure-classification.json.
- Before: No formal failure classification existed for grill sessions.
- After: 12 stable failure classes (session-id-missing, missing-required-question-field, multiple-questions-in-one, invalid-question-status, invalid-question-severity, invalid-session-status, complete-with-p0-open-items, missing-recommended-answer, no-questions-in-non-template, sensitive-data-in-report, parse-error, missing-top-level-fields). All propagate to repair-needed, never completed.
- Why: Failure classes must be stable identifiers so downstream skills can route them without ambiguity.
- Impact: The validator now checks that no failure class maps to completed.
- Detail record: ../entries/2026/2026-08/CR-20260829-001-grill-strong-gate.md
