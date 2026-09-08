# Naming And Boundaries

## Chosen Name

- Skill name: `development-system`
- Human-readable name: `Development System`
- Role: reusable total router for requirement-driven Codex development work.

## Why Not Rename `handoff-system`

`handoff-system` is already a useful downstream execution-loop system. Renaming it would blur two responsibilities:

- `development-system`: requirement anchoring, evidence gates, planning, routing, and final decision control.
- `handoff-system`: A2A handoff loop orchestration and execution feedback cycle.

Keeping them separate makes the ecosystem easier to test, package, install, and evolve.

## Skill System Boundary

`development-system` may call or route to other skills, but it should not duplicate their detailed instructions. It owns:

- route selection;
- requirement-anchor lifecycle;
- authority order;
- stop and approval decisions;
- phase progression;
- final gap-to-requirement review.

It does not own:

- external research methodology details;
- grill question workflow details;
- PRD template internals;
- Claude CLI implementation internals;
- Midscene browser execution;
- packaging and installation mechanics.
