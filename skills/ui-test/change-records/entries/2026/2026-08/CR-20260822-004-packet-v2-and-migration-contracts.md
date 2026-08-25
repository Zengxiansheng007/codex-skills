# CR-20260822-004 - Packet v2 And Migration Contracts

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test |
| Story | PH01-ST04 |
| Requirements | FR-CASE-014, FR-CASE-040, FR-CASE-050 |
| Acceptance | AC-CASE-008, AC-CASE-016, AC-CASE-024 |

## Summary

Promote Packet v2 with `module_path` as the only executable packet contract. Packet v1 is deprecated and rejected from direct execution. Add a deterministic dry-run migration adapter that preserves the source, returns a candidate sidecar, and emits a strict machine-readable migration issue list with stable problem codes and blocking semantics.

## Context And Problem

Legacy packet variants were interpreted inconsistently downstream.

## Sections Changed

Packet v2 schema, validator and migration issue contracts.

## Decision And Alternatives

Reject direct v1 execution and centralize adaptation in a dry-run migration layer.

## Impact Analysis

Downstream Skills consume only one executable packet shape.

## Boundary

The adapter does not write a sidecar, overwrite a source, execute a packet, or migrate formal assets. Binding compatibility and plan staleness are consumed by later Compiler and preflight Stories.

## Validation Evidence

- Full candidate `ui-test` suite: 63 tests passed.
- Packet v2 positive, v1 migration-required, R1-write, unknown action and unknown version fixtures pass.
- v1 dry-run preserves source bytes semantically, maps module to module_path and validates the candidate.
- Unknown source versions fail closed with `E_MIGRATION_PACKET_VERSION_UNSUPPORTED`.
- Migration Issue List passes Draft 2020-12 validation.

## Safety And Privacy

Migration does not overwrite source data or persist credentials.

## Risks And Follow-up

Blocking issues require review before sidecar activation.
