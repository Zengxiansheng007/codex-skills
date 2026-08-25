---
name: ui-test-plan
description: Create and review UI-test planning packets from PRD, design, Figma, HTML prototype, live URL, code evidence, and knowledge base sources. Use for test-point decomposition, coverage matrix design, ambiguity discovery, automation candidate screening, and execution readiness before Midscene exploration.
---

# UI Test Plan

## Purpose

Turn source material into an execution-ready `ui-test-packet` for UI exploration and verification.

## Operating Rules

- Do not assume PRD, design, Figma, HTML prototype, code, or live UI is current. Record source version and confidence.
- Use source-grounded reasoning. If knowledge is missing or low confidence, mark it for confirmation instead of inventing facts.
- Separate business test design from UI execution details.
- Do not pass a flow to exploration until risk, scope, expected result, forbidden actions, and evidence requirements are explicit.
- Create or update the governed Source Case as the only case truth. Do not author separate Human/Midscene/Playwright case bodies.
- Declare P0/P1/P2, five-field scope, branch, test-point responsibility, applicable component variant, and separate setup/feature/assertion sections.
- Resolve output locations only through the `ui-test` project config and Path Planner. A missing v2 config blocks new formal assets.

## Workflow

1. Build a source inventory with version, timestamp, owner if known, and confidence.
2. Identify business objects, module boundaries, roles, states, permissions, upstream/downstream dependencies, and hidden conditions.
3. Produce test points covering normal flow, abnormal flow, boundary, permission, state transition, data dependency, and upstream/downstream consistency.
4. Mark ambiguity as P0/P1/P2 questions and route unresolved P0 issues to human confirmation.
5. Screen automation candidates and define evidence expectations.
6. Output or update `ui-test-packet` with `next_action: explore` when ready.

## Validation

- Every test point traces to at least one source reference or explicit assumption.
- P0 ambiguity is closed or blocks execution.
- Forbidden actions are listed before exploration.
- Expected results are specific enough to verify.

Read [the planning checklist](references/planning-checklist.md) before marking a packet execution-ready.

## Safety

Planning grants no execution permission. Block plans with unresolved P0 ambiguity, unknown environment, missing forbidden actions, embedded credentials, or unreviewed write scope.
