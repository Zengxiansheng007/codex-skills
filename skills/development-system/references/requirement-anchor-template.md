# Requirement Anchor Template

Use this reference when a task is complex, schema-bearing, cross-Skill, global, A2A, or otherwise needs a saved anchor before implementation.

## Purpose

A requirement anchor is the small, stable contract Codex uses to prevent drift. It is not a full PRD. It preserves the user-approved target and the evidence needed to decide whether work can continue or finish.

## Minimum Fields

Use the minimum fields for ordinary local work:

```json
{
  "originalGoal": "",
  "approvedScope": [],
  "nonGoals": [],
  "acceptanceCriteria": [],
  "sourceBaseline": [],
  "approvalGates": [],
  "stopConditions": [],
  "currentIterationObjective": "",
  "nextState": "continue"
}
```

## Complete Fields

Use complete fields for schema, reference, Skill, global, adapter, or long-running tasks:

```json
{
  "cycleId": "",
  "roundNumber": 1,
  "sequenceIndex": 1,
  "sentAt": "",
  "receivedAt": "",
  "originalGoal": "",
  "approvedScope": [],
  "nonGoals": [],
  "frAc": [],
  "confirmedDecisions": [],
  "authorityOrder": [],
  "allowedActions": [],
  "forbiddenActions": [],
  "manualConfirmActions": [],
  "sourceBaseline": [],
  "currentIterationObjective": "",
  "expectedFeedbackSchema": "",
  "stopConditions": [],
  "nextState": "continue"
}
```

## Rules

- Store the anchor as Markdown or JSON when the task will span phases, files, Skills, or Agents.
- Update the anchor only when the user confirms a scope or decision change.
- Treat implementation output, test output, and Agent feedback as evidence against the anchor, not as a replacement for it.
- If a later user confirmation conflicts with the anchor, route to requirements review before continuing.

