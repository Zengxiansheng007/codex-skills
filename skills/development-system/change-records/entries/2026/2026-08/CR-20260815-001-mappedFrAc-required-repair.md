# CR-20260815-001 - Repair mappedFrAc Required In Artifact Envelope Schema

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system workspace copy |
| Change Type | fixed / validation / governance |
| Scope | references-and-assets / scripts-and-validation |
| Source | PH-01A regression failure after Claude timeout |
| Baseline | CR-20260814-001 workspace candidate |
| Author | Claude Code + Codex takeover |
| Related Records | CR-20260814-001; HND-DS-PH1A-REPAIR-20260815-003 |

## Summary

Require `mappedFrAc` in the artifact envelope schema, matching its existing `minItems: 1` rule and the AC-003 traceability contract. Complete the repair record after the bounded Claude recovery run timed out.

## Context And Problem

`scripts/test_phase_story_contract.py` reproduced a P1 contract mismatch: `mappedFrAc` was defined with `minItems: 1` but omitted from the schema's `required` array. The specialized validator passed because it checked presence and parsing but did not exercise this exact required-field invariant. Claude fixed the schema during an approved live recovery round, but the adapter timed out before Claude completed validation or change-record updates. Codex took over inside the same Story and workspace boundary.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `schemas/artifact-envelope.schema.json` | `required` | Added `mappedFrAc` so trace mapping cannot be omitted. |
| `change-records/index.md` | Latest Changes / Open Risks | Added this repair and corrected workspace deployment status. |
| `change-records/categories/references-and-assets.md` | outline + detail | Recorded the schema repair. |
| `change-records/categories/scripts-and-validation.md` | outline + detail | Recorded regression and validation evidence. |

## Decision And Alternatives

Chosen: make `mappedFrAc` required. This follows the existing schema description, `minItems: 1`, FR-007/FR-008 and AC-003.

Rejected alternatives:

- Remove the test assertion: rejected because it would weaken deterministic traceability.
- Allow empty or absent mappings for root artifacts: rejected because the requirement anchor has its own schema; artifact envelopes in this contract must map to FR/AC.
- Retry Claude again: rejected because the initial 600-second execution and bounded 300-second recovery both timed out, satisfying the confirmed Codex takeover condition.

## Detailed Change

The repair adds `mappedFrAc` to the JSON Schema `required` array. No enum, ownership, permission, runtime or external Skill behavior changes.

## Impact Analysis

- Artifact envelopes without requirement traceability now fail schema validation.
- PH1-ST-002 and PH1-ST-004 evidence aligns with AC-003 and AC-005.
- Existing valid fixtures remain compatible because they already include mappings.
- The change remains isolated to the workspace candidate and is not installed globally.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| RED reproduction | `python scripts/test_phase_story_contract.py` before repair | failed as expected | `artifact-envelope.schema.json: mappedFrAc must be in required` |
| Claude initial run | 600-second live adapter | timed out | `test-runs/claude-ph1a-live/manifest.json` |
| Claude bounded recovery | 300-second live adapter | timed out after applying schema edit | `test-runs/claude-ph1a-repair-live/manifest.json` |
| GREEN specialized validator | `python scripts/validate_development_system.py` | accepted, P0/P1/P2 = 0 | Codex takeover run 2026-08-15 |
| GREEN phase/story test | `python scripts/test_phase_story_contract.py` | `PHASE_STORY_CONTRACT_OK` | Codex takeover run 2026-08-15 |
| GREEN boundary tests | `test_phase1_boundary_contract.py`; `test_skill_governance_contract.py` | both passed | Codex takeover run 2026-08-15 |
| GREEN generic validator | `validate_create_skill.py . --require-change-records` | accepted-with-constraints, P0/P1/P2 = 0 | Codex takeover run 2026-08-15 |

## Safety And Privacy

No credential, network, production, install or global Skill action occurred. Claude and Codex were restricted to the approved workspace and validation evidence.

## Risks And Follow-up

- Full PH-01A validation passed; this repair is validated.
- PH1-ST-005 through PH1-ST-010 remain outside this repair.
- User-level installation remains approval-gated.

Refs:

- `../../../../../../handoff/HND-DS-PH1A-REPAIR-20260815-003.json`
- `../../../../../../test-runs/claude-ph1a-repair-live/feedback.json`
