# CR-20260906-001 - Phase Boundary Cross-Skill Documentation

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | grill-system |
| Change Type | governance / documentation |
| Scope | core-skill-md / references-and-assets / safety-and-governance / downstream-and-handoff |
| Source | approved ART-GRILL-PHASE-001 and GRILL-ST-003 delegation |
| Baseline | 2026-09-06 candidate capture: SKILL.md SHA-256 A99255D3469A81405BFA81CF20941BE7BE43FCAD28D8196D80D556FFDA63ED54; route/reference hashes captured before edit |
| Author | Codex |
| Related Records | CR-20260906-002, CR-20260906-003, CR-20260906-004 |

## Summary

Document one phase write boundary across all seven Grill routes and their downstream calls. The documentation uses the candidate runtime's proposed phase/result concepts but does not claim its scripts or schemas have passed behavior validation.

## Context And Problem

Earlier instructions could be read as allowing a callee, report, or confirmed question to resume formal writing. That conflicts with FR-001 through FR-013, especially the one-ledger, complete-freeze, explicit-closure, batch-writeback, exception, external-edit, and legacy-read-only requirements.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Operating Rules, Workflow, Decision Rules, Closure/Validation Gates, Formal Session Gate | Define the separation of process-ledger permission from formal-asset permission, ledger authority, phase/result distinction, closure evidence, authorized batch behavior, no-op versus updated receipts, notes-only, exception, external edits, active-Grill domain modeling suppression, and the V2 CLI. |
| references/routing-policy.md | Review Write Boundary | Make all seven routes inherit the same formal-asset freeze. |
| references/downstream-skill-map.md | Transition map | Gate formal writers on closure-backed eligible results and preserve non-writing outcomes. |
| references/question-packs/*.md | Phase Boundary | Add route-local instructions to update the ledger only while review is active. |

## Decision And Alternatives

The documentation aligns to the V2 runtime fields: `phase`, `result`, `questions`, `decisions`, `effectiveDecisions`, `openItems`, `closureEvidence`, `writebackPolicy`, `protectedAssets`, `processArtifacts`, `exceptions`, `recovery`, `checkpoints`, and `writebackReceipts`. The V2 schema remains the field-level authority. Global OS interception and a report-as-authority model were rejected by approved scope.

## Impact Analysis

- Covers requirements, test-case-design, design-review, risk-premortem, pre-implementation, failure-retrospective, and handoff-continuation.
- Calls to domain-modeling under active Grill return proposed decisions to the ledger; independent domain-modeling keeps its existing immediate-update behavior.
- Legacy records remain read-only and cannot create write authority.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source baseline | SHA-256 capture before edit | passed | Hashes recorded in this entry; exact candidate files were read before modification. |
| Documentation behavior | Final runtime, QA, and forward checks | passed within candidate scope | `development/evidence/root-independent/final-02/summary.json`; QA run 11; active-Grill domain forward keeps CONTEXT.md unchanged while standalone forward updates it. |
| Change-record integrity | Four package validators | passed | Final local `validate_create_skill.py --require-change-records` runs: exit 0 and P0/P1/P2 all zero for all four candidate Skills. |

## Safety And Privacy

Candidate-local documents only. No credentials, network, global Skill modification, OS interception, or formal business-asset write occurred.

## Risks And Follow-up

- Reconcile references with the final runtime schema/API before status can become `validated`.
- Run behavior tests that prove no per-answer formal writes, no report-based authority, one-use exceptions, external-edit preservation, and legacy-read-only handling.

Refs: FR-001 to FR-013; AC-001 to AC-013.
