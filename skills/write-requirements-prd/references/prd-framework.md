# PRD Framework Reference

Use this reference when the task requires detailed PRD structure, review criteria, or Agent-ready testability.

## Required PRD Sections

1. Document metadata
   - name, ID, version, status, owner, reviewers, date, related prototype/design/spec/test plan.
2. Revision record
   - version, date, author, change summary, impact, re-review flag.
3. Background and problem definition
   - problem, evidence, affected users, impact, why now.
4. Goals and success metrics
   - business goal, user goal, product goal, baseline, target, metric owner.
5. Scope and boundaries
   - in scope, out of scope, later versions, dependencies, non-goals.
6. Users, roles, and permissions
   - role visibility, operations, data scope, permission failure behavior.
7. Glossary and business objects
   - terms, objects, fields, type, required flag, validation rules.
8. Information architecture, pages, and flows
   - entry, exit, page goal, controls, states, empty/loading/error/permission states.
9. Functional requirements
   - ID, name, source, story, preconditions, main flow, branch flow, exception flow, business rules, design/prototype, dependencies, acceptance criteria, priority, impact.
10. Business rules and state machines
   - rule ID, condition, result, examples, affected requirements; state, allowed actions, next state.
11. Non-functional requirements
   - performance, reliability, security, compatibility, observability, privacy, compliance.
12. Acceptance criteria
   - Given/When/Then; normal, abnormal, permission, boundary, idempotency, async, rollback.
13. RTM traceability matrix
   - goal -> requirement -> rule/state -> design -> development task -> test case -> automation asset -> evidence -> defect/change.
14. Dependencies, risks, and fallback
   - dependency owner, deadline, risk level, fallback strategy.
15. Change management
   - CR ID, reason, content, impact, decision owner, re-review, affected requirement/test/development/automation assets.

## Functional Requirement Template

| Field | Required | Notes |
|---|---|---|
| Requirement ID | Yes | Use stable IDs such as `FR-TASK-001`. |
| Requirement name | Yes | Use verb-object naming. |
| Requirement source | Yes | User input, business rule, compliance, data analysis, defect. |
| Source baseline | Yes | PRD/design/Figma/API/code/environment version and date. |
| User story | Yes | As a role, I want, so that. |
| Preconditions | Yes | Role, state, data, permission, environment. |
| Main flow | Yes | Normal path. |
| Branch flow | Yes | Conditional path. |
| Exception flow | Yes | Failure, timeout, no permission, empty data. |
| Business rules | Yes | Conditions, thresholds, state transitions. |
| UI/API/data dependencies | Recommended | Page, API, downstream, business ID. |
| Acceptance criteria | Yes | Concrete pass/fail standards. |
| Priority | Yes | P0/P1/P2/P3. |
| Impact | Yes | Page, system, data, user, test asset, development task. |

## DoR Checklist

A P0/P1 requirement is ready only when:

- goal, scope, non-goals, and user role are clear;
- source baseline and version/date are recorded;
- page/entry or API entry is identified;
- main, branch, and exception flows are described;
- business rules and state transitions are explicit;
- acceptance criteria are testable;
- dependencies and risks have owners;
- test data and evidence strategy are known;
- forbidden high-risk actions are marked;
- missing information is listed as open questions.

## DoD Checklist

A requirement is done only when:

- all acceptance criteria pass or have approved exceptions;
- UI/API/task/downstream evidence is captured as required;
- defects and changes are linked to the requirement;
- impacted development tasks, test cases, and automation assets are updated;
- NFR/security/privacy requirements are verified or waived;
- reports are reviewed and sensitive data is redacted.

## RTM Template

| Goal | Requirement ID | Rule/State | Design/Prototype | Development Task | Test Case | Automation Asset | Evidence | Defect/Change |
|---|---|---|---|---|---|---|---|---|
| Improve task state accuracy | FR-TASK-001 | BR-TASK-003 | Task detail page | DEV-TASK-002 | TC-TASK-001 | Playwright/Midscene step | Screenshot + API JSON | BUG/CR |

## Agent-ready Fields

Add these when the PRD will be used for automated UI/API testing:

| Field | Purpose |
|---|---|
| Test entry | URL, route, menu path, page entry, prerequisite state. |
| Role/account type | Role needed for test; never include real password or token. |
| Allowed actions | Read-only or approved actions. |
| Forbidden actions | Delete, publish, deploy, approve, pay, production writes. |
| Key observable UI states | Page title, selected menu, buttons, table, empty state, toast. |
| Key APIs | Request/response to capture or assert. |
| Business ID extraction | JSONPath or page text pattern for taskId, orderId, projectId. |
| Downstream verification | Detail page, task status API, log platform, downstream query. |
| Evidence type | UI screenshot, API JSON, contract result, task status, downstream data. |
| Failure attribution | How to decide UI issue vs API issue vs business rule issue. |
| Fallback strategy | Deterministic check, Playwright fallback, manual confirmation, or blocked gate. |
| Execution quality review | How to assess Agent false positive, slow step, selector drift, missing assertion, or data problem. |
| Memory promotion | Conditions for promoting a pattern to reusable Agent Memory or regression asset. |
| Test data | Required seed data, cleanup rule, read-only limitation. |

## Permission Matrix Guidance

For role/menu/button/data-scope documents:

- normalize role names and page names;
- convert visual marks into structured expected values: visible, hidden, disabled, denied, full-data, filtered-data;
- distinguish menu permission, button permission, data permission, form option filtering, and backend enforcement;
- create tests by role x page x action x expected result;
- include both UI visibility evidence and API/backend denial evidence for sensitive operations.

## State Machine Guidance

For state machine requirements:

- distinguish persisted status, display status, status source, and derived status;
- define allowed transitions and forbidden transitions;
- specify who can trigger each transition;
- define required parameters and validation errors;
- cover terminal states, soft delete, audit, concurrency, idempotency, retry, and recovery;
- map each transition to at least one acceptance criterion and test case.

## Source Freshness Guidance

When PRD, Figma, design, code, API, or HTML prototype can be stale:

- record source name, version/date, owner, and confidence;
- prefer current runtime behavior only for observation, not as a replacement for business rules;
- if code contains offline modules or dead routes, mark them as `candidate-stale` until confirmed by route, feature flag, product owner, or runtime access;
- create open questions for conflicts instead of silently choosing one source.

## Scoring Rubric

Score PRDs out of 100:

| Dimension | Points |
|---|---:|
| Problem and goals | 12 |
| Scope and boundaries | 10 |
| Users, roles, and permissions | 12 |
| Functional requirements and rules | 18 |
| State/data/API clarity | 10 |
| Acceptance and test coverage | 14 |
| RTM and evidence chain | 10 |
| Agent-ready automation fields | 8 |
| Change governance and readability | 6 |

Suggested gate:

- below 80: not ready for development;
- below 85: not ready for automation asset creation;
- below 90: not ready for unattended regression in high-risk systems.
