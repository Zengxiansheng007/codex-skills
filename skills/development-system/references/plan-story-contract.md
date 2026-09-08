# Phase And Story Contract

> Maps: FR-008 ｜ AC-005 ｜ Story: PH1-ST-004

## Purpose

Ensure complex goals are decomposed into phases with entry/exit criteria and stories that are small, testable, mapped to FR/AC, dependencies and evidence requirements.

## Phase Requirements

A phase must declare:

| Field | Required | Validation |
|---|---|---|
| `phaseId` | yes | unique within the system |
| `name` | yes | human-readable |
| `goal` | yes | one sentence |
| `entryCriteria` | yes | at least one |
| `exitCriteria` | yes | at least one |
| `runtimeBoundary` | no | Phase 1 = contract/schema/fixture/validator only |
| `stories` | yes | at least one |

A phase missing `entryCriteria`, `exitCriteria` or `stories` is rejected.

## Story Requirements

A story must declare:

| Field | Required | Validation |
|---|---|---|
| `storyId` | yes | unique |
| `title` | yes | |
| `goal` | yes | |
| `mappedRequirements` | yes | at least one FR id |
| `acceptanceCriteria` | yes | at least one AC id |
| `dependsOn` | yes | may be empty; cyclic deps rejected |
| `testability` | yes | how this story is deterministically tested |
| `evidenceRequirements` | yes | at least one evidence artifact |

A story missing any of `mappedRequirements`, `acceptanceCriteria`, `testability` or `evidenceRequirements` is rejected (AC-005).

## Dependency Cycle Rule

The validator must detect cyclic dependencies among stories and reject them. A cycle exists if following `dependsOn` from any story returns to itself.

## Forward Evolvability (NFR-007)

Phase 1 story ids, state values and core contract fields must be directly extensible by later phases. No field name or enum value may be repurposed.

## Schema

Phase and story objects must validate against `schemas/phase-story.schema.json`.
