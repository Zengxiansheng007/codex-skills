---
name: write-requirements-prd
description: Draft, improve, review, or convert notes, business rules, permission matrices, state machines, design docs, prototypes, UI automation requirements, development plans, and test plans into structured, testable PRD-style requirements documents with DoR/DoD, RTM, acceptance criteria, evidence, and change governance. Use when the user asks to 编写需求文档, 生成PRD, 评审需求文档, 补强需求规范, 转换权限矩阵/状态机, 生成开发测试计划, or create Agent-ready traceable requirements.
---

# Write Requirements PRD

## Operating Rules

Produce requirements that are understandable, developable, testable, traceable, and maintainable.

Default to HTML output when creating artifacts, unless the user explicitly requests Markdown, Word, JSON, or another format. For this workspace, write HTML deliverables to `C:\Users\lenovo\Desktop\UI自动化` when no other path is specified.

Do not invent business facts. Mark unknowns, assumptions, and required confirmations explicitly.

When producing or reviewing a high-impact PRD, development plan, test plan, Agent-ready requirement, or skill-change plan, consume available `research-decision-gate` evidence before finalizing deterministic recommendations. If P0/P1 coverage is `insufficient` or `blocked`, route back to `research`, mark the artifact `partial/blocked`, or ask for explicit risk acceptance.

Default repair policy: prefer complete root-cause repair over minimal patching when the user asks to fix, adjust, review, or harden requirements, plans, Skills, or automation workflows. A task is not complete until direct fixes, related references, validation, reports, and known downstream impacts are handled or explicitly documented as out of scope. If the user explicitly asks for a minimal change, follow that constraint.

Do not include secrets, passwords, tokens, cookies, private keys, real credentials, or production-only account data in generated PRDs, reports, examples, Memory, or test data sections.
For account-related content, do not include real credentials; use role/account type, placeholder names, or redacted examples instead.

If the user only asks for a brief explanation, comparison, or definition, answer directly and do not generate a full PRD/plan artifact. Enter the full artifact workflow only when the user asks to draft, generate, review, convert, harden, or update a document, plan, or traceable requirement package.

Treat business documents as the source of truth. If a generated framework conflicts with company rules, preserve the company rule and add the missing governance or Agent-ready fields around it.

When the input mixes requirement, development, and testing content, first classify the artifact type. Do not merge all details into one undifferentiated document.

## Workflow

1. Identify the document type:
   - business PRD or feature requirement;
   - permission matrix or data access rule;
   - state machine or workflow rule;
   - UI automation / Agent-ready testing requirement;
   - development plan;
   - test plan;
   - development and test plan PRD;
   - review or gap analysis.

2. Route the document:
   - declare `documentType`, target reader, applicable sections, intentionally excluded sections, and referenced standards;
   - apply reference priority in this order: `document-type-routing.md` decides artifact type and scope, `capability-boundary-map.md` decides skill ownership and handoff, `agent-ready-output-schema.md` defines downstream contract when needed, `dev-test-plan-contract.md` adds development/test gates when applicable, `prd-framework.md` fills general PRD/RTM/DoR/DoD fields, `governance-diagnostics.md` adds version/change/diagnostic rules, and `review-checklist.md` checks severity and readiness;
   - use `references/document-type-routing.md` when the user asks for a development plan, test plan, combined plan, or document review;
   - use `references/dev-test-plan-contract.md` when the output must include development tasks, test strategy, quality gates, execution evidence, or release/change governance.

3. Extract source facts:
   - goals, users, roles, permissions, scope, non-goals;
   - pages, menus, buttons, forms, states, business objects;
   - business rules, data filters, state transitions, exceptions;
   - APIs, downstream systems, business IDs, test data, evidence needs;
   - baselines, source versions, deadlines, owners, and change impact;
   - open questions and assumptions.

   If the artifact depends on external references, reference skills, products, standards, or literature, inspect the latest `research-decision-gate` first. If it is missing for a high-impact decision, call or request `research` before converting the decision into a requirement, plan, or acceptance criterion.

4. Structure the artifact:
   - document metadata and revision record;
   - background and problem definition;
   - goals and success metrics;
   - scope, boundaries, non-goals;
   - users, roles, permissions;
   - glossary and business objects;
   - pages, flows, state machines, and interactions;
   - functional requirements with IDs;
   - non-functional requirements;
   - acceptance criteria;
   - RTM traceability matrix;
   - risks, dependencies, fallback, launch/rollback if relevant;
   - change management.

5. Add testability:
   - number requirements as `FR-*`, `BR-*`, `NFR-*`, `TR-*`, `AC-*`;
   - include normal, abnormal, permission, boundary, idempotency, async, and rollback criteria for P0/P1 requirements;
   - map each requirement to tests and evidence;
   - specify UI/API/task/downstream/log evidence where needed.

6. Add Agent-ready fields when the PRD will feed Codex, Midscene, Playwright, Solution D, or a testing Agent:
   - test entry path and URL/route;
   - role/account type, not actual credentials;
   - allowed read-only actions and forbidden high-risk actions;
   - key observable UI states;
   - key APIs and JSONPath/business ID extraction;
   - downstream verification entry;
   - expected evidence type;
   - failure attribution priority;
   - fallback and deterministic verification strategy;
   - test data and cleanup strategy;
   - execution quality review and memory promotion criteria when relevant.

7. Validate before finalizing:
   - DoR satisfied for requirements entering development/testing;
   - DoD clear for delivery completion;
   - RTM links goals, requirements, development tasks, tests, automation assets, evidence, defects, and changes;
   - document type boundaries are respected;
   - no sensitive information included;
   - assumptions and open questions are visible.
   - P0/P1 evidence gaps from `research-decision-gate` are closed, routed to `research`, or explicitly marked as accepted risk.

## Reference Loading

Read `references/prd-framework.md` when:

- creating a new PRD from sparse notes;
- reviewing whether a PRD is complete;
- converting permission matrices, state machines, or business rules into testable requirements;
- adding DoR/DoD, RTM, Agent-ready testing fields, or scoring.

Read `references/document-type-routing.md` when:

- the user asks for a development plan, test plan, combined development and test plan, document review, or gap analysis;
- the input contains mixed requirement, implementation, and testing content;
- you need to decide which sections belong in the current artifact and which should remain out of scope.

Read `references/dev-test-plan-contract.md` when:

- producing or reviewing a development plan, test plan, or combined development/test plan;
- adding phases, WBS, dependencies, quality gates, test strategy, evidence requirements, pause/resume criteria, defect handling, release/rollback, or change governance.

Read `references/agent-ready-output-schema.md` when:

- the output will feed another Agent or Skill;
- the artifact needs module boundary, business objects, upstream/downstream, evidence contract, safety, handoff targets, or grill questions;
- checking whether an output is machine-consumable by downstream skills.

Read `references/capability-boundary-map.md` when:

- deciding whether a capability belongs in this skill or should be handed off to `development-plan`, `test-plan`, `testcase-generator`, or `ui-test`;
- reviewing whether this skill is expanding beyond upstream requirement truth and handoff contracts.

Read `references/governance-diagnostics.md` when:

- handling version baselines, change impact, output scoring, failure diagnosis, grill escalation, or Memory governance;
- deciding whether an artifact can be promoted to downstream use or must be re-reviewed.

Read the latest `research` report and its `research-decision-gate` JSON when:

- writing requirements, development plans, test plans, or skill-change plans from researched references;
- grill-system identified P0/P1 findings that affect the recommendation;
- the artifact would otherwise depend on assumptions about external products, reference skills, standards, or literature.

Read `references/review-checklist.md` when:

- reviewing requirements, plans, UI automation inputs, or Agent-ready outputs;
- deciding P0/P1/P2 severity;
- checking complete repair, source baseline, traceability, evidence quality, or readiness gates.

If the user gives a company document, preserve its terminology and business rules. Use references only to add missing structure, not to overwrite domain language.

## Review Output Rules

When reviewing a PRD or plan, lead with findings ordered by severity:

- P0: blocks development/testing, creates safety/compliance risk, or prevents traceability;
- P1: likely causes ambiguity, missing tests, implementation mismatch, or unreviewed change impact;
- P2: improves maintainability, readability, automation readiness, or evidence quality.

For each finding, include the affected section, why it matters, and the concrete fix.

## Artifact Naming

For generated HTML artifacts, use concise Chinese or task-specific names such as:

- `需求文档-v1.html`
- `权限规则-agent-ready-prd.html`
- `状态机需求评审.html`
- `UI自动化开发测试计划PRD.html`
- `开发测试计划评审报告.html`

Do not overwrite existing artifacts unless the user explicitly requests it.

## Validation

When this skill is changed, run:

```powershell
python scripts/forward_test_write_prd_skill.py
python scripts/validate_agent_ready_schema.py
```

Also validate:

- frontmatter has only `name` and `description`;
- every referenced file in `references/` exists;
- `agents/openai.yaml` reflects PRD, development plan, test plan, RTM, evidence, and change governance capabilities;
- outputs contain no secrets, tokens, cookies, private keys, real credentials, or production-only account details;
- high-impact artifacts do not ignore `research-decision-gate` P0/P1 gaps;
- forward-test cases cover sparse PRD, permission matrix, state machine, combined development/test plan, lightweight explanation, and sensitive input.
- Agent-ready schema validation covers module understanding, business objects, upstream/downstream, evidence, safety, handoff targets, and governance references.

## Escalation

Ask before:

- writing outside the requested output directory;
- changing global skill directories;
- using private repositories, private URLs, or internal systems;
- sending documents, screenshots, credentials, or business content to external LLMs;
- including production actions, destructive operations, real credentials, tokens, cookies, or private identifiers in any artifact.
