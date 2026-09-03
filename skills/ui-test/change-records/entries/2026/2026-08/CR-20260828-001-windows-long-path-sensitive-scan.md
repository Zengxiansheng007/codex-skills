# CR-20260828-001 Windows long-path sensitive scan

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / validation |

- Status: validated
- Scope: `ui-test`
- Requirement: `FR-RVI-009`

## Change

`scan_sensitive_assets.py` now applies the Windows extended-length namespace to every normalized absolute local root and converts UNC roots to the extended UNC form. This allows a short scan root to reach deep Unicode descendants beyond the legacy MAX_PATH boundary.

## Validation

- Synthetic deep Unicode path fixture;
- short-root/deep-descendant fixture;
- UNC normalization fixture;
- already-prefixed path fixture;
- sensitive values remain redacted from findings.

Project-specific form-label contract tests are intentionally excluded from the global Skill package.

## Summary

Normalize Windows and UNC roots before scanning deep descendants.

## Context And Problem

Legacy path handling could omit files beyond the Windows path-length boundary.

## Sections Changed

`scan_sensitive_assets.py` and its path fixtures.

## Decision And Alternatives

Use the operating-system extended namespace rather than shortening governed business paths.

## Detailed Change

The original Change and Validation sections above remain the historical detail.

## Impact Analysis

Deep files become visible to the same scanner without changing finding content.

## Validation Evidence

The original validation list above records the executed fixture coverage.

## Safety And Privacy

Findings remain redacted and no credential value is emitted.

## Risks And Follow-up

Callers that bypass the scanner still need the shared long-path I/O boundary.
