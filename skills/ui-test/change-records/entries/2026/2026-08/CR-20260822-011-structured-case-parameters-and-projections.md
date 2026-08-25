# CR-20260822-011 - Structured Case Parameters And Projections

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | feature / contract / compiler / validation |
| Scope | Source Case, Case IR, Case Compiler, Human View, Midscene View, governance |
| Source | Human View parameter-column requirement and shared-data reference governance |
| Baseline | CR-20260822-010 validated candidate |
| Author | Codex |
| Related Records | CR-20260822-002, CR-20260822-006, CR-20260822-010 |

## Summary

Added structured step parameters as part of the Source Case contract and propagated them through Case IR into generated Human View and Midscene View outputs.

## Context And Problem

Human-readable cases needed a dedicated `参数/数据` column while preserving one Source Case as the only business truth. Shared accounts and public data also needed reference-only display with an index address or reference ID, without exposing raw values.

## Detailed Change

- Added `steps[*].parameters` to the Source Case and Case IR schemas.
- Added parameter metadata for literal, generated, shared-data, public-data, environment and reference sources.
- Required `index_ref` for shared/public data parameters.
- Added deterministic validation for missing shared/public data indexes.
- Updated Case Compiler output so Human View renders `序号 | 操作 | 参数/数据 | 预期结果`.
- Updated Midscene View to carry the same structured parameter records.
- Preserved source hash, build fingerprint and generated-projection consistency.
- Updated governance guidance to prohibit separately maintained case bodies.

## Validation Evidence

| Check | Result |
|---|---|
| Full candidate pytest suite | passed, 99 tests |
| Direct and module pytest entry | both passed |
| Independent test-file execution | passed, 11 files |
| Schema parsing | passed, 19 schemas |
| Python compileall | passed |
| Sensitive asset scan | clear, 0 findings |

## Safety And Privacy

Shared account and public data values are represented by reference names and index references. No credentials, Cookies, Tokens, private URLs or browser state were added. The change does not grant new UI execution or write permissions.

## Installation Note

This record is part of the candidate package and must be installed together with the corresponding `ui-test` candidate files. The global installation remains separately audited with a backup and post-install hash comparison.

## Sections Changed

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Decision And Alternatives

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Impact Analysis

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Risks And Follow-up

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.
