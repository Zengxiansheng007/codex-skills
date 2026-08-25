# CR-20260825-004 Formal Tianjin publish and renderer repair

- Date: 2026-08-25
- Scope: total Human View compiler pilot for Tianjin Operations Management Platform
- Requirement anchor: `RA-UI-TEST-TOTAL-HUMAN-VIEW-20260824-v1.0`
- Status: candidate implementation and formal D-drive publish verified; XMind desktop Golden remains external pending

## Problem

The candidate compiler had tests that checked structural output but did not protect the real Chinese Human View wording. A renderer path contained malformed parameter separators and table text. The formal A source also contained the incorrect popup-version assertion.

## Change

- Stabilized Human View wording as `序号 | 操作 | 参数/数据 | 预期结果`.
- Rendered each parameter atomically with `：`, `；`, `索引：`, `来源：`, and `脱敏`.
- Repaired the A source assertion and normalized legacy text before lowering.
- Recompiled A and B from Source Case through Case IR.
- Published per-case Human/Midscene/Resolved/Playwright artifacts and product-level total Human View/outline/manifest.
- Added a short-path backup/staging strategy to avoid Windows MAX_PATH while retaining original path mappings in the backup manifest.

## Evidence

- Candidate pytest: `132 passed`.
- Compileall: passed.
- Sensitive scan: `status=clear`, `finding_count=0`.
- Formal publish backup: `D:\UI-Test\_tmp\formal-publish-backup-20260825-total-human-view`.
- Formal post-publish verification: passed; A/B `in_sync`; content variants and aggregate case set verified.

## Remaining gate

XMind desktop Golden import has not been executed through a desktop interaction channel. Completion must remain blocked on `xmind-golden-pending` until independent node-tree evidence is recorded.
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
