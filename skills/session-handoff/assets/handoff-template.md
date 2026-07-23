# Session Handoff: <task-name>

Generated: <ISO-8601 timestamp>
Scope: <what the next agent should continue>
Output Status: <accepted | accepted-with-constraints | review-required>

## 1. Handoff Objective

- [V/R/?] <One sentence describing what the next agent must continue.>

## 2. Current Status

- [V/R/?] Current phase:
- [V/R/?] Done:
- [V/R/?] Not done:
- [V/R/?] Current blocker:

## 3. Completed Work

| Item | Evidence | Notes |
|---|---|---|
| <completed item> | <path, command summary, report, or confirmation> | <important caveat> |

## 4. Unfinished Work And Next Actions

| Priority | Next Action | Input / Path | Completion Criteria |
|---|---|---|---|
| P0 | <next action> | <path or prerequisite> | <observable done condition> |

## 5. Key Decisions

| Decision | Reason | Evidence |
|---|---|---|
| <decision> | <why> | <path or confirmation> |

## 6. Important Files And Reports

| Type | Path / URL | How The Next Agent Should Use It |
|---|---|---|
| <type> | <path> | <usage> |

## 7. Risks, Blockers, And Forbidden Actions

- [V/R/?] Risks:
- [V/R/?] Blockers:
- [V/R/?] Do not:
- [V/R/?] Requires user confirmation:

## 8. Suggested Skills

| Order | Skill | Purpose |
|---|---|---|
| 1 | <skill-name> | <why it should be invoked> |

## 9. Sensitive Information Handling

- Redacted items:
- Safe references:
- Data the user must re-provide:

## 10. Recovery Prompt For The Next Agent

```text
Read this handoff first: <handoff-path>
Then briefly restate the objective, current status, unfinished work, risks, and first next action.
Do not execute risky actions until the listed confirmation gates are satisfied.
```
