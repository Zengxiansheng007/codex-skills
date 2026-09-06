# CR-20260906-003 - Phase-Aware PRD Authoring

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | write-requirements-prd |
| Change Type | governance / contract |
| Scope | core-skill-md / safety-and-governance / downstream-and-handoff |
| Source | approved ART-GRILL-PHASE-001 and GRILL-ST-003 delegation |
| Baseline | 2026-09-06 candidate capture: SKILL.md SHA-256 A9AE880AADD6CB311F957B4F8A32C3B02780624FEF2EB530906F9458055368D3 |
| Author | Codex |
| Related Records | CR-20260906-001, CR-20260906-002, CR-20260906-004 |

## Summary

Prevent `write-requirements-prd` from writing a PRD while Grill is active or from treating a non-writing result as closure.

## Context And Problem

The former workflow said to resume after a Grill decision returned. It did not distinguish a single answer from whole-review closure or a legacy result from an authorized centralized PRD batch.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Operating Rules and References | Freeze body, metadata, version, status, dates, RTM, and substitute versions during active Grill; use local adapters that preserve the canonical write-prd contract. |
| SKILL.md | Workflow | Require closure-backed `review-ended` / `ready-for-writeback` before formal authoring resumes. |
| SKILL.md | Decision Rules | Recheck fresh baseline, preserve external edits, and selectively reopen semantic conflicts. |
| references/*.md | Local adapters | Provide resolvable pointers to the canonical shared contract, Grill adapter, and routing prerequisites. |

## Decision And Alternatives

The PRD author is a downstream writer, not a second review ledger. It relies on the Grill V2 contract for field validation and does not create an independent closure mechanism.

## Impact Analysis

- Supports FR-001 through FR-009 and FR-012, with AC-001, AC-002, AC-004 through AC-009, and AC-012.
- Keeps standalone PRD authoring intact when no active Grill boundary applies.
- Does not claim an OS-level write interceptor or runtime behavior validation.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source baseline | SHA-256 capture before edit | passed | Hash recorded above. |
| Cross-Skill review | Final Grill V2 contract review | passed | Uses `review-ended`, `ready-for-writeback`, public plan preparation, and closure-policy semantics. |
| Candidate validation | Root independent final-02 plus local package validator | passed within candidate scope | `development/evidence/root-independent/final-02/summary.json`; final local write-requirements-prd validator exit 0 with P0/P1/P2 all zero. |

## Safety And Privacy

Candidate-only instructions. No PRD, metadata, global Skill, credential, network, or external system was changed.

## Risks And Follow-up

Run the final candidate validator and behavior scenarios for notes-only, exception consumption, external drift, partial failure, and legacy-read-only before marking validated.

Refs: FR-001 to FR-009, FR-012; AC-001, AC-002, AC-004 to AC-009, AC-012.
