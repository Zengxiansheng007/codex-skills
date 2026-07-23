---
name: task-understanding-router
description: Classify and visibly frame a new user task before execution, then route it to direct execution, one high-value clarification, an existing safety or approval gate, or grill-system. Use for new tasks and material goal changes; do not re-enter for ordinary follow-ups or active grill-system answers.
---

# Task Understanding Router

Use this as an instruction-level router, not a function or a platform hook. It has no programmatic input/output API and cannot guarantee that every message is intercepted.

## Workflow

1. Determine the conversation state. Do not re-enter when the user is answering an active grill-system question or making an ordinary follow-up. Treat an explicit replacement such as “停止当前任务，改为 X” as a new task.
2. Before ordinary routing, check the full-grill trigger in [routing contract](references/routing-contract.md). If it matches, create the minimal handoff described in [handoff contract](references/handoff-contract.md), set the conceptual state to `full-grill-active`, and let grill-system own the question sequence.
3. Otherwise select one mode, in priority order: `safety-gated`, `detailed-clarify`, `detailed-execute`, `brief`. Read [routing contract](references/routing-contract.md) for observable criteria.
4. Produce only the visible structure required by [output contract](references/output-contract.md). Do not reveal hidden chain-of-thought. Mark assumptions as assumptions. For a valid silent ordinary-execution request, do not emit router/classification commentary in any user-visible channel.
5. Ask at most one clarification question. After an answer, ask another only if the remaining unknown materially changes the deliverable, external action, irreversibility, or safety conclusion; otherwise state an assumption and proceed.

## Boundaries

- A user request to hide ordinary understanding does not bypass classification, clarification, safety, approvals, or an explicit full grill.
- Do not recreate grill-system's question pack, recursively invoke grill-system, or show a router understanding block while `full-grill-active`.
- Treat a single-file, specified, reversible text edit with no runtime behavior change as eligible for `brief`; escalate cross-file, behavior/config/API/data, unclear-scope, or hard-to-reverse work.
- Use the deterministic fixture validator only to validate assets. It does not invoke a model or prove runtime discovery.

## Resources

- Read [routing contract](references/routing-contract.md) for state, trigger, priority, and classification rules.
- Read [output contract](references/output-contract.md) before composing a visible response.
- Read [handoff contract](references/handoff-contract.md) before delegating to grill-system.
- Use `assets/fixture-suite.json` and `scripts/validate_fixture_suite.py` when changing rules or regressions. Record real-session results using `assets/forward-test-record.schema.json`.
