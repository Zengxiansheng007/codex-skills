# Governance and Diagnostics

Use this reference for Phase 6 style governance: versioning, change impact, output scoring, failure diagnosis, and long-term maintenance.

## Version Governance

Record baselines for:

- PRD / requirement document;
- design / Figma / prototype;
- API document and examples;
- code branch or release tag;
- test environment and feature flags;
- Agent-ready schema version;
- generated report version.

## Change Impact Analysis

When a source changes:

1. Identify impacted goals and requirements.
2. Identify impacted business rules, states, permissions, and data fields.
3. Identify impacted test points, test cases, automation assets, and evidence contracts.
4. Mark whether review, rewrite, retest, or retirement is required.
5. Invalidate stale Memory, schemas, or downstream assumptions.

## Output Quality Scoring

Score important outputs with this overlay:

| Dimension | Points |
|---|---:|
| Source baseline and fact fidelity | 15 |
| Module and boundary clarity | 12 |
| Business object/data/state clarity | 14 |
| Upstream/downstream clarity | 14 |
| Acceptance and testability | 12 |
| Agent-ready schema completeness | 12 |
| Evidence and failure attribution | 10 |
| Safety, privacy, and forbidden action handling | 7 |
| Change governance and maintainability | 4 |

Gate:

- below 80: not ready for downstream use;
- below 85: not ready for test case generation;
- below 90: not ready for UI automation execution;
- any P0: blocked until fixed or explicitly accepted.

## Failure Diagnosis Library

Classify failures as:

| Layer | Examples |
|---|---|
| requirement-ambiguity | PRD does not define expected behavior or state. |
| source-conflict | PRD, Figma, code, API, and runtime disagree. |
| module-boundary | Wrong module owner or unclear upstream/downstream responsibility. |
| permission-data | Role, data scope, seed data, or environment mismatch. |
| evidence-gap | UI success but API/task/downstream proof missing. |
| test-asset | Wrong selector, weak assertion, stale step, brittle data. |
| agent-recognition | Visual/model false positive or missed visible state. |
| safety-policy | Operation is forbidden or needs approval. |

## Grill Escalation

Use `grill-system` for:

- any P0 ambiguity;
- repeated P1 disagreement;
- module ownership disputes;
- safety and automation approval decisions;
- downgrade decisions when downstream access is unavailable;
- whether an output can be promoted to downstream automation.

## Memory Governance

Only promote rules or patterns to Memory when:

- source baseline is known;
- evidence supports the conclusion;
- P0/P1 disputes are resolved;
- applicability and limits are stated;
- stale/expiry condition is recorded.

Memory levels:

- global rule;
- project rule;
- module rule;
- page/route rule;
- field/business-object rule;
- failure attribution rule;
- forbidden automation rule.
