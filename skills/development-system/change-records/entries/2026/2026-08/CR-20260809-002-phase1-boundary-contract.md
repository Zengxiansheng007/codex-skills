# CR-20260809-002 - Phase 1 Boundary Contract

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | governance / validation / fixture |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user-confirmed Phase 1 decision: single-file behavior changes also require workspace-copy-first |
| Baseline | `validate_development_system.py` accepted before change; new Phase 1 boundary regression test failed before implementation |
| Author | Codex |
| Related Records | CR-20260809-001 |

## Summary

Add a Phase 1 boundary contract and deterministic validation coverage so `development-system` can enforce route boundaries, workspace-copy-first scope, approval gate fields, and final-state evidence rules.

## Context And Problem

Phase 1 research and grill confirmed that `workspace-copy-first` should not be limited to multi-file, high-risk, or global Skill changes. A single-file behavior change can still alter validation, routing, approval, adapter, final-state, or handoff semantics. The previous skill copy did not expose this as a hard contract or validate it.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Non-negotiable Rules | Added mandatory workspace-copy-first scope, including single-file behavior changes. |
| `SKILL.md` | Router Workflow / Routing Map / References | Added Phase 1 boundary contract as a required routing reference. |
| `references/phase1-boundary-contract.md` | all | Added route boundary rules, mandatory workspace-copy-first triggers, direct edit exception, approval boundary template, and final-state decision table. |
| `references/local-global-skill-edit-loop.md` | Mandatory scope | Added mandatory workspace-copy-first scope. |
| `references/router-contract.md` | Input classification | Added workspace-copy-first boundary check. |
| `assets/fixtures/router-single-file-behavior-change.json` | all | Added regression fixture for single-file behavior change routing. |
| `scripts/test_phase1_boundary_contract.py` | all | Added focused regression test for Phase 1 boundary artifacts. |
| `scripts/validate_development_system.py` | required files and semantic checks | Added checks for boundary contract, fixture, markers, and CR-20260809-002. |
| `scripts/validate_handoff_codex_system.py` | package required files | Added package-level coverage for new reference and fixture. |

## Decision And Alternatives

Chosen: add a dedicated `phase1-boundary-contract.md` reference and keep `SKILL.md` as the concise router.

Alternatives considered:

- Put the whole boundary matrix in `SKILL.md`: rejected because it would bloat the top-level router.
- Only update `local-global-skill-edit-loop.md`: rejected because the route, approval, and final-state boundaries cut across multiple workflows.
- Rely on prose without validator coverage: rejected because the original defect was weak operational enforcement.

## Impact Analysis

- Routing: future Skill behavior changes are classified through the Phase 1 boundary contract instead of relying on unstated judgment.
- Execution safety: workspace-copy-first applies to single-file behavior changes as well as multi-file, high-risk, and global Skill work.
- Approval control: live, deploy, install, and external-write actions require an exact-scope approval record.
- Completion control: the final-state table prevents `completed` when P0/P1 drift, missing evidence, invalid feedback, skipped critical validation, unapproved global write, or unmapped action remains.
- Compatibility: no live adapter, third-party service, or persisted user data behavior changed.

## Validation Evidence

| Check | Command or Method | Result |
|---|---|---|
| RED test | `python scripts/test_phase1_boundary_contract.py <skill-root>` before implementation | failed on missing `phase1-boundary-contract.md` in `SKILL.md` |
| Phase 1 boundary regression | `python scripts/test_phase1_boundary_contract.py <skill-root>` | passed |
| development-system validator | `python scripts/validate_development_system.py <skill-root>` | passed, accepted |
| package-level validator | `python scripts/validate_handoff_codex_system.py <system-root>` | passed, accepted |
| sensitive scan | validator secret-pattern scan | passed |

## Safety And Privacy

No credentials, tokens, cookies, private keys, or production-only secrets were added. The change was made only in the workspace copy. Global deployment remains approval-gated.

## Risks And Follow-up

- Not deployed to global Skill directory in this turn.
- Live Claude and Midscene execution were not part of this change.
