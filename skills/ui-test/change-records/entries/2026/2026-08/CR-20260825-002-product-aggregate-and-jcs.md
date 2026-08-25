# CR-20260825-002 - product-aggregate-and-jcs

- Date: 2026-08-25
- Scope: candidate `ui-test` workspace only.
- Status: validated in isolation.
- Requirements: FR-TOTAL-001, FR-TOTAL-002, FR-TOTAL-003, FR-TOTAL-004, FR-TOTAL-006, FR-TOTAL-007, FR-TOTAL-012, FR-TOTAL-013.

## Change

- Added product aggregate renderer for Markdown and recursive XMind outline JSON.
- Added fixed `参数/数据` operation nodes with atomic parameter children.
- Added fail-closed rejection for stale, hash-mismatched, mixed-scope and uncovered P0 aggregate inputs.
- Added `product-outline` and `product-aggregate-manifest` schemas.
- Added an internal RFC 8785 wrapper, locked `rfc8785==0.1.4`, and recorded dependency licenses.
- Added Chinese and legacy Windows-code-page semantic matching for the A popup-version assertion defect.
- Added accepted project variant aliases for `system-plain-text` and `popup-rich-text`.

## Validation

- `python -m compileall -q scripts tests`: passed.
- `python -m unittest discover -s tests -v`: 122 tests passed.
- Sensitive scan: clear, 0 findings, raw values not persisted.
- Read-only diagnostic of existing D-drive A/B Source Cases: A reports `SEM-ASSERT-001`; B reports no semantic issue; joint P0 coverage reports no issue.

## Boundary

- No D-drive file was modified.
- No global Skill was modified or installed.
- No D:RAG write, private UI run, production operation, or business write was performed.
- XMind desktop import remains a pending external Golden verification.
| Status | validated |

## Summary

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Context And Problem

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Sections Changed

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Decision And Alternatives

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Impact Analysis

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Validation Evidence

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Safety And Privacy

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Risks And Follow-up

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.
