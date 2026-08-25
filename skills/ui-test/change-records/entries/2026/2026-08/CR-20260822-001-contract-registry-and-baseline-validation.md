# CR-20260822-001 - Contract Registry And Baseline Validation

| Field | Value |
|---|---|
| Status | applied |
| Story | PH01-ST01 |
| Requirements | FR-CASE-001, FR-CASE-015, FR-CASE-050 |
| Acceptance | AC-CASE-015, AC-CASE-017 |
| Scope | contract registry, source baseline validator, tests |

## Summary

Extend the cross-Skill contract registry with explicit planned lifecycle entries for Source Case, Case IR, Resolved IR and Compile Receipt. Add deterministic validators for active schema references, JSON parsing, Draft 2020-12 schema validity, duplicate contract identities, planned ownership and copied Skill baseline hashes.

## Context And Problem

Candidate contracts needed explicit ownership and source-baseline evidence.

## Sections Changed

Contract registry, source baseline validator and tests.

## Decision And Alternatives

Use lifecycle states in one registry rather than infer readiness from file presence.

## Impact Analysis

Invalid or unowned contracts now fail before later phases.

## Boundary

This Story does not implement the planned schemas, write D-drive assets, modify global Skills, install dependencies or execute private UI tests.

## Validation Evidence

- `python -m unittest discover -s tests -p "test_*.py"`
- sensitive scan over the candidate `ui-test` package
- source baseline hash validation
- active-contract JSON parse and Draft 2020-12 meta-schema validation, including negative fixtures

## Safety And Privacy

Validation stores hashes and contract metadata only.

## Risks And Follow-up

Planned contracts must not be treated as executable until activated.
