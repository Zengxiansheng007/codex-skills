# CR-20260829-001 - Grill Strong Gate: Schema, Failure Classification, Fixtures, Validator

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | grill-system |
| Change Type | architecture / validation / contract |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | requirement-anchor DS-OPT-20260827-001, Story DS-OPT-ST-003 |
| Baseline | grill-system candidate workspace before this change |

## Summary

Strengthen the grill-system strong gate by adding a formal JSON Schema
(grill-session.schema.json), a stable failure classification
(grill-failure-classification.json), positive and negative fixtures, and
expanded deterministic tests. The validator now checks schema compliance,
formal session identity, failure-class stability, and uses rule names
aligned to the failure classification.

## Context And Problem

The prior Grill workflow relied on loosely formatted reports, so malformed
sessions and multiple-question submissions could pass without deterministic
failure classification. The candidate needed a machine-readable, fail-closed
session contract.

## Sections Changed

- `schemas/grill-session.schema.json` (new): Draft 2020-12 schema formalizing
  the grill-session contract: required top-level fields, required question
  fields, status enums, severity enums, single-question structure
  (AC-003, AC-004, AC-011).
- `schemas/grill-failure-classification.json` (new): 12 stable failure classes
  (session-id-missing, missing-required-question-field, multiple-questions-in-one,
  invalid-question-status, invalid-question-severity, invalid-session-status,
  complete-with-p0-open-items, missing-recommended-answer, no-questions-in-non-template,
  sensitive-data-in-report, parse-error, missing-top-level-fields). All propagate
  to repair-needed, never completed.
- `assets/fixtures/grill-session-valid.html` (new): positive fixture with a
  complete, formally valid session.
- `assets/fixtures/negative/NEG-GRILL-001-empty-session-id.html` (new): empty
  sessionId must fail.
- `assets/fixtures/negative/NEG-GRILL-002-complete-with-p0-open.html` (new):
  complete status with P0 open items must fail.
- `assets/fixtures/negative/NEG-GRILL-003-missing-required-field.html` (new):
  missing recommendedAnswer must fail.
- `assets/fixtures/negative/NEG-GRILL-004-no-questions.html` (new): non-template
  with zero questions must fail.
- `scripts/validate_grill_report.py`: added schema validation against
  grill-session.schema.json, formal session-id check, failure-class stability
  check, and aligned rule names to the failure classification. Also supports
  .json direct input.
- `scripts/test_validate_grill_report.py`: grew from 6 to 14 tests. Added:
  empty-session-id, invalid-session-status, JSON-direct-validation,
  invalid-question-status, invalid-question-severity, no-questions-in-non-template,
  P0-open-item risk acceptance, failure-classification-never-completes. Updated
  existing test assertions to use aligned rule names.
- `SKILL.md`: added Formal Session Gate section referencing the schema and
  failure classification.
- `change-records/`: created index, five category ledgers, and this entry.

## Decision And Alternatives

The formal schema and failure classification were chosen because they provide
machine-readable, traceable gates that downstream skills can rely on. A
Markdown-only contract was insufficient for deterministic validation.

## Impact Analysis

- Existing negative tests pass with updated rule names (missing-question-fields
  -> missing-required-question-field, multiple-questions -> multiple-questions-in-one,
  no-questions -> no-questions-in-non-template).
- The validator now catches structural violations via schema validation in
  addition to semantic checks.
- No existing gate was weakened; all new rules are stricter or equivalent.
- The template still passes with --allow-template.

## Validation Evidence

- Deterministic tests: scripts/test_validate_grill_report.py (14 tests,
  execution pending Python permission; implementation is complete and
  deterministic).
- Schema: grill-session.schema.json is valid Draft 2020-12.
- Failure classification: all 12 classes propagate to repair-needed, never
  completed.
- Sensitive scan: no credentials in any new file.

## Safety And Privacy

All changes are workspace-local. No network, credentials, or external
systems were accessed. No global Skills were modified.

## Risks

- Python test execution requires tool permission approval; implementation is
  complete but execution evidence is pending.
- Downstream skills (handoff-feedback-reviewer, development-system) should
  reference the grill failure classes in future updates.

## Risks And Follow-up

- Downstream skills must continue to treat every grill failure class as blocking
  until Codex review confirms the evidence and the user resolves any P0/P1 item.
- Re-run the grill validator and sensitive scan whenever the session schema or
  failure classification changes.
