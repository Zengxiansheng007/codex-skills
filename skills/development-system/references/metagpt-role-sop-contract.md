# MetaGPT Role SOP Contract

> Maps: FR-004, FR-009 ｜ AC-004 ｜ Story: PH1-ST-003

## Purpose

Define the five business roles, their SOP stages, entry/exit conditions, artifacts and ownership boundaries following MetaGPT's structured collaboration model, while keeping Codex as the sole control plane.

## Roles

| Role Profile | SOP Stages Owned | Key Artifacts |
|---|---|---|
| `product-requirement` | requirement, architecture(input) | requirement anchor, scope decisions |
| `architect` | architecture | architecture artifact, interface contracts |
| `project-planner` | planning | phase/story contract, dependency graph |
| `engineer` | implementation | implementation evidence, change records |
| `qa` | QA, completion(input) | test evidence, defect reports |

Each role owns exactly the artifacts listed. Roles must not overlap ownership.

## SOP Stage Definitions

| Stage | Entry Condition | Artifact Produced | Owner | Exit Condition |
|---|---|---|---|---|
| Requirement | Anchor approved or user goal received | requirement anchor | `product-requirement` | anchor has FR/AC, scope, non-goals |
| Architecture | Requirement anchor version locked | architecture artifact | `architect` | interfaces, ownership and boundaries defined |
| Planning | Architecture artifact version locked | phase/story contract | `project-planner` | stories map FR/AC, dependencies, testability |
| Implementation | Phase/story approved and workspace copied | implementation evidence | `engineer` | changed files map to approved scope |
| QA | Implementation evidence available | test evidence, defect reports | `qa` | independent verification passes or defects routed |
| Rework | Defect routed to owner | updated artifact | original owner | upstream artifact version bumped and downstream gates reopened |
| Completion | All evidence and drift checks pass | completion decision | Codex CompletionEvaluator only | Codex writes `completed` |

## Non-overlap Rule

No two roles may own the same artifact type. The validator rejects ownership overlap (AC-004).

## Codex Control Plane Boundary

Roles produce artifacts and evidence; they do not:
- approve state transitions;
- invoke Agents;
- write `completed`;
- bypass risk gates.

These remain Codex-only.
