# Question Pack: Requirements

Use when the user asks to clarify a PRD, business rule, permission matrix, workflow, or state machine.

Ask only one question at a time. Start with the highest blocking item.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| REQ-01 | What user outcome must be true when this requirement is complete? | Anchor the feature to observable value. | PRD goal, user story, support ticket | State one measurable user outcome. | success metric |
| REQ-02 | Who is the actor, and which roles are explicitly excluded? | Prevent permission ambiguity. | role matrix, route guards, existing docs | Name included and excluded roles. | actor boundary |
| REQ-03 | Which source is authoritative when PRD, design, code, and live behavior disagree? | Resolve freshness conflicts. | latest PRD, design timestamp, code route, live page | Prefer latest approved source; mark drift as risk. | source of truth |
| REQ-04 | What is out of scope for this version? | Prevent scope creep. | roadmap, issue labels, release notes | List explicit non-goals. | scope boundary |
| REQ-05 | What are the required states and transitions? | Make workflows testable. | state machine docs, enum usage, UI labels | Define state list and allowed transitions. | state model |
| REQ-06 | Which failure or empty states must be visible to users? | Avoid happy-path-only requirements. | UI copy, API errors, logs | List empty, error, loading, disabled states. | exception behavior |
| REQ-07 | What data must be created, changed, or left unchanged? | Define side effects and idempotency. | schema, API contract, audit logs | State data mutations and no-op cases. | data effect |
| REQ-08 | How will completion be verified? | Bind requirement to evidence. | acceptance criteria, tests, reports | Define UI/API/task/downstream evidence. | acceptance evidence |
| REQ-09 | Which decisions are hard to reverse? | Identify ADR candidates. | architecture docs, migrations, dependencies | Record alternatives and consequences. | ADR need |
| REQ-10 | What must be confirmed by a human before an agent executes? | Set risk gate. | permissions, destructive actions, prod data | List manual approval gates. | execution safety |
