# CR-20260809-003 - Generic Skill Governance Contract

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | fixed / validation / governance |
| Scope | core-skill-md / scripts-and-validation / safety-and-governance |
| Source | generic `create-skill --require-change-records` validation failure after global Phase 1 deployment |
| Baseline | generic validator: `review-required`, P0=0, P1=5; governance regression test failed on the missing `## Safety And Escalation` source marker in `scripts/validate_development_system.py` |
| Author | Codex |
| Related Records | CR-20260809-001, CR-20260809-002 |

## Summary

Repair the mismatch between `development-system`'s dedicated validator and the generic Skill governance validator without weakening either validation contract.

## Context And Problem

The dedicated Phase 1 validation passed, but the generic `create-skill` validator reported a missing safety/escalation heading, a noncanonical index heading, and a missing impact-analysis section in CR-20260809-002. The contract test also requires the validator source to visibly carry the canonical heading string so the governance contract remains auditable in code. The generic result was `review-required`; the P1 count included duplicated index/detail findings because the validator evaluates the record system during both general and strict passes.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Safety And Escalation | Rename the existing approval/refusal section to the canonical safety heading; its substantive rules are unchanged. |
| `change-records/index.md` | Latest Changes / Open Risks | Use the canonical index heading and record this repair's pending deployment risk. |
| `change-records/entries/.../CR-20260809-002-phase1-boundary-contract.md` | Impact Analysis | Add the required impact analysis for the prior Phase 1 change. |
| category ledgers | CR-20260809-003 entries | Record the affected core, validation, and safety/governance scopes. |
| `scripts/test_skill_governance_contract.py` | all | Add a focused governance regression test. |
| `scripts/validate_development_system.py` | governance checks | Require the canonical safety, index, and Phase 1 impact-analysis terms, plus a source-visible marker for the governance contract test. |

## Decision And Alternatives

Chosen: align the Skill's headings and records to the generic validator, then add local checks for the same contract.

Alternatives considered:

- Relax the generic validator: rejected because it is shared governance infrastructure and other Skills rely on its stable schema.
- Ignore the generic P1 findings because the dedicated validator passed: rejected because a deployable Skill needs both behavior and governance evidence.
- Add empty headings only: rejected because the Phase 1 record needs a substantive impact analysis, not a placeholder.

## Detailed Change

The repair keeps the existing approval rules intact while making their safety/escalation purpose explicit. It normalizes the record index to `## Latest Changes`, completes CR-20260809-002's impact analysis, and introduces a deterministic local regression that would fail again if those markers disappear. The validator source now also includes the canonical heading string so the contract test can verify the governance contract directly from code.

## Impact Analysis

- Functional behavior: no routing, A2A, Claude, Midscene, or deployment behavior changed.
- Governance: generic and dedicated validators now share explicit evidence for safety labeling and complete change-record structure.
- Maintenance: future Skill edits fail locally before global deployment if the canonical governance markers are removed.
- Risk: this change does not invoke live adapters, install packages, or expose sensitive data.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| RED regression | `python scripts/test_skill_governance_contract.py <skill-root>` before repair | failed | Missing `## Safety And Escalation` source marker assertion. |
| Dedicated regression | `python scripts/test_skill_governance_contract.py <skill-root>` after repair | passed | `SKILL_GOVERNANCE_CONTRACT_OK` |
| Phase 1 regression | `python scripts/test_phase1_boundary_contract.py <skill-root>` | passed | `PHASE1_BOUNDARY_CONTRACT_OK` |
| Dedicated validator | `python scripts/validate_development_system.py <skill-root>` | passed | `P0=0, P1=0, P2=0` |
| Generic validator | `python validate_create_skill.py <skill-root> --require-change-records` | passed | `accepted-with-constraints`, `P0=0, P1=0, P2=0` |
| Global validation | same checks against global Skill | passed | Global mirror matched workspace and all checks passed. |

## Safety And Privacy

No credentials, tokens, cookies, private keys, production data, or live adapter calls are involved. All edits begin in the approved workspace copy. Global deployment occurs only after the workspace checks pass and the deployment scope is authorized.

## Risks And Follow-up

- Until global deployment and validation finish, the global Skill retains the generic-governance P1 findings.
- The generic validator's duplicated P1 display is a reporting characteristic; this repair addresses the three unique missing artifacts.

Refs:

- `C:\Users\lenovo\.codex\skills\create-skill\references\change-record-traceability.md`
- `C:\Users\lenovo\.codex\skills\development-system\references\local-global-skill-edit-loop.md`
