# Control Plane And Authority Contract

> Maps: FR-001, FR-002, FR-003, FR-004, FR-005 ｜ AC-001, AC-002 ｜ Story: PH1-ST-001

## Purpose

Freeze the control plane, authority order, internal Profile ownership and independent Skill boundaries so that later phases can extend contracts without re-litigating control.

## Authority Order

The system must fix and validate the following precedence, highest first:

1. `user-confirmed grill decisions`
2. `final requirements baseline (DS-PSR-001)`
3. `active requirement anchor`
4. `runtime evidence`

Codex is the **sole control plane**. Only Codex may approve state transitions, Agent invocations, risk gates, rework routing and `completed` writes.

## Independent Skill Ownership

The following skills retain **single ownership** and may only be called through versioned interfaces:

| Skill | Owned By | development-system may |
|---|---|---|
| `research` | independent skill | route to and consume evidence |
| `grill-system` | independent skill | route to and consume decisions |
| `write-prd` | independent skill | route to and consume PRD/plan artifacts; delegates PRD/plan work to child skills |
| `handoff-system` | independent skill | call interface contract only; must not duplicate handoff internals |
| `ui-test-system` | independent skill | route to and consume UI-test results |

development-system **must not** copy, rename, shadow or implicitly replace any independent Skill.

`write-prd` is the routed entry point for PRD and plan work. `write-requirements-prd`, `architecture-design`, `development-plan`, and `test-plan` remain downstream child skills owned by `write-prd`, not direct replacement routes inside `development-system`.

## Internal Private Profiles

The five business roles are **private namespace profiles** inside `development-system`:

| Profile | Namespace | Responsibility |
|---|---|---|
| `product-requirement` | `development-system/profiles/product-requirement` | requirement anchor, scope, FR/AC |
| `architect` | `development-system/profiles/architect` | architecture artifact, interface contracts |
| `project-planner` | `development-system/profiles/project-planner` | phase/story decomposition, dependencies |
| `engineer` | `development-system/profiles/engineer` | implementation, change evidence |
| `qa` | `development-system/profiles/qa` | independent verification, defect attribution |

These profiles **must not** register as global skills with conflicting names. The validator rejects any ownership claim where a private profile clashes with a global same-name skill (AC-001).

## MetaGPT Hybrid Reuse Classification

Every MetaGPT-derived object must declare exactly one of:

| Classification | Meaning | Phase 1 |
|---|---|---|
| `contract-reuse` | Reuse the concept/contract; implement locally. | allowed |
| `code-admission-candidate` | Candidate for code-level admission in a later phase. | record only; no runtime admission in Phase 1 |
| `reference-only` | Reference for design; no code or contract import. | allowed |

An object without exactly one classification is rejected (AC-002). Phase 1 must not depend on the full MetaGPT runtime.

## Validation Hooks

- `validate_development_system.py` must reject ownership conflicts and missing authority entries.
- Negative fixtures must prove that a private profile registered as a global same-name skill is rejected.
