# CR-20260816-001 - Artifact Envelope Dual Contract Closure

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | fixed / validation / governance |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance |
| Source | DS-PREDEV-001; HCE-V1-ARCH-20260816-001 section 5 |
| Baseline | Workspace before this repair; validator required sourceRefs/changeType not in normative schema |
| Author | Claude Code as execution Agent; Codex owns review and completion authority |
| Related Records | CR-20260815-003, CR-20260815-001 |

## Summary

Close the dual contract where validate_artifact_envelope independently required sourceRefs and changeType fields not in the normative schema. The runtime validator now mirrors the schema required list exactly.

## Context And Problem

The normative schema artifact-envelope.schema.json defines required as nine fields: artifactId, version, artifactType, owner, sourceAnchorId, sourceAnchorVersion, mappedFrAc, createdAt, derivedFrom. The runtime validator independently required sourceRefs and changeType instead of createdAt and derivedFrom. This created a dual contract violating NFR-TOT-003.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| scripts/development_runtime.py | validate_artifact_envelope | Replace sourceRefs/changeType with createdAt/derivedFrom to mirror normative schema |
| scripts/test_development_runtime.py | artifact envelope test | Replace sourceRefs/changeType with createdAt/derivedFrom |
| scripts/test_full_refactor_contract.py | vertical slice test | Replace sourceRefs/changeType with createdAt/derivedFrom |
| references/artifact-lifecycle-contract.md | Single-Contract Rule | Document DS-PREDEV-001 closure |

## Decision And Alternatives

The normative schema is the single source of truth. The runtime validator must require exactly the same fields as the schema required list.

## Impact Analysis

- An artifact carrying only normative schema fields now passes both schema and runtime validator.
- An artifact relying on sourceRefs or changeType must add createdAt and derivedFrom.
- No user-level Skill was modified; all changes are in the workspace copy.

## Validation Evidence

| Check | Method | Result |
|---|---|---|
| Runtime regression | test_development_runtime.py | pass |
| Full contract regression | test_full_refactor_contract.py | pass |
| Schema/validator parity | manual inspection | pass |

## Safety And Privacy

No credentials or production data were added. User-level installation remains out of scope.

## Risks And Follow-up

No open P0/P1 risk remains for this record. Re-run the schema/runtime parity regression whenever the Artifact Envelope schema changes.

Refs: DS-PREDEV-001, HCE-V1-ARCH-20260816-001 section 5, CR-20260815-003.
