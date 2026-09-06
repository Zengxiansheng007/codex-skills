# CR-20260906-004 - Active-Grill Domain Modeling

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | domain-modeling |
| Change Type | governance / downstream contract |
| Scope | core-skill-md / safety-and-governance / downstream-and-handoff |
| Source | approved ART-GRILL-PHASE-001 and GRILL-ST-003 delegation |
| Baseline | 2026-09-06 candidate capture: SKILL.md SHA-256 152E2C97239AFFB12A60C5F4A7E74AB546A49AE169688C81F4E2CCC42DAFA579 |
| Author | Codex |
| Related Records | CR-20260906-001, CR-20260906-002, CR-20260906-003 |

## Summary

Add a caller-scoped mode that sends domain-model proposals to the Grill ledger while keeping standalone domain-modeling immediate and unchanged.

## Context And Problem

Domain-modeling requires immediate CONTEXT.md and occasional ADR updates when terms crystallize. Under active Grill, that behavior conflicts with the required freeze of formal assets and centralized post-closure writeback.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Grill Invocation Boundary | Define proposal-only output under active Grill, closure-backed writeback, external-edit preservation, and independent standalone behavior. |

## Decision And Alternatives

Suppressing all domain-modeling writes would break its independent workflow; leaving immediate writes active under Grill would violate FR-002 and AC-002. The new instruction scopes suppression to an explicit active Grill invocation.

## Impact Analysis

- Supports FR-002, FR-004, FR-005, FR-007, FR-008, FR-010, and AC-002, AC-004, AC-007, AC-008, AC-010.
- Requires the Grill caller to propagate active phase context and consume proposal output in its authoritative ledger.
- Does not alter CONTEXT-FORMAT.md or ADR-FORMAT.md because output formatting is unchanged after eligible writeback.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source baseline | SHA-256 capture before edit | passed | Hash recorded above. |
| Contract review | Final V2 phase-boundary review | passed within candidate scope | Active Grill has proposal-only ledger output; standalone behavior remains separate and immediate. |
| Candidate validation | Domain forward review plus final local package validator | passed within candidate scope | `candidate/evidence/domain-forward/forward-result.json` records unchanged active CONTEXT.md and updated standalone CONTEXT.md; final validator exit 0 with P0/P1/P2 all zero. |

## Safety And Privacy

Candidate-local documentation only. No CONTEXT.md, ADR, global Skill, credential, or external system was changed.

## Risks And Follow-up

Validate caller-context propagation and both behavior branches before marking this record validated.

Refs: FR-002, FR-004, FR-005, FR-007, FR-008, FR-010; AC-002, AC-004, AC-007, AC-008, AC-010.
