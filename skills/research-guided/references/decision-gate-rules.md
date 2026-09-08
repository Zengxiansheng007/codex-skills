# Decision Gate Rules

## Final Review Checklist

Codex must verify before deciding pass:

1. Coverage of all requirement items (FR-RES-001 through FR-RES-012).
2. Coverage of development plan phases (PH-0 through PH-6).
3. Coverage of test plan items (TC-01 through TC-10).
4. No open P0/P1 gaps.
5. Sensitive content scan passed.
6. Evidence index is complete and traceable.
## Decision Matrix

| Condition | Decision |
|---|---|
| All checklist pass, no P0/P1 gaps | pass |
| P0 gaps remain after reinforcement | blocked |
| P1 gaps remain, user not confirmed | blocked |
| P1 gaps remain, user confirmed | partial |
| Coverage incomplete, no P0/P1 | partial |
| Validation cannot complete | repair-needed |
| Claude unavailable, no fallback confirm | blocked |
| Sensitive scan failed | blocked |
## Partial Result

When the decision is partial:
- Document which items passed and which are incomplete.
- Record remaining gaps and their severities.
- Recommend next steps for closure.

## Blocked Result

When the decision is blocked:
- Document the blocking condition.
- Record what is needed to unblock.
- Do not proceed without user direction.

## Rerun Result

When the decision is rerun:
- The research approach or scope needs revision.
- Document what went wrong and what should change.
- Require a fresh research cycle.
