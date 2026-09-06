# CR-20260906-002 - Phase-Aware Grill Routing

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | write-prd |
| Change Type | governance / contract |
| Scope | core-skill-md / references-and-assets / safety-and-governance / downstream-and-handoff |
| Source | approved ART-GRILL-PHASE-001 and GRILL-ST-003 delegation |
| Baseline | 2026-09-06 candidate capture: SKILL.md SHA-256 05400AC408A2924F0DE5A4380348146880DE24C8544919AA64EEF97AB20DA3B2; adapter SHA-256 7B68A9FCB71F8DB144BCE7B2DBF70CED69469D87C1D5B075BB228FE948C729CB |
| Author | Codex |
| Related Records | CR-20260906-001, CR-20260906-003, CR-20260906-004 |

## Summary

Make `write-prd` a phase-aware recipient of Grill results. It keeps governed artifacts frozen during review and routes one closure-backed eligible result to centralized batch writing.

## Context And Problem

The prior adapter allowed `write-requirements-prd` to resume after any Grill return and exposed a legacy status-only shape. That could convert reports or per-question progress into unreviewed formal writes.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Operating Rules, Routing Workflow, Decision Rules | Inherit the Grill freeze and validate the phase-aware return before formal writing. |
| references/grill-system-requirements-adapter.md | Phase Boundary, Call Contract, Return Contract | Replace immediate resumption with semantic phase/result, closure, policy, scope, checkpoint, exception, receipt, and no-op versus updated handling. |
| references/shared-contracts.md | Grill Phase Boundary | Add the shared artifact-level freeze, centralized writeback, external edit, and capability rules. |
| references/baseline-selection.md | Spec Kit exclusion | Exclude incremental merge/save/validation behavior. |

## Decision And Alternatives

The adapter names candidate runtime concepts but defers field-level enforcement to the final session schema. Keeping the former immediate-resume contract or adopting Spec Kit's incremental save policy would contradict the approved requirements.

## Impact Analysis

- `write-requirements-prd` now has a documented formal-writing gate.
- Architecture, development-plan, and test-plan consumers inherit the shared artifact boundary when routed through `write-prd`.
- Existing artifact status mapping remains separate from Grill phase/result.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source baseline | SHA-256 capture before edit | passed | Hashes recorded above. |
| Reference consistency | Final V2 API review | passed | Uses public `propose-question` and `prepare-writeback-plan`; no private fingerprint algorithm is specified. |
| Behavior and package validation | Root independent final-02 plus local package validator | passed within candidate scope | `development/evidence/root-independent/final-02/summary.json`; final local write-prd validator exit 0 with P0/P1/P2 all zero. |

## Safety And Privacy

Candidate-local documentation only. No global Skill installation, credentials, network access, or formal artifact write.

## Risks And Follow-up

Reconcile this semantic adapter against the final candidate schema and run behavior tests for closure, notes-only, legacy-read-only, exceptions, and external edit conflict handling.

Refs: FR-001, FR-002, FR-004 to FR-012; AC-001, AC-002, AC-004 to AC-012.
