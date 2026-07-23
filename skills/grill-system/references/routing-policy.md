# Routing Policy

Route by the user's intent and the artifact being hardened. Pick one primary route and at most one secondary route.

| Route | Trigger | Primary output | Secondary skills |
|---|---|---|---|
| requirements | PRD, feature idea, business rule, permission, state machine, acceptance criteria | clarified requirement decisions | write-requirements-prd, domain-modeling |
| test-case-design | test cases, UI automation, regression scope, PRD/Figma freshness, stale code, coverage | test design decisions | ui-test, research, domain-modeling |
| design-review | architecture, module design, API shape, UX flow, alternatives | design decision record | codebase-design, prototype, domain-modeling |
| risk-premortem | launch, rollout, production risk, high-impact change | risk register and mitigations | research, analysis-skill |
| pre-implementation | ready for agent, coding plan, tickets, implementation gate | implementation readiness decision | tdd, to-spec, to-tickets |
| failure-retrospective | failed run, bug, regression, flaky automation, unexpected result | root-cause questions and repair path | diagnosing-bugs, code-review |
| handoff-continuation | long session, context limit, branch exploration, continue later | handoff checklist | handoff, wayfinder |

## Priority

1. Safety and data risk outrank all other routes.
2. Failure evidence outranks speculative design.
3. If the user asks for test cases, prefer test-case-design even when requirements are vague.
4. If the work cannot fit one session, use handoff-continuation or wayfinder before deeper grilling.

## First Question Pattern

The first question should identify the highest blocking uncertainty:

```text
Question: <one question>
Why it matters: <blocked decision>
Recommended answer: <opinionated recommendation>
Evidence: <facts already inspected or missing>
If unresolved: <risk>
```
