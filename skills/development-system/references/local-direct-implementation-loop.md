# Local Direct Implementation Loop

Use this reference when Codex implements directly without Claude Code, Midscene, or another execution Agent.

## Loop

1. Frame the task and save or restate the requirement anchor.
2. Confirm whether evidence or grill gates are needed.
3. Inspect the existing source, tests, validation scripts, and relevant generated artifacts.
4. Produce a concise repair or development plan.
5. Patch the smallest owned surface that closes the root cause and related validation/documentation gaps.
6. Run validation proportional to blast radius.
7. Compare changed files and validation evidence back to the requirement anchor.
8. Decide exactly one next state.

## Evidence To Preserve

- source baseline before edits;
- files changed;
- validation commands and results;
- skipped validation with reasons;
- known risks and follow-up actions;
- final gap-to-requirement review.

## Completion Rules

Completion is allowed only when:

- changed files map to the approved scope;
- no P0/P1 drift remains open;
- validation evidence supports the acceptance criteria;
- skipped validation is explained and does not hide a release-blocking risk;
- the final answer includes the next-state decision.

## When To Escalate

Route to A2A handoff or a user approval gate when the task needs an external Agent, live adapter, installer, global write, production data, irreversible action, or high-risk permission change.

