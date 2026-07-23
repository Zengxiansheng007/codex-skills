# Development and Test Plan Contract

Use this reference when producing or reviewing a development plan, test plan, or combined development/test plan.

## Required Metadata

| Field | Required | Notes |
|---|---|---|
| Document name | Yes | Use a stable Chinese or task-specific title. |
| Document type | Yes | Development plan, test plan, or combined development/test plan. |
| Version/status | Yes | Draft, review, approved, implemented, archived. |
| Owner/reviewers | Recommended | Product, development, testing, security, operations. |
| Source baseline | Yes | PRD version, design/Figma version, code branch, environment URL, API doc version, date. |
| Change summary | Yes | What changed and whether re-review is required. |
| Security boundary | Yes | Credentials, production actions, external LLM export, sensitive data handling. |

## Combined Plan Structure

For a combined development/test plan, use this structure:

1. Background and problem.
2. Goals and success metrics.
3. Scope, non-goals, and assumptions.
4. Source baseline and dependencies.
5. Architecture or workflow overview.
6. Development phases and tasks.
7. Test strategy and test phases.
8. Evidence and reporting requirements.
9. Entry, exit, pause, and resume criteria.
10. Risks, fallback, rollback, and release gates.
11. RTM traceability matrix.
12. Change governance and maintenance.

## Development Plan Requirements

Each development phase should define:

| Field | Purpose |
|---|---|
| Phase ID | Stable ID such as `PH-0`, `PH-1`. |
| Goal | What capability is completed in this phase. |
| Inputs | PRD, design, API doc, data, environment, previous phase output. |
| Tasks | Implementable WBS items with owners or responsible roles. |
| Interfaces | API, data model, configuration, CLI, report schema, browser/MCP/LLM boundary. |
| Dependencies | Internal/external systems, permissions, test data, model gateway, browser, package versions. |
| Completion criteria | Observable state, command result, generated artifact, passing test, approval gate. |
| Rollback/fallback | How to disable or revert the phase if it fails. |

## Test Plan Requirements

Each test phase should define:

| Field | Purpose |
|---|---|
| Test objective | What risk or requirement is verified. |
| Test scope | Modules, roles, browsers, environments, APIs, downstream systems. |
| Non-scope | Explicitly excluded modules or risky actions. |
| Test data | Seed data, account type, cleanup, read-only constraints. |
| Entry criteria | Required docs, environment, data, accounts, feature flags, build status. |
| Exit criteria | Pass rate, evidence completeness, unresolved defect threshold. |
| Pause criteria | Environment outage, missing data, blocking defect, unsafe action, unclear requirement. |
| Resume criteria | Fix verified, data restored, environment stable, owner approval. |
| Evidence | Screenshot, API JSON, task state, downstream data, logs, trace, report. |
| Defect handling | Severity, owner, reproduction, evidence attachment, retest rule. |

## Evidence Quality Rules

Evidence is acceptable only when it is:

- linked to a requirement or test item;
- time-stamped;
- generated from the declared environment;
- redacted for secrets and personal data;
- sufficient to distinguish business defect, test asset problem, environment/data problem, and unclear requirement;
- accessible through a stable report path or embedded evidence index.

For UI automation or Agent execution, capture:

- before/after UI screenshot for UI-changing steps;
- API request/response for key business operations;
- contract assertion result for key fields;
- business ID extraction result;
- task polling timeline for async work;
- downstream verification or an explicit downgrade note when downstream access is unavailable;
- Agent execution quality report when Midscene/Playwright/fallback is involved.

## Quality Gates

| Gate | Applies to | Must pass |
|---|---|---|
| Requirement gate | Before development/test design | Scope, roles, rules, acceptance, evidence, open questions. |
| Design gate | Before implementation | Architecture, interface, dependency, security, rollback. |
| Test readiness gate | Before execution | Environment, account type, data, entry criteria, forbidden actions. |
| Evidence gate | Before accepting test result | Evidence linked, redacted, complete, and attributable. |
| Regression gate | Before stable automation | Repeated pass, deterministic checks, low false positive rate, maintained traceability. |
| Change gate | After PRD/design/code change | Impacted requirements, tests, assets, evidence, and owners identified. |
| Complete repair gate | After defects, review findings, failed validation, or plan gaps | Root cause analyzed; direct fix completed; related documents, tests, configuration, reports, validation logic, and upstream/downstream impacts checked; remaining risks documented. |

## RTM for Development and Testing

Use this extended matrix for combined plans:

| Goal | Requirement ID | Business Rule/State | Development Task | Test Item | Automation Asset | Evidence | Defect/Change |
|---|---|---|---|---|---|---|---|
| Improve pipeline navigation reliability | FR-UI-001 | BR-MENU-001 | DEV-NAV-001 | TC-NAV-001 | explore-steps + Playwright spec | Screenshot + route + selected menu | BUG/CR |

## Change Impact Rules

When PRD, Figma, design, API, code, route, permission, or environment changes:

1. Record the change baseline and date.
2. Identify impacted requirements and business rules.
3. Identify impacted test cases and automation assets.
4. Mark whether retest, rewrite, or review is required.
5. Do not promote automation memory or stable regression scripts until the new baseline passes evidence gates.

## Safety and Data Rules

- Never include real passwords, tokens, cookies, API keys, or production-only account details.
- Use role/account type instead of actual credentials.
- Mark delete, publish, deploy, payment, approval, production write, and irreversible actions as forbidden unless explicitly approved.
- For external LLM or model gateway use, state what content may be sent and what must be redacted.
- If the plan requires GitHub, package installation, browser control, or external network calls, list the approval boundary.

## Complete Repair Checklist

Use this checklist whenever the user asks to fix, adjust, review, or harden a requirement, plan, Skill, automation workflow, or test asset:

- Did the work analyze the root cause and impact scope?
- Did it fix only the symptom, or also the underlying cause?
- Were related documents, tests, configuration, reports, validation logic, and upstream/downstream workflows checked?
- Were necessary tests or validation steps added or rerun?
- Are unresolved items, risks, and required user confirmations explicitly documented?
- Did the work avoid unrelated business logic changes, unauthorized overwrites, destructive actions, and production writes?

## Scoring Add-on

For development/test plans, add these points to the PRD scoring rubric or use them as a review overlay:

| Dimension | Points |
|---|---:|
| Source baseline and change impact | 12 |
| Development task clarity | 14 |
| Interface/dependency clarity | 10 |
| Test strategy and coverage | 16 |
| Evidence and reporting | 14 |
| Entry/exit/pause/resume criteria | 10 |
| Safety and data boundary | 10 |
| Traceability and maintenance | 14 |

Suggested gate:

- below 80: not ready for execution;
- below 85: not ready for automation asset creation;
- below 90: not ready for unattended or cross-team regression.
