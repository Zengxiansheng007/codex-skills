# CR-20260828-003: Governed popup announcement version sequence

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | added / governance |

## Summary

Adds a machine-maintained `runtime_state` partition, append-only sequence ledger, exclusive lock, atomic initializer and allocator. The Tianjin popup announcement branch consumes the sequence only after form and R2 preflight gates; system announcements do not consume it.

## Compatibility

Existing runtime indexes without `runtime_state` remain valid. Existing Source Cases and system-announcement execution remain unchanged. No new dependency is introduced.

## Context And Problem

Popup versions must increase exactly once per authorized run without moving the counter into editable case business data.

## Sections Changed

Runtime-state Schema, allocator, ledger, branch configuration and tests.

## Decision And Alternatives

Use an append-only governed sequence rather than deriving the next version from the UI or storing it in Source Case.

## Detailed Change

The Summary and Compatibility sections above retain the original detailed record.

## Impact Analysis

Popup runs allocate one auditable value; system-announcement runs do not consume the sequence.

## Validation

- Candidate pytest covers first value 1, later increments, duplicate-run rejection, concurrency uniqueness, human Hash preservation, sensitive references and branch filtering.
- Formal B branch R2 run `RVI-20260828-R2-B-002` passed with one visible-UI submission, `popup_version=1`, and `write_succeeded_verified`.
- Runtime-state readback proved `next_value=2` with one append-only allocation for the same run; the canonical report and evidence chain were validated separately.

## Validation Evidence

The original validation list above records allocator, concurrency, branch and formal evidence.

## Safety And Privacy

The ledger stores sequence metadata and evidence references, never credential values.

## Risks And Follow-up

Future v2 execution must keep the sequence reference-only until the authorized run allocation occurs.
