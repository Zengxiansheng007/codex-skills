# Review Checklist

Use this checklist when reviewing requirements, plans, UI automation inputs, Agent-ready artifacts, or outputs produced by this skill.

## Severity Rules

| Severity | Meaning | Typical Fix |
|---|---|---|
| P0 | Blocks development/testing, creates safety/compliance risk, invalidates evidence, or makes traceability impossible. | Stop or fix before proceeding. |
| P1 | Likely causes ambiguity, missing tests, implementation mismatch, stale baseline, or unreviewed change impact. | Fix before asset promotion or unattended execution. |
| P2 | Improves maintainability, readability, automation readiness, or evidence quality. | Fix when practical or document as known limitation. |

## Document Routing Review

- Is `documentType` explicit?
- Are target readers, included sections, excluded sections, and source baselines visible?
- Is the artifact using the correct reference priority: routing first, dev/test contract second, PRD framework third, checklist last?
- Are lightweight explanation requests handled without generating a full artifact?

## Requirement Quality Review

- Are goals, scope, non-goals, users, roles, and permissions clear?
- Are P0/P1 requirements numbered and traceable?
- Are business rules, data rules, states, exceptions, and dependencies explicit?
- Are assumptions and open questions separated from confirmed facts?
- Are source versions and dates recorded when PRD, Figma, design, code, or API may be stale?

## Acceptance and Evidence Review

- Are acceptance criteria concrete and pass/fail testable?
- Do P0/P1 requirements cover normal, abnormal, permission, boundary, idempotency, async, and rollback cases when relevant?
- Is each requirement mapped to tests and evidence?
- Is evidence strong enough to distinguish business defect, test asset problem, environment/data problem, and unclear requirement?
- Are UI/API/task/downstream/log evidence types specified where needed?

## Development/Test Plan Review

- Are phases, WBS tasks, dependencies, interfaces, and completion criteria explicit?
- Are test objectives, scope, non-scope, entry/exit criteria, pause/resume criteria, and defect handling present?
- Are release, rollback, fallback, and change gates defined?
- Does the RTM map goal -> requirement -> development task -> test item -> automation asset -> evidence -> defect/change?

## Agent-ready Review

- Does the artifact define test entry, route/menu path, account role type, allowed actions, and forbidden high-risk actions?
- Are key observable UI states, APIs, business ID extraction, downstream verification, fallback, and failure attribution included?
- Are credentials, tokens, cookies, private identifiers, and production-only commands excluded?
- Are model/LLM export boundaries and redaction rules stated when external models may be used?

## Complete Repair Review

When the user asks to fix, harden, or update a requirement, plan, Skill, or automation asset:

- Was the root cause analyzed?
- Were direct issues fixed?
- Were related references, documents, tests, configuration, reports, validation logic, and upstream/downstream impacts checked?
- Were necessary tests or validations added or rerun?
- Are remaining risks, deferred items, and required approvals documented?
- Did the work avoid unrelated business logic changes, unauthorized overwrites, destructive actions, and production writes?

## Output Review

Every review result should include:

- findings ordered by P0/P1/P2;
- affected section or artifact;
- why it matters;
- concrete fix;
- blocking status;
- validation or evidence needed before proceeding.
