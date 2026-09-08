# CR-20260815-002 - Full Runtime PH1B Through PH7

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | changed / governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | confirmed DS-PSR-001 requirements baseline and DS-REFRACTOR-RA-002 v1.1 |
| Baseline | PH-01A validated workspace with CR-20260815-001; PH1-ST-005 through PH7-ST-003 incomplete |
| Author | mixed Claude and Codex, with Codex completion authority |
| Related Records | CR-20260814-001, CR-20260815-001 |

## Summary

Implement the remaining PH1-ST-005 through PH7-ST-003 governance capabilities as one compatible contract family. The change extends the existing Requirement Anchor, Artifact and Phase/Story foundation rather than introducing a second router or state machine.

## Context And Problem

The confirmed requirements contain seven phases and 33 stories. The workspace previously validated only PH1-ST-001 through PH1-ST-004. Remaining behavior was documented in plans but not enforced by scripts, schemas, fixtures or the Skill entry workflow.

The first runtime red test found a P1 defect in MetaGPT admission ordering and fourteen missing negative fixtures. Claude fixed the function ordering and created five fixtures before a 420-second adapter timeout. Codex review found those JSON files contained UTF-8 BOM and caused the strict reader to crash. The authorized Codex takeover rebuilt all fourteen fixtures as UTF-8 without BOM, removed the one-time generator and preserved the original assertions.

The first generated RTM then found that NFR-003 and NFR-007 had no Story trace. This was a mapping omission rather than a scope change. The confirmed requirements baseline was revised from 1.0 to 1.1, with NFR-003 mapped to recovery Stories and NFR-007 mapped to the reusable Phase/Story contract and Agent-extension Story; the human HTML summary was updated in the same change.

The first extracted candidate exposed two delivery defects that source validation could not see. The full-refactor test depended on a requirements file outside the Skill package, and the PowerShell governance runner had written a hidden `.codex` audit directory under the development workspace that the generic packager copied. The repair added a portable 1.1 baseline fixture plus a deterministic sync script, and packages from a clean staging source that excludes governance/runtime cache directories without disabling governance.

## Sections Changed

| File group | Section | Change Summary |
|---|---|---|
| `SKILL.md` | rules, workflow, phase map, references, validation | Activate the full governance workflow and installation boundary. |
| `scripts/development_runtime.py` | deterministic control plane | Add Artifact, transition, authorization, event/snapshot, circuit, merge, interface, observability, resource and admission gates. |
| `scripts/test_development_runtime.py` | runtime regression | Test positive and negative runtime behavior and fixture semantics. |
| `scripts/test_full_refactor_contract.py` | full vertical slice | Verify 7 phases, 33 stories, schemas, references, fixtures and end-to-end completion control. |
| `scripts/sync_requirements_baseline.py` | portable baseline | Generate the package-local requirement trace fixture and compare it to the authority baseline when available. |
| `scripts/validate_development_system.py` | strong asset gate | Require all new contracts, schemas, fixtures, runtime functions and this change record. |
| `schemas/*.schema.json` | PH-01B through PH-07 data contracts | Add runtime, history, snapshot, completion, slot, role, Skill interface, resource and module-admission schemas. |
| `references/*.md` | operational contracts | Add handoff, rework, recovery, completion, long-task, workspace, Claude-first, profile, concurrency, observability and module-admission rules. |
| `assets/fixtures/negative/*.json` | bypass regressions | Add fourteen traced rejection cases. |
| `assets/fixtures/phase-story/full-refactor-baseline.json` | portable trace baseline | Keep installed-package tests independent of workspace-only paths. |

## Decision And Alternatives

The chosen design reuses MetaGPT role/SOP/Artifact concepts, Ralph L2 progress and circuit modules, and Temporal-inspired Event History plus Atomic Snapshot. It rejects importing a complete runtime because that would duplicate the Codex control plane and weaken independent Skill boundaries.

Deterministic code is used for hard gates. Narrative references explain when to invoke the gates and how independent Skills participate.

## Detailed Change

- PH1-ST-005: versioned independent handoff/feedback interface.
- PH1-ST-006: Artifact Owner rework and downstream gate reopening.
- PH1-ST-007: hash-linked Event History, Atomic Snapshot and resume gate.
- PH1-ST-008: governed states, Codex-only transition and CompletionEvaluator.
- PH1-ST-009: verified progress, repeated-failure, invalid-feedback, timeout, ten-round and HALF_OPEN limits.
- PH1-ST-010: workspace-copy-first and complete preauthorization.
- PH2-ST-001 through PH2-ST-005: Claude-first selection, self-approval on exact policy match, visible status and bounded takeover.
- PH3-ST-001 through PH3-ST-005: private software-company Profile pipeline and independent Skill interface.
- PH4-ST-001 through PH4-ST-004: long-task ledger, recovery and circuit runtime.
- PH5-ST-001 through PH5-ST-003: isolated execution slots, scheduling and merge gates.
- PH6-ST-001 through PH6-ST-003: safe status, resource limits and audit reconstruction.
- PH7-ST-001 through PH7-ST-003: MetaGPT admission classification and unified Agent extension contract.

## Impact Analysis

- Existing PH-01A schemas and route fixtures remain valid.
- Live Agent calls may proceed without a new prompt only when all six preauthorization dimensions match.
- Codex-local development now requires an allowed exception or a qualified takeover.
- Independent Skills remain separate packages; only their interface contracts are validated here.
- User-level installation is still blocked until a separate explicit user approval.
- Any missing reference, schema, negative fixture or runtime function becomes a validator failure.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Runtime red test | `test_development_runtime.py` before fixture completion | failed as expected | governance bypass plus fourteen missing fixtures |
| Claude bounded execution | HND-DS-RUNTIME-FIXTURES-20260815-004 live | timeout with valid synthesized feedback | `test-runs/claude-runtime-fixtures-live/` |
| Codex takeover runtime test | `test_development_runtime.py` | passed | `DEVELOPMENT_RUNTIME_OK` |
| Specialized validator | `validate_development_system.py` | accepted; P0/P1/P2 = 0/0/0 | validator JSON output |
| Full regression suite | runtime, full refactor, Phase/Story, Phase 1 boundary, Skill governance | passed | `DEVELOPMENT_RUNTIME_OK`, `FULL_REFACTOR_CONTRACT_OK` and legacy OK markers |
| Generic Skill validator | `validate_create_skill.py --require-change-records` | accepted-with-constraints; P0/P1/P2 = 0/0/0 | validator JSON output |
| RTM coverage | `build_refactor_reports.py` | 7 phases, 33 stories, uncovered IDs = 0 | `reports/development-system-full-refactor-rtm-2026-08-15.json` |
| Packaging dry-run | `skill_packager.py package --target codex --dry-run` | source and extracted mirrors have no missing or mismatched files | `install-candidate/verify/` |
| Extracted Codex package | specialized, runtime, full-refactor and generic Skill validators | passed; P0/P1/P2 = 0/0/0 | clean staging candidate under `install-candidate/canonical/` |
| Sensitive-data scan | specialized and generic validators | passed | no secret-pattern finding |

## Safety And Privacy

No credential values were added. Claude received only the approved workspace files and public requirement identifiers. Adapter output is stored under the controlled output root. The user-level Skill directory was not modified.

## Risks And Follow-up

- A successful workspace candidate still requires explicit user approval before installation.
- MetaGPT code modules remain reference-only until a concrete pinned candidate passes admission.
- PowerShell governance audit files are project evidence and are intentionally excluded from the portable Skill package.

Refs: DS-PSR-001, DS-REFRACTOR-RA-002 v1.1, HND-DS-RUNTIME-FIXTURES-20260815-004.
