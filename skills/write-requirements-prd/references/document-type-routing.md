# Document Type Routing

Use this reference before drafting or reviewing an artifact that mixes requirements, development planning, testing, execution evidence, or review content.

## Routing Rule

Always declare these fields near the beginning of the output:

| Field | Meaning |
|---|---|
| `documentType` | PRD, permission rules, state machine, UI automation requirement, development plan, test plan, combined development/test plan, or review report. |
| `targetReaders` | Product, development, testing, operations, security, management, or agent executor. |
| `sourceBaseline` | Source documents, versions, URLs, prototype frames, code branch, test environment, and date used. |
| `includedSections` | Sections intentionally included in this artifact. |
| `excludedSections` | Sections intentionally excluded or delegated to another artifact. |
| `openQuestions` | Facts that cannot be inferred and must be confirmed. |

If the source is incomplete, generate a partial artifact with assumptions and open questions instead of inventing business facts.

## Reference Priority

Apply references in this order:

1. `document-type-routing.md` decides artifact type, target readers, included sections, excluded sections, and whether a lightweight answer is enough.
2. `dev-test-plan-contract.md` adds development/test phases, gates, evidence, rollback, defect handling, and change governance when the artifact is a development plan, test plan, or combined plan.
3. `prd-framework.md` fills common PRD structure, DoR/DoD, RTM, acceptance criteria, permission/state guidance, and Agent-ready fields.
4. `review-checklist.md` is applied last to score readiness, classify P0/P1/P2 findings, and check complete repair closure.

If references conflict, preserve confirmed company business rules first, then apply the priority order above. Record the conflict as an open question when the correct interpretation cannot be proven.

## Lightweight Answer Boundary

lightweight explanation requests should be answered directly without over-generating a full PRD/plan artifact. If the user asks only for a brief explanation, concept comparison, definition, or wording suggestion, answer directly and do not generate a full PRD/plan artifact.

Use the full artifact workflow only when the user asks to draft, generate, review, convert, harden, update, or package a document, plan, traceable requirement set, or Agent-ready input.

## Document Types

### Business PRD / Feature Requirement

Use when the user asks for a product requirement, feature requirement, permission rule, state machine, or business-rule document.

Must include:

- background, goal, scope, non-goals;
- users, roles, permissions;
- glossary and business objects;
- pages, flows, states, business rules;
- functional requirements and acceptance criteria;
- NFR/security/privacy if relevant;
- RTM and change governance.

Exclude:

- detailed implementation code;
- low-level task assignment unless requested;
- detailed test cases beyond acceptance criteria and testability mapping.

### Permission Matrix / Data Access Rule

Use when source documents describe roles, menus, buttons, data scopes, filters, or backend denial behavior.

Must distinguish:

- menu visibility;
- button visibility or disabled state;
- form option filtering;
- data row/field scope;
- backend authorization enforcement;
- no-permission response and audit behavior.

### State Machine / Workflow Rule

Use when source documents describe task states, approval states, pipeline states, async jobs, or transition rules.

Must include:

- persisted state vs display state;
- status source and derived status;
- allowed transitions and forbidden transitions;
- trigger role, preconditions, side effects, idempotency, retry, recovery;
- terminal states and abnormal paths.

### UI Automation / Agent-ready Testing Requirement

Use when the output will feed Codex, Midscene, Playwright, Solution D, or another testing Agent.

Must include:

- test entry and route/menu path;
- role/account type, not real credentials;
- allowed read-only actions and forbidden high-risk actions;
- observable UI states;
- key API and business ID extraction;
- downstream verification entry;
- evidence type and failure attribution priority;
- fallback strategy and rerun conditions.

### Development Plan

Use when the user asks how to implement a requirement or skill.

Must include:

- implementation scope and non-goals;
- architecture and module boundaries;
- task breakdown and dependencies;
- data/API/interface changes;
- migration, compatibility, observability, security;
- development risks, rollback and release gates;
- engineering verification and acceptance criteria.

Exclude:

- detailed business PRD restatement unless needed for traceability;
- full test case inventory unless requested.

### Test Plan

Use when the user asks how to test, validate, or accept a system.

Must include:

- test objectives and risks;
- scope, non-scope, environment, data and accounts;
- test levels/types: functional, API, UI, integration, regression, security, performance when relevant;
- entry/exit criteria;
- pause/resume criteria;
- evidence requirements;
- defect severity and triage;
- regression and reporting strategy.

Exclude:

- implementation WBS unless needed to align test phases;
- exhaustive detailed test cases unless requested.

### Combined Development and Test Plan

Use when the user asks for a total plan, phased implementation plan, or development/testing plan for a capability.

Must keep three layers distinct:

1. Requirement and acceptance layer.
2. Development implementation layer.
3. Testing and evidence layer.

The combined plan should include a traceability matrix that maps:

`Goal -> Requirement -> Development Task -> Test Item -> Automation Asset -> Evidence -> Defect/Change`.

Do not collapse all layers into one task list.

### Review / Gap Analysis

Use when the user asks whether a document, plan, or skill is reasonable.

Lead with findings ordered by severity:

- P0: blocks development/testing, creates safety/compliance risk, or invalidates evidence.
- P1: likely causes ambiguity, missing tests, mismatch, or unreviewed changes.
- P2: maintainability, readability, automation readiness, or completeness improvements.

Each finding must include:

- affected section or artifact;
- why it matters;
- concrete fix;
- whether it blocks the next phase.

## Routing Anti-patterns

Avoid these patterns:

- using a PRD template for every artifact without declaring document type;
- generating a full HTML/PRD artifact when the user only asked for a lightweight explanation;
- mixing business requirement, implementation details, and test cases without traceability;
- turning acceptance criteria into vague statements such as "works normally";
- including real passwords, keys, cookies, account secrets, or production-only commands;
- treating stale PRD/Figma/code as current without a source baseline date;
- ignoring code modules that are present but already offline or feature-flagged off.

## Minimum Routing Checklist

Before finalizing, confirm:

- the artifact type is explicit;
- source baselines are recorded;
- out-of-scope sections are named;
- open questions are visible;
- acceptance and evidence are linked;
- sensitive information is excluded.
