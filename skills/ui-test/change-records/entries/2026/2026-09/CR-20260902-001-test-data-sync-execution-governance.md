# CR-20260902-001 - Test Data, Sync And Execution Governance

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test workspace candidate |
| Change Type | added / changed / fixed / validation / governance |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | approved user requirements and implementation authorization |
| Baseline | `manifests/global-source-baseline.json`; 140 files copied byte-identically to `manifests/candidate-initial-baseline.json` |
| Author | Codex |
| Related Records | AUTH-UI-TEST-REPAIR-20260902-001 |

## Summary

Implement the approved v2 business-parameter, deterministic compilation, synchronization, execution guard, failure/repair logging, migration and cleanup-governance closure in a clean workspace candidate.

## Context And Problem

The current v1 design keeps business-value rules in Source Case and executable Python, emits incomplete release manifests, conflates release damage with current input drift, and places Tianjin-specific publish/verify scripts inside the generic Skill. The current A/B formal assets therefore remain audit-only until a validated v2 successor is produced.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` and `references/asset-governance.md` | project asset governance | Define Source Case/Test Data ownership and v2 execution eligibility. |
| `schemas/*v2*.json` and `schemas/contract-registry.json` | artifact contracts | Register the complete v2 contract family. |
| `scripts/ui_test_core/*` | deterministic runtime | Add strict loading, typed resolution, compiler, verifier, sync, guard, event store and migration/cleanup planners. |
| `tests/*` | regression evidence | Cover positive, negative, drift, concurrency, recovery and scope boundaries. |
| project adapter and migration fixture | Tianjin A/B candidate | Keep business locators/values outside the generic package and exercise controlled migration. |

## Decision And Alternatives

Use Source Case for test semantics and branch-level `tests/test-data.json` for manually editable business values. Use the standard library for RFC 6901 resolution and Windows file locks because installing `jsonpointer` or `portalocker` is not authorized. Preserve v1 as audit-readable and write only v2 successors.

## Detailed Change

Added the complete v2 contract family, strict loader and RFC 6901 resolver, compiler and shared parameter manifest, exact release verifier, plan-bound synchronization, frozen execution data session, derived run parameters, immutable snapshot, product diagnostics event store, RunResult/evidence linker and migration/cleanup planners. Removed three project-specific scripts from the generic package and added the Tianjin A/B adapter, fixed sync/materialization scripts and offline migration fixture.

## Impact Analysis

The generic package gains deterministic reusable contracts and runtimes. The Tianjin adapter owns case paths, locators and business mappings. Historical formal assets and the global installed Skill remain unchanged.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source/candidate baseline | governed copy and per-file SHA-256 comparison | passed | `manifests/global-source-baseline.json`; `manifests/candidate-initial-baseline.json` |
| Focused and full validation | `python -B -m pytest -p no:cacheprovider ...` | passed, 247 tests | `../evidence/validation-summary.json` |
| Skill structure | `validate_create_skill.py ... --require-change-records` | passed, no findings | `../evidence/validation-summary.json` |
| Sensitive and scope scan | candidate scan plus active-surface test | passed, zero findings | `../evidence/validation-summary.json` |
| Migration and cleanup | offline rehearsal against read-only formal inventory | passed, two successors and zero deletion | `../evidence/migration-cleanup/` |

## Safety And Privacy

No credential values or prohibited sensitive values are copied into the candidate. Public research, if needed, must not receive local project content. Global installation, formal D-drive migration, actual deletion and real UI/R2 remain separate gates.

## Risks And Follow-up

- PowerShell governance incident capture under the project root is read-only in this sandbox; candidate work used the writable `work` root and retained eight diagnosed incident records.
- Windows process-crash recovery is in scope; power-loss durability beyond filesystem guarantees remains an explicit limitation.
- Global installation, formal migration/active switch, actual formal cleanup and live UI/R2 remain separate approval gates after candidate completion.

Refs: RA-UI-TEST-REPAIR-20260830@v0.5; PRD-UI-TEST-REPAIR-20260830@v0.3; ARCH-UI-TEST-REPAIR-20260902@v0.2.
