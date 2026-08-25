# CR-20260822-005 - Unified Preflight And Sensitive Scan

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test |
| Story | PH01-ST05 |
| Requirements | FR-CASE-030, FR-CASE-031, FR-CASE-033, FR-CASE-034, FR-CASE-049 |
| Acceptance | AC-CASE-015, AC-CASE-016, AC-CASE-026 |

## Summary

Add a versioned unified preflight/post-write result, combining config, Packet, release state, migration blockers, sensitive data and governed path checks. Add a redacted package scanner that detects strong credential forms and non-placeholder sensitive-field literals without treating function parameter names or detection-rule strings as secrets.

## Context And Problem

Independent validators did not provide one write/completion decision.

## Sections Changed

Preflight, post-write and package sensitive scan.

## Decision And Alternatives

Aggregate stable issue codes into one fail-closed result.

## Impact Analysis

Any contract, path, release, migration or sensitive failure blocks completion.

## Validation Evidence

- Full candidate `ui-test` suite: 70 tests passed.
- Candidate sensitive scan: clear, 0 findings.
- Contract registry and 14-Skill source baseline: valid, 0 issues.
- Positive preflight and post-write fixtures pass; nine stable negative issue codes block write or completion.
- Non-UI-Test C-drive workspace files remain outside enforcement.

## Safety And Privacy

Scanner findings are redacted and do not echo matched values.

## Risks And Follow-up

Static signatures require ongoing false-positive regression tests.
