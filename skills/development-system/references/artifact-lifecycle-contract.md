# Artifact Lifecycle Contract

> Maps: FR-006, FR-007, FR-032 ｜ AC-003 ｜ Story: PH1-ST-002, DS-PREDEV-001

## Purpose

Ensure every artifact can be traced back to a requirement anchor, FR/AC mapping, version, owner and change source.

## Artifact Envelope

Every PRD, architecture, phase, story, handoff, feedback, test evidence, defect and completion decision must carry an envelope matching `schemas/artifact-envelope.schema.json`:

| Field | Required | Notes |
|---|---|---|
| `artifactId` | yes | stable unique id |
| `version` | yes | bumped on any change |
| `artifactType` | yes | one of the enum values |
| `owner` | yes | single resolvable owner profile or skill |
| `sourceAnchorId` | yes | anchor this artifact derives from |
| `sourceAnchorVersion` | yes | anchor version at derivation time |
| `mappedFrAc` | yes | at least one FR or AC id |
| `createdAt` | yes | timestamp |
| `derivedFrom` | yes | upstream artifact ids (empty for root) |
| `supersedes` | no | artifact ids this one replaces |
| `contentHash` | no | integrity hash |
| `evidenceRefs` | no | linked evidence artifact ids |

### Single-Contract Rule (DS-PREDEV-001)

The normative field set is defined **exclusively** by `schemas/artifact-envelope.schema.json`. The runtime validator `development_runtime.validate_artifact_envelope()` must require exactly the same fields as the schema — no more, no less. Previous versions of the runtime independently required `sourceRefs` and `changeType`, which were never part of the normative schema. This dual contract has been closed: the runtime validator now mirrors the schema's `required` list.

## Traceability Rule (AC-003)

Any artifact must be traceable in both directions:
- **backward**: artifact → anchor → FR/AC → original goal;
- **forward**: goal → FR/AC → anchor → artifact → evidence → completion decision.

The validator rejects any artifact whose `sourceAnchorId`, `sourceAnchorVersion`, `mappedFrAc` or `owner` is missing or unresolvable.

## Change Governance (FR-032)

When an artifact's contract changes:
1. create a change record with impact analysis;
2. bump the artifact version;
3. declare `supersedes` if replacing an old version;
4. reopen downstream gates for affected artifacts;
5. re-validate within the new acceptance scope.

## Phase 1 Boundary

Phase 1 only requires the envelope, traceability and change-record rules. Runtime event history, snapshots and completion evaluation runtimes are deferred to later phases but their contracts must remain extensible.
