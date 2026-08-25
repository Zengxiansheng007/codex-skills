# CR-20260822-010 - Full Suite Validation And Pytest Entry

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / validation / dependency |
| Scope | scripts-and-validation |
| Source | full candidate suite execution |
| Baseline | CR-20260822-009 validated candidate |
| Author | Codex |
| Related Records | CR-20260822-008, CR-20260822-009 |

## Summary

Stabilized the candidate Skill's direct pytest entry, declared the YAML parser dependency, added YAML project-config coverage, and completed full validation.

## Context And Problem

The candidate tests imported `scripts.ui_test_core` but had no pytest root configuration, so direct `pytest` invocation failed during collection unless the caller supplied an implicit import-path adjustment. The runtime also required PyYAML for the governed `ui-test.project.yaml` loader, while the development lock omitted it.

## Sections Changed

| File | Change Summary |
|---|---|
| `pytest.ini` | Declare the candidate root on the pytest import path and collect both `tests/` and governed script tests. |
| `tests/test_project_paths.py` | Add a real YAML project-config loading regression. |
| `requirements-dev.lock` | Add `PyYAML>=6.0,<7`. |

## Validation Evidence

| Check | Result |
|---|---|
| Direct `pytest -q` | passed, 99 tests |
| `python -m pytest -q` | passed, 99 tests |
| Independent test-file execution | passed, 11 files |
| `pytest --collect-only -q` | passed, 99 tests collected |
| Schema JSON parsing | passed, 19 schemas |
| Python `compileall` | passed |
| Sensitive asset scan | clear, 0 findings |

## Historical Count Clarification

Earlier records cite 99, 101 and 102 tests for earlier candidate states or combined validation scopes. The current candidate package contains 99 collected tests after the latest changes; this record is the current validation fact for this package.

## Safety And Privacy

No credentials, private URLs, Cookies, Tokens or browser state were added. PyYAML was installed into the existing Codex Python runtime only; no global UI-Test Skill installation was performed.

## Remaining Risks

Private Tianjin live UI execution and global Skill installation remain separate gated activities.

## Decision And Alternatives

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Impact Analysis

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Risks And Follow-up

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.
