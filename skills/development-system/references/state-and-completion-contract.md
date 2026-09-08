# State And Completion Contract

Read this before any state transition or final decision.

## Governed States

The runtime uses exactly the 11 states confirmed by DS-PSR-001: `running`, `waiting-approval`, `blocked-external-dependency`, `blocked-user-decision`, `repair-needed`, `requirements-review`, `risk-gate-required`, `loop-limit-reached`, `resource-limit-reached`, `completed` and `failed`.

Only Codex may call the transition gate. `validate_transition` rejects unknown states, illegal terminal-state reopening, non-Codex actors and any `completed` transition that does not pass `evaluate_completion`.

Cancellation or supersession stops orchestration outside the governed runtime state machine and records a lifecycle event against the requirement anchor. It must not introduce an undeclared runtime state. Adding a new governed state requires requirements review first.

## CompletionEvaluator

Completion requires all stories and acceptance criteria passed, valid feedback, complete evidence, independent QA pass, no P0/P1 drift, no unmapped actions, permission and risk gates passed, and a Codex completion review. Stop signals, Agent claims, timeouts, circuit states and resource limits never imply completion.

`feedbackValid` is no longer satisfied by a bare boolean. The evaluator consumes the actual `feedback` object plus `feedbackValidation` evidence and requires a hash-bound validation result: non-empty `schemaRef` and `validatorId`, a 64-character lowercase SHA-256 `feedbackHash` equal to the canonical hash of the supplied feedback object, `ok=true`, `errorCount=0`, `errors=[]` or absent, and non-empty `validatedAt`. The handoff-system remains the sole owner of the feedback packet schema; this Skill does not duplicate or replace it. An Agent completion claim, stop signal, timeout, circuit state or resource limit is never a completion signal on its own.

Trace: FR-001, FR-011, FR-013, FR-014, FR-027, AC-006, AC-009, AC-011, AC-014, REPAIR-ST-001, REPAIR-ST-002.
