# CR-20260817-003 - CLW-ST-202 Recovery And Bounded Takeover

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | repair / validation |
| Source | CLW-ST-202; FR-CLW2-005 through 007; AC-CLW2-006 through 009 |
| Author | Codex bounded takeover after Claude `claude-unavailable` |

## Summary

The live Claude Attempt exhausted its bounded provider retry window without a
feedback packet and made no ST-202 workspace changes. The active exact policy
allowed one same-Story Codex takeover. Red-light review found that persisted
aggregate snapshots added `writtenAt` and `snapshotHash` fields rejected by
their own schema, and recovery did not explicitly bind Phase/queue identity.

The repair aligns the persisted snapshot schema, records last event identity,
adds Phase/queue resume checks, strengthens aggregate reconciliation, and adds
crash-gap, tamper, drift and no-duplicate-resume tests and fixtures.

## Validation

Codex reran the dedicated PH-2 serial test and observed
`CLW_PHASE2_SERIAL_RUNTIME_OK`. The Claude `claude-unavailable` manifest
remains immutable evidence and is not rewritten as success. A later read-only
Claude validation Attempt is still required before the PH-2 aggregate gate.

## Safety

The takeover stayed inside the approved development-system workspace. No
network, dependency installation, global Skill write or user-level install
occurred.

## Context And Problem

The CLW-ST-202 recovery path had to preserve crash/retry evidence while keeping Codex as completion authority after Claude provider unavailability.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/development_runtime.py` | Recovery and aggregate snapshot handling | Align persisted snapshot fields and resume identity gates with the schema contract. |
| `assets/fixtures/clw-phase2/*` | Recovery fixtures | Add crash-gap, tamper, drift and no-duplicate-resume coverage. |
| `scripts/test_clw_phase2_serial_runtime.py` | Recovery tests | Verify strict recovery acceptance and rejection behavior. |

## Decision And Alternatives

Decision: perform a bounded same-Story Codex takeover and preserve the failed Claude attempt as immutable evidence. Alternative rejected: rewrite the unavailable Claude attempt as success, because downstream Agent output is evidence only.

## Impact Analysis

Recovery snapshots now reject stale or mismatched identity evidence more strictly. This affects recovery validation only and does not authorize global Skill writes or user-level installation.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| PH-2 serial runtime | `python scripts/test_clw_phase2_serial_runtime.py` | passed | `CLW_PHASE2_SERIAL_RUNTIME_OK` |

## Safety And Privacy

No credentials, production data, dependency installation, network write or global Skill deployment was involved.

## Risks And Follow-up

Read-only Claude validation remained a later gate; Codex completion still requires current validation evidence.
