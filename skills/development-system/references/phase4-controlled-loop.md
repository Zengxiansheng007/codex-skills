# Phase 4 Controlled Loop

## Phase 4 Goal

Phase 4 adds a reusable requirements hub above the existing handoff-system execution loop. It prepares the system for controlled automatic execution while keeping Codex anchored to requirements.

## Controlled Loop Shape

```text
User goal
  -> Codex requirement anchor
  -> research/grill gates when needed
  -> PRD + development plan + test plan
  -> A2A handoff packet
  -> dry-run adapter
  -> approved live adapter
  -> structured feedback packet
  -> Codex feedback review
  -> gap analysis and next-state decision
```

## Adapter Limits

Phase 4 may design and validate adapter contracts, dry-runs, manifests, command construction, output capture, and schema review.

Phase 4 must not silently enable unlimited autonomous execution. Live adapter calls remain approval-gated and bounded by:

- exact command or adapter scope;
- target workspace;
- allowed tools/actions;
- timeout and max-turn limits;
- expected feedback schema;
- loop limit;
- explicit stop conditions.

## Requirement Anchor Fields

Use complete fields for schema/reference/complex tasks:

- `originalGoal`
- `approvedScope`
- `nonGoals`
- `frAc`
- `confirmedDecisions`
- `authorityOrder`
- `allowedActions`
- `forbiddenActions`
- `manualConfirmActions`
- `sourceBaseline`
- `currentIterationObjective`
- `cycleId`
- `roundNumber`
- `sequenceIndex`
- `sentAt`
- `receivedAt`
- `stopConditions`
- `expectedFeedbackSchema`

Use the minimum subset only for simple narrative or ordinary execution steps.

## Loop State

The router must decide exactly one DS-PSR-001 governed runtime state after each feedback review:

- `running`
- `waiting-approval`
- `repair-needed`
- `requirements-review`
- `risk-gate-required`
- `blocked-user-decision`
- `blocked-external-dependency`
- `loop-limit-reached`
- `resource-limit-reached`
- `completed`
- `failed`

Cancellation or supersession is recorded as a requirement-lifecycle event and stops orchestration without adding a runtime state.
