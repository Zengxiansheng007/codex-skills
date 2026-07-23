# Question Pack: Failure Retrospective

Use after a test, implementation, deployment, automation run, or agent workflow fails.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| FR-01 | What is the tightest command or action that reproduces the failure? | Build a feedback loop. | logs, report, test command | Name one red-capable loop. | repro loop |
| FR-02 | What exactly failed: business behavior, test asset, environment, data, or requirement understanding? | Classify root area. | screenshots, API logs, assertions | Pick one primary category and evidence. | failure category |
| FR-03 | What evidence proves the symptom is the user's reported failure? | Avoid fixing wrong bug. | screenshots, traces, console, network | Cite exact symptom evidence. | symptom proof |
| FR-04 | What was the first false assumption? | Learn from the failure. | prior plan, decisions, memory | State assumption and correction. | assumption update |
| FR-05 | What would have caught this earlier? | Prevent recurrence. | tests, review gate, monitoring | Add preflight, test, or evidence check. | prevention |
| FR-06 | What should be repaired upstream? | Avoid local-only fixes. | steps, assertions, policy, fallback | Identify asset to change. | repair target |
| FR-07 | Should the experience become memory, ADR, or a regression test? | Promote learning. | recurrence risk, business impact | Choose promotion type. | learning path |
| FR-08 | What is safe to rerun now? | Gate retry. | side effects, data cleanup | Define rerun scope and safeguards. | rerun gate |
